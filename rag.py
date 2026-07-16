"""
rag.py
------
RAG (Retrieval-Augmented Generation) tool.
- Stores research documents in a FAISS or ChromaDB vector store
- Retrieves relevant chunks during analysis and writing phases
- Supports both backends via VECTOR_STORE env var ("faiss" | "chroma")
"""

from __future__ import annotations

import os
import uuid
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE", "faiss").lower()


class RAGTool:
    """
    Vector store wrapper that supports FAISS and ChromaDB.

    Usage:
        rag = RAGTool()
        rag.add_documents(source_documents)
        chunks = rag.retrieve("competitor pricing AI tools", k=5)
    """

    def __init__(self, backend: Optional[str] = None, persist_dir: str = "./logs/chroma_db"):
        self.backend = backend or VECTOR_STORE_BACKEND
        self.persist_dir = persist_dir
        self._vectorstore = None
        self._embeddings = None
        self._documents: List[dict] = []  # fallback in-memory store
        self._initialized = False

        self._setup_embeddings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_documents(self, source_documents: List) -> int:
        """
        Add SourceDocument objects (or dicts) to the vector store.

        Args:
            source_documents: List of SourceDocument or dict with title/url/content keys

        Returns:
            Number of chunks added
        """
        if not source_documents:
            return 0

        texts, metadatas = self._prepare_chunks(source_documents)

        if not texts:
            return 0

        if self._initialized and self._vectorstore is not None:
            try:
                self._add_to_vectorstore(texts, metadatas)
                return len(texts)
            except Exception as e:
                print(f"[RAG] Vector store add failed: {e}. Falling back to in-memory.")

        # Fallback: simple in-memory list
        for text, meta in zip(texts, metadatas):
            self._documents.append({"content": text, "metadata": meta})
        return len(texts)

    def retrieve(self, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Args:
            query: Natural language query
            k: Number of chunks to return

        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        if self._initialized and self._vectorstore is not None:
            try:
                return self._query_vectorstore(query, k)
            except Exception as e:
                print(f"[RAG] Retrieval failed: {e}. Using fallback.")

        # Fallback: return first k documents (no ranking)
        return self._documents[:k]

    def clear(self):
        """Clear all stored documents."""
        self._documents = []
        if self._initialized and self._vectorstore is not None:
            try:
                if self.backend == "chroma":
                    self._vectorstore.reset_collection()
                elif self.backend == "faiss":
                    self._setup_faiss()
            except Exception:
                pass

    def document_count(self) -> int:
        """Return the number of stored chunks."""
        if self._initialized and self._vectorstore is not None:
            try:
                if self.backend == "faiss":
                    return self._vectorstore.index.ntotal
                elif self.backend == "chroma":
                    return self._vectorstore._collection.count()
            except Exception:
                pass
        return len(self._documents)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_embeddings(self):
        """Initialize embeddings model and vector store."""
        try:
            from langchain_openai import OpenAIEmbeddings
            openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
            if not openrouter_key:
                print("[RAG] OPENROUTER_API_KEY not set — RAG will use in-memory fallback.")
                return

            # OpenRouter supports OpenAI-compatible embeddings via the same base URL.
            # We point OpenAIEmbeddings at OpenRouter and use a supported embeddings model.
            self._embeddings = OpenAIEmbeddings(
                model="openai/text-embedding-3-small",
                openai_api_key=openrouter_key,
                openai_api_base="https://openrouter.ai/api/v1",
            )

            if self.backend == "faiss":
                self._setup_faiss()
            elif self.backend == "chroma":
                self._setup_chroma()
            else:
                print(f"[RAG] Unknown backend '{self.backend}'. Using faiss.")
                self._setup_faiss()

        except ImportError as e:
            print(f"[RAG] Import error: {e}. RAG will use in-memory fallback.")
        except Exception as e:
            print(f"[RAG] Setup error: {e}. RAG will use in-memory fallback.")

    def _setup_faiss(self):
        """Initialize an empty FAISS index."""
        try:
            from langchain_community.vectorstores import FAISS
            # Create a minimal placeholder — actual store built on first add
            self._faiss_class = FAISS
            self._vectorstore = None  # Built lazily on first add
            self._initialized = True
            self.backend = "faiss"
        except ImportError:
            print("[RAG] faiss-cpu not installed. Falling back to in-memory.")

    def _setup_chroma(self):
        """Initialize a ChromaDB persistent store."""
        try:
            from langchain_community.vectorstores import Chroma
            os.makedirs(self.persist_dir, exist_ok=True)
            self._vectorstore = Chroma(
                collection_name="ci_briefing",
                embedding_function=self._embeddings,
                persist_directory=self.persist_dir,
            )
            self._initialized = True
            self.backend = "chroma"
        except ImportError:
            print("[RAG] chromadb not installed. Falling back to faiss.")
            self._setup_faiss()
        except Exception as e:
            print(f"[RAG] ChromaDB setup error: {e}. Using in-memory fallback.")

    def _prepare_chunks(self, source_documents: List) -> tuple[List[str], List[dict]]:
        """Split source documents into text chunks with metadata."""
        texts = []
        metadatas = []

        for doc in source_documents:
            # Accept both SourceDocument objects and plain dicts
            if hasattr(doc, "content"):
                content = doc.content or ""
                meta = {
                    "title": getattr(doc, "title", ""),
                    "url": getattr(doc, "url", ""),
                    "published_date": getattr(doc, "published_date", ""),
                }
            elif isinstance(doc, dict):
                content = doc.get("content", "")
                meta = {
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "published_date": doc.get("published_date", ""),
                }
            else:
                continue

            if not content.strip():
                continue

            # Chunk into ~1000-char pieces
            chunks = self._chunk_text(content, chunk_size=1000, overlap=100)
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append({**meta, "chunk_index": i})

        return texts, metadatas

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Simple character-level chunker."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return chunks

    def _add_to_vectorstore(self, texts: List[str], metadatas: List[dict]):
        """Add texts to the active vector store."""
        if self.backend == "faiss":
            from langchain_community.vectorstores import FAISS
            if self._vectorstore is None:
                # First add — create the store from these texts
                self._vectorstore = FAISS.from_texts(
                    texts=texts,
                    embedding=self._embeddings,
                    metadatas=metadatas,
                )
            else:
                self._vectorstore.add_texts(texts=texts, metadatas=metadatas)
        elif self.backend == "chroma":
            self._vectorstore.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=[str(uuid.uuid4()) for _ in texts],
            )

    def _query_vectorstore(self, query: str, k: int) -> List[dict]:
        """Query the vector store and return formatted chunks."""
        if self._vectorstore is None:
            return self._documents[:k]

        docs = self._vectorstore.similarity_search(query, k=k)
        return [
            {
                "content": d.page_content,
                "metadata": d.metadata,
            }
            for d in docs
        ]
