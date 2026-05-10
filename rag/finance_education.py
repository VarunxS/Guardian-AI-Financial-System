"""
Finance Education RAG — answers personal finance questions using
the guardian_education ChromaDB collection.
"""

import logging

from agents.llm_factory import create_llm
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

from rag.vectorstore import GuardianVectorStore

logger = logging.getLogger(__name__)

EDUCATION_SYSTEM_PROMPT = (
    "You are a friendly personal finance educator. Answer questions clearly and "
    "simply for someone with no finance background. Use Indian examples and rupee "
    "amounts where relevant. If a question is about a specific regulation, cite "
    "RBI or SEBI as appropriate. Never give specific investment advice.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


class FinanceEducationRAG:
    """RAG chain for personal finance education queries."""

    def __init__(self, vectorstore: GuardianVectorStore):
        self._vectorstore = vectorstore

    def answer(self, question: str, api_key: str, provider: str = "google", model_id: str = "gemini-2.5-flash-lite") -> dict:
        """
        Answer a personal finance education question using RAG.

        Args:
            question: User's finance question
            api_key: User's OpenAI API key (BYOK)
            provider: AI provider (google, openai, etc.)
            model_id: Specific model to use

        Returns:
            Dict with answer and topics covered
        """
        try:
            llm = create_llm(api_key, provider, model_id, temperature=0.4)
            retriever = self._vectorstore.get_education_retriever(k=4)

            prompt = PromptTemplate(
                template=EDUCATION_SYSTEM_PROMPT,
                input_variables=["context", "question"],
            )

            chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )

            result = chain.invoke({"query": question})

            # Extract topics from source documents
            topics = list({
                doc.page_content.split("\n")[0].strip("# ").strip()
                for doc in result.get("source_documents", [])
                if doc.page_content.strip()
            })

            return {
                "answer": result.get("result", "No answer generated."),
                "topics_covered": topics[:5],  # limit to 5 topics
            }

        except Exception as e:
            logger.error(f"FinanceEducationRAG error: {e}")
            return {
                "answer": f"Unable to answer at this time: {str(e)}",
                "topics_covered": [],
            }
