"""
Card Intelligence RAG — answers questions about Indian credit cards
using the guardian_cards ChromaDB collection.
"""
from __future__ import annotations

import logging

from agents.llm_factory import create_llm
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from rag.vectorstore import GuardianVectorStore

logger = logging.getLogger(__name__)

CARD_SYSTEM_PROMPT = (
    "You are a credit card expert specialising in Indian cards. Answer questions "
    "about which cards give the best rewards for specific spending patterns. Always "
    "mention the reward rate as a percentage, annual fee, and net benefit after fee. "
    "If you don't know something, say so — never invent card details. Cite the card "
    "name clearly.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


class CardIntelligenceRAG:
    """RAG chain for credit card intelligence queries."""

    def __init__(self, vectorstore: GuardianVectorStore):
        self._vectorstore = vectorstore

    def answer(
        self,
        question: str,
        api_key: str,
        provider: str = "google",
        model_id: str = "gemini-2.5-flash-lite",
        user_spend_context: dict | None = None,
    ) -> dict:
        """
        Answer a credit card question using RAG.

        Args:
            question: User's question about cards
            api_key: User's OpenAI API key (BYOK)
            user_spend_context: Optional dict of category → monthly spend

        Returns:
            Dict with answer, source cards, and recommended card
        """
        try:
            # Prepend user context if available
            full_question = question
            if user_spend_context:
                context_lines = ", ".join(
                    f"₹{amount:,.0f}/month on {cat}"
                    for cat, amount in user_spend_context.items()
                    if amount > 0
                )
                full_question = f"User context: {context_lines}\nQuestion: {question}"

            # Build the chain with user's API key
            llm = create_llm(api_key, provider, model_id, temperature=0.3)
            retriever = self._vectorstore.get_cards_retriever(k=8)

            prompt = PromptTemplate(
                template=CARD_SYSTEM_PROMPT,
                input_variables=["context", "question"],
            )

            chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )

            result = chain.invoke({"query": full_question})

            # Extract source card names from documents
            source_cards = list({
                doc.metadata.get("card_name", "Unknown")
                for doc in result.get("source_documents", [])
            })

            # Try to identify a recommended card from the answer
            recommended = source_cards[0] if source_cards else None

            return {
                "answer": result.get("result", "No answer generated."),
                "source_cards": source_cards,
                "recommended_card": recommended,
            }

        except Exception as e:
            logger.error(f"CardIntelligenceRAG error: {e}")
            return {
                "answer": f"Unable to answer at this time: {str(e)}",
                "source_cards": [],
                "recommended_card": None,
            }
