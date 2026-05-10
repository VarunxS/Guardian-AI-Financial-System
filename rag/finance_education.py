"""
Finance Education RAG — answers personal finance questions using
the guardian_education ChromaDB collection.
"""

import logging

from agents.llm_factory import create_llm
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
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
        """
        try:
            # Build the chain with LCEL (LangChain 0.3 compatible)
            llm = create_llm(api_key, provider, model_id, temperature=0.4)
            retriever = self._vectorstore.get_education_retriever(k=4)

            prompt = PromptTemplate.from_template(EDUCATION_SYSTEM_PROMPT)

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            # Retrieve source documents first
            source_documents = retriever.invoke(question)
            
            # Run the chain manually for maximum compatibility
            chain = (
                {"context": lambda x: format_docs(source_documents), "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )

            answer = chain.invoke(question)

            # Extract topics from source documents
            topics = list({
                doc.page_content.split("\n")[0].strip("# ").strip()
                for doc in source_documents
                if doc.page_content.strip()
            })

            return {
                "answer": answer,
                "topics_covered": topics[:5],  # limit to 5 topics
            }

        except Exception as e:
            logger.error(f"FinanceEducationRAG error: {e}")
            return {
                "answer": f"Unable to answer at this time: {str(e)}",
                "topics_covered": [],
            }
