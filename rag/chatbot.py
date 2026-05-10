"""
Guardian RAG Chatbot — routes questions to the right knowledge base,
retrieves context, and generates answers with source attribution.
"""

import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage

from agents.utils import get_llm
from rag.vectorstore import GuardianVectorStore
from rag.exa_research import ExaResearch

logger = logging.getLogger(__name__)

RouteLabel = Literal["education", "card", "hindsight", "unclear"]

# ── Router ────────────────────────────────────────────────────────────────────

ROUTER_SYSTEM = """
You are a query router for a personal finance chatbot called Guardian.
Classify the user's question into exactly one of these four categories:

"education"  — general finance concepts, definitions, how-things-work questions.
               Examples: "what is CIBIL score", "explain credit utilisation",
               "how does no-cost EMI work", "what is the 50/30/20 rule"

"card"       — questions about credit cards, rewards, which card to use,
               card comparisons, whether a card is worth its fee.
               Examples: "which card is best for travel", "is HDFC Infinia worth it",
               "compare Axis Atlas vs Amex Platinum", "best cashback card India"

"hindsight"  — questions about the user's own past spending, categories, budget,
               trends, and missed rewards. Requires personal transaction data.
               Examples: "analyze my Zomato spend trend", "compare my top 3 categories",
               "what card should I have used last month", "how much reward did I miss",
               "how much did I spend on groceries", "what are my biggest expenses"

"unclear"    — the question spans multiple categories, is ambiguous, or
               cannot be confidently classified into one of the above three.
               Example: "is my dining spend worth getting a premium card"
               (needs both card data AND the user's own spend context)

Return only the single label. No explanation. No punctuation. Just the label.
"""


class RAGRouter:
    def __init__(self, api_key: str, provider: str = "openai", model_id: str = "gpt-4o-mini"):
        self.llm = get_llm(api_key, provider, model_id)

    async def classify(self, question: str, has_hindsight_data: bool) -> RouteLabel:
        """
        Classifies the user question into a route label.
        If hindsight data doesn't exist for this user, never routes to hindsight.
        Falls back to 'unclear' on any failure.
        """
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=ROUTER_SYSTEM),
                HumanMessage(content=question)
            ])
            label = response.content.strip().lower()

            # Validate label is one of the four
            if label not in ("education", "card", "hindsight", "unclear"):
                return "unclear"

            # Downgrade hindsight to unclear if no data exists
            if label == "hindsight" and not has_hindsight_data:
                return "unclear"

            return label

        except Exception as e:
            logger.warning(f"Router classification failed: {e}")
            return "unclear"


# ── System prompts for each chain ────────────────────────────────────────────

EDUCATION_SYSTEM = """
You are Guardian's finance educator — a friendly, clear teacher explaining
personal finance concepts to a young Indian professional.

Answer using only the context provided. If the context doesn't cover the
question, say so honestly — do not guess.

Rules:
- Use simple language, no jargon
- Use Indian examples and rupee amounts where relevant
- If a concept involves RBI or SEBI regulation, cite it
- Keep answers under 150 words unless the question genuinely requires more
- Never give specific investment advice
"""

CARD_SYSTEM = """
You are Guardian's credit card expert — India's most knowledgeable, unbiased
card recommendation engine.

You have retrieved relevant card data from the database. You also have the
user's financial context showing their actual spend by category.

Answer using the retrieved card data combined with the user's spend context.

Rules:
- If the user asks for a specific number of cards (e.g. "top 5"), provide exactly that many if available in context.
- Always mention reward rate as a percentage AND as a rupee amount
  based on the user's actual spend (e.g. "5% on dining = ₹420/month for you")
- Always mention the annual fee and whether it makes sense at this user's spend level
- If two cards are close, compare them. Be direct about which one is better for THIS user.
- Keep answers informative but concise. If multiple cards are listed, use a numbered list.
- Never recommend a card not present in the retrieved context
"""

HINDSIGHT_SYSTEM = """
You are Guardian's personal finance analyst. You have access to the user's LATEST spending analysis.

Your job: Answer the user's question about their spending, trends, or budget using the provided context.

Rules:
- CRITICAL: Use the 'LATEST ANALYSIS DATA' provided in the user context as your primary source of truth.
- If the retrieved documents from the knowledge base contain conflicting data or multiple 'periods', ALWAYS prefer the numbers from the 'LATEST ANALYSIS DATA' section.
- NEVER hallucinate or guess. If you can't find a specific merchant or amount in the context, say: "I don't have that specific data in your recent statement."
- ALWAYS use specific rupee amounts and category names.
- Do not say "based on the context" or "which period do you mean?". Assume the user is asking about their most recent upload unless they explicitly specify otherwise.
- Keep answers under 200 words.
"""

MERGED_SYSTEM = """
You are Guardian — a personal finance assistant with access to finance
education content, credit card data, and the user's own spending history.

Answer the question using all the context provided. Blend the sources
naturally — you don't need to label which part comes from where.

Rules:
- CRITICAL: Do NOT hallucinate the user's spending based on credit card data. If the user's spending data does not contain the exact category they are asking about, say you don't have that data. Never reverse-calculate spending from a card's break-even point.
- CRITICAL: Do NOT guess merchant names or amounts if they are not explicitly listed in the context.
- Use the user's actual spend numbers when they are available in context.
- Be specific with rupee amounts.
- Keep answers under 250 words.
- If the question asks for a recommendation, give one clearly.
"""


# ── Source labels ─────────────────────────────────────────────────────────────

SOURCE_LABELS = {
    "education": "📚 Finance education",
    "card":      "💳 Card database",
    "hindsight": "📊 Your analysis",
    "unclear":   "🔍 Combined sources",
}

NO_HINDSIGHT_MESSAGE = (
    "I don't have your transaction data yet. Upload your bank or credit card "
    "statement first — once Guardian analyses it, I can tell you exactly which "
    "cards you should have used and how much reward you missed."
)


# ── Main chatbot class ───────────────────────────────────────────────────────

class GuardianChatbot:
    """
    Main chatbot class. Instantiate once per session and reuse.
    Routes questions to the right KB, retrieves context, generates answers.
    """

    def __init__(self, api_key: str, vectorstore: GuardianVectorStore,
                 user_id: str, provider: str = "openai", model_id: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.provider = provider
        self.model_id = model_id
        self.vectorstore = vectorstore
        self.user_id = user_id
        self.llm = get_llm(api_key, provider, model_id)
        self.router = RAGRouter(api_key, provider, model_id)
        self.exa = ExaResearch()

        # Check if hindsight data exists for this user
        self.has_hindsight_data = vectorstore.user_has_hindsight_data(user_id)

        # Conversation history — simple list of (role, content) tuples
        self._chat_history: list[tuple[str, str]] = []
        self._max_history = 6  # keep last 6 messages (3 exchanges)

    def _add_to_history(self, question: str, answer: str):
        """Append a Q/A pair and trim to window size."""
        self._chat_history.append(("human", question))
        self._chat_history.append(("assistant", answer))
        # Keep only the last N messages
        if len(self._chat_history) > self._max_history:
            self._chat_history = self._chat_history[-self._max_history:]

    def _build_history_messages(self) -> list:
        """Convert history to LangChain message objects."""
        messages = []
        for role, content in self._chat_history:
            if role == "human":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(HumanMessage(content=f"[Previous assistant response]: {content}"))
        return messages

    async def _retrieve_context(self, route: RouteLabel, question: str) -> str:
        """Retrieve documents from the appropriate KB based on route."""
        if route == "education":
            retriever = self.vectorstore.get_education_retriever(k=4)
            docs = await retriever.ainvoke(question)
            return "\n\n".join(d.page_content for d in docs) if docs else ""

        elif route == "card":
            retriever = self.vectorstore.get_cards_retriever(k=8)
            docs = await retriever.ainvoke(question)
            return "\n\n".join(d.page_content for d in docs) if docs else ""

        elif route == "hindsight":
            retriever = self.vectorstore.get_hindsight_retriever(self.user_id, k=5)
            docs = await retriever.ainvoke(question)
            return "\n\n".join(d.page_content for d in docs) if docs else ""

        return ""

    async def _query_single_kb(self, route: RouteLabel, question: str,
                         user_context: str) -> str:
        """Query a single knowledge base and generate a response."""
        system_prompts = {
            "education": EDUCATION_SYSTEM,
            "card": CARD_SYSTEM,
            "hindsight": HINDSIGHT_SYSTEM,
        }

        import asyncio
        system_prompt = system_prompts.get(route, MERGED_SYSTEM)
        
        # Parallel: Retrieval + Exa Search
        tasks = [self._retrieve_context(route, question)]
        
        if route == "card":
            tasks.append(asyncio.to_thread(self.exa.search_card_details, question, 3))
        elif route == "education":
            tasks.append(asyncio.to_thread(self.exa.search_finance_regulations, topic=question, num_results=3))
        else:
            tasks.append(asyncio.sleep(0, result=[])) # dummy
            
        kb_context, exa_results = await asyncio.gather(*tasks)

        exa_context = ""
        if exa_results:
            exa_context = "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in exa_results])
        
        if exa_context:
            kb_context += f"\n\n## Live Web Research (Exa AI):\n{exa_context}"

        if not kb_context.strip():
            return "I don't have enough information to answer that question confidently."

        prompt_messages = (
            [SystemMessage(content=system_prompt)]
            + self._build_history_messages()
            + [HumanMessage(content=(
                f"Context from knowledge base:\n{kb_context}\n\n"
                f"User financial context:\n{user_context}\n\n"
                f"Question: {question}"
            ))]
        )

        try:
            response = await self.llm.ainvoke(prompt_messages)
            answer = response.content.strip()
            self._add_to_history(question, answer)
            return answer
        except Exception as e:
            logger.error(f"Single KB query failed for route {route}: {e}")
            return "Something went wrong. Please try again."

    async def _query_merged(self, question: str, user_context: str) -> str:
        """
        Option 3 fallback — queries all three KBs, merges context,
        single LLM call. Used when route is 'unclear'.
        """
        import asyncio
        # Retrieve from all available KBs in parallel
        edu_retriever = self.vectorstore.get_education_retriever(k=3)
        card_retriever = self.vectorstore.get_cards_retriever(k=3)

        tasks = [
            edu_retriever.ainvoke(question),
            card_retriever.ainvoke(question),
            asyncio.to_thread(self.exa.search_card_details, question, 3)
        ]
        
        if self.has_hindsight_data:
            h_retriever = self.vectorstore.get_hindsight_retriever(self.user_id, k=3)
            tasks.append(h_retriever.ainvoke(question))
        
        results = await asyncio.gather(*tasks)
        edu_docs, card_docs, exa_results = results[0], results[1], results[2]
        hindsight_docs = results[3] if self.has_hindsight_data else []

        merged_context = ""

        if edu_docs:
            merged_context += "## Finance education context\n"
            merged_context += "\n".join(d.page_content for d in edu_docs) + "\n\n"

        if card_docs:
            merged_context += "## Card database context\n"
            merged_context += "\n".join(d.page_content for d in card_docs) + "\n\n"

        if hindsight_docs:
            merged_context += "## User's spending analysis context\n"
            merged_context += "\n".join(d.page_content for d in hindsight_docs) + "\n\n"

        if exa_results:
            exa_context = "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in exa_results])
            merged_context += f"## Live Web Research (Exa AI):\n{exa_context}\n\n"

        if not merged_context.strip():
            return ("I don't have enough information to answer that question "
                    "confidently. Try asking about a specific card, finance "
                    "concept, or your spending habits.")

        # Single LLM call with merged context
        prompt_messages = (
            [SystemMessage(content=MERGED_SYSTEM)]
            + self._build_history_messages()
            + [HumanMessage(content=(
                f"Context:\n{merged_context}\n\n"
                f"User financial context:\n{user_context}\n\n"
                f"Question: {question}"
            ))]
        )

        try:
            response = await self.llm.ainvoke(prompt_messages)
            answer = response.content.strip()
            self._add_to_history(question, answer)
            return answer
        except Exception as e:
            logger.error(f"Merged query failed: {e}")
            return "Something went wrong. Please try again."

    async def chat(self, question: str, user_context: str = "") -> dict:
        """
        Main entry point called on every user message.

        Args:
            question: the user's message
            user_context: formatted string of user's financial snapshot
                          built by get_user_context_summary() from Supabase

        Returns:
            {
                "answer": str,
                "route": RouteLabel,
                "source_label": str — human-readable source badge
            }
        """
        # Classify the question
        route = await self.router.classify(question, self.has_hindsight_data)

        # Handle hindsight with no data gracefully
        if route == "hindsight" and not self.has_hindsight_data:
            return {
                "answer": NO_HINDSIGHT_MESSAGE,
                "route": "hindsight",
                "source_label": SOURCE_LABELS["hindsight"]
            }

        # Option 3 fallback for unclear questions
        if route == "unclear":
            answer = await self._query_merged(question, user_context)
            return {
                "answer": answer,
                "route": "unclear",
                "source_label": SOURCE_LABELS["unclear"]
            }

        # Single KB chain
        answer = await self._query_single_kb(route, question, user_context)
        # Fallback to merged if single KB returned nothing useful
        if answer == "I don't have enough information to answer that question confidently.":
            answer = await self._query_merged(question, user_context)
            return {
                "answer": answer,
                "route": "unclear",
                "source_label": SOURCE_LABELS["unclear"]
            }

        return {
            "answer": answer,
            "route": route,
            "source_label": SOURCE_LABELS[route]
        }

    def clear_history(self):
        """Reset conversation memory."""
        self._chat_history = []
