"""
Guardian vector store — ChromaDB with 3 collections and HuggingFace embeddings.
"""

import os
import logging
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

from config import settings

logger = logging.getLogger(__name__)


class GuardianVectorStore:
    """Manages 3 ChromaDB collections for Guardian's RAG system."""

    CARDS_COLLECTION = "guardian_cards"
    EDUCATION_COLLECTION = "guardian_education"
    HINDSIGHT_COLLECTION = "guardian_hindsight"

    def __init__(self):
        # Memory Optimization: Using Google's Cloud Embeddings instead of local models
        # to save ~300MB of RAM and prevent Render OOM crashes.
        embedding_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._embedding_model = None
        self._embedding_error = None

        if embedding_api_key:
            self._embedding_model = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=embedding_api_key,
            )
        else:
            self._embedding_error = (
                "Vector search is not configured on the backend. "
                "Set GOOGLE_API_KEY on the Render service for AskGuardian and card intelligence."
            )

        self._chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
        )

    @property
    def embedding_model(self) -> GoogleGenerativeAIEmbeddings:
        if self._embedding_model is None:
            raise RuntimeError(self._embedding_error)
        return self._embedding_model

    def _get_langchain_chroma(self, collection_name: str) -> Chroma:
        """Get a LangChain Chroma instance for a specific collection."""
        return Chroma(
            client=self._chroma_client,
            collection_name=collection_name,
            embedding_function=self.embedding_model,
        )

    # ------------------------------------------------------------------
    # Retrievers
    # ------------------------------------------------------------------
    def get_cards_retriever(self, k: int = 4):
        """Retriever for card intelligence collection."""
        store = self._get_langchain_chroma(self.CARDS_COLLECTION)
        return store.as_retriever(search_kwargs={"k": k})

    def get_cards_retriever_for_category(self, category: str, k: int = 4):
        """
        Returns a retriever that fetches the top-k card chunks
        most relevant to the given spend category.
        Uses similarity search with metadata awareness.
        """
        store = self._get_langchain_chroma(self.CARDS_COLLECTION)
        return store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": k,
                "filter": None   # no hard filter — let semantic similarity work
            }
        )

    def similarity_search_with_scores(self, query: str, k: int = 4) -> list[tuple]:
        """
        Returns (Document, score) pairs for confidence checking.
        Score is cosine distance — lower is better (closer to 0 = more relevant).
        """
        store = self._get_langchain_chroma(self.CARDS_COLLECTION)
        return store.similarity_search_with_score(query, k=k)

    def get_education_retriever(self, k: int = 4):
        """Retriever for finance education collection."""
        store = self._get_langchain_chroma(self.EDUCATION_COLLECTION)
        return store.as_retriever(search_kwargs={"k": k})

    def get_hindsight_retriever(self, user_id: str, k: int = 4):
        """Retriever for user-specific hindsight collection."""
        store = self._get_langchain_chroma(self.HINDSIGHT_COLLECTION)
        return store.as_retriever(
            search_kwargs={
                "k": k,
                "filter": {"user_id": user_id},
            }
        )

    # ------------------------------------------------------------------
    # Hindsight document management
    # ------------------------------------------------------------------
    def add_hindsight_docs(self, user_id: str, docs: list) -> None:
        """Add user-specific hindsight documents, purging any old ones for this user first."""
        # 1. Purge old documents for this user to prevent RAG confusion
        try:
            self._chroma_client.get_collection(self.HINDSIGHT_COLLECTION).delete(
                where={"user_id": user_id}
            )
        except Exception as e:
            logger.warning(f"[VectorStore] Could not purge old hindsight for {user_id}: {e}")

        # 2. Add new documents
        store = self._get_langchain_chroma(self.HINDSIGHT_COLLECTION)
        for doc in docs:
            doc.metadata["user_id"] = user_id
        store.add_documents(docs)

    def user_has_hindsight_data(self, user_id: str) -> bool:
        """
        Checks if hindsight documents exist in ChromaDB for this user_id.
        Returns False if the collection is empty or user has no documents.
        """
        try:
            store = self._get_langchain_chroma(self.HINDSIGHT_COLLECTION)
            results = store.similarity_search(
                query="spending analysis",
                k=1,
                filter={"user_id": user_id}
            )
            return len(results) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Bulk add (used by ingest_knowledge.py)
    # ------------------------------------------------------------------
    def add_card_documents(self, docs: list) -> None:
        """Add card intelligence documents."""
        store = self._get_langchain_chroma(self.CARDS_COLLECTION)
        store.add_documents(docs)

    def add_education_documents(self, docs: list) -> None:
        """Add finance education documents."""
        store = self._get_langchain_chroma(self.EDUCATION_COLLECTION)
        store.add_documents(docs)
