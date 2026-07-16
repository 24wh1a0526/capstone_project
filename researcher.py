"""
researcher.py
-------------
Research Agent:
- Executes search queries provided by the Supervisor
- Collects trustworthy sources (pricing, product launches, market news)
- Stores structured SourceDocuments (title, URL, date, content)
- Isolates per-URL failures — failed sources are skipped and logged
- Respects MAX_SOURCES limit
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from dotenv import load_dotenv

from tools.web_search import WebSearchTool, SourceDocument, SearchResult

load_dotenv()


class ResearcherAgent:
    """
    Executes web searches and returns structured source documents.

    Responsibilities:
    - Run search queries from the supervisor's plan
    - Collect pricing data, product launches, market news
    - Track failed URLs separately from successful ones
    - Enforce MAX_SOURCES limit across all queries
    """

    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        max_sources: int = None,
    ):
        self.max_sources = max_sources or int(os.getenv("MAX_SOURCES", 20))
        self._search_tool = WebSearchTool(
            api_key=tavily_api_key,
            max_sources=self.max_sources,
        )
        self.collected_sources: List[SourceDocument] = []
        self.failed_sources: List[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def research(self, queries: List[str]) -> Tuple[List[SourceDocument], List[dict]]:
        """
        Execute a list of search queries and collect source documents.

        Args:
            queries: List of search query strings from the Supervisor

        Returns:
            Tuple of (successful_sources, failed_sources)
        """
        self.collected_sources = []
        self.failed_sources = []

        for query in queries:
            if len(self.collected_sources) >= self.max_sources:
                print(f"[Researcher] Source limit ({self.max_sources}) reached. Stopping.")
                break

            print(f"[Researcher] Searching: {query}")
            result: SearchResult = self._search_tool.search(
                query=query,
                collected_so_far=len(self.collected_sources),
            )

            # Collect successful documents
            for doc in result.documents:
                if len(self.collected_sources) >= self.max_sources:
                    break
                self.collected_sources.append(doc)

            # Record failures
            for failure in result.failed_urls:
                self.failed_sources.append({
                    "query": query,
                    "url": failure.get("url", "unknown"),
                    "reason": failure.get("reason", "Unknown error"),
                })
                print(f"[Researcher] ⚠ Failed source: {failure.get('url')} — {failure.get('reason')}")

        print(
            f"[Researcher] Collected {len(self.collected_sources)} sources, "
            f"{len(self.failed_sources)} failures."
        )
        return self.collected_sources, self.failed_sources

    def store_in_rag(self, rag_tool) -> int:
        """
        Push collected sources into the RAG vector store.

        Args:
            rag_tool: An initialized RAGTool instance

        Returns:
            Number of chunks stored
        """
        if not self.collected_sources:
            return 0
        return rag_tool.add_documents(self.collected_sources)

    def summarize_findings(self) -> dict:
        """Return a quick summary of the research run."""
        return {
            "total_sources": len(self.collected_sources),
            "failed_sources": len(self.failed_sources),
            "sources": [
                {
                    "title": d.title,
                    "url": d.url,
                    "published_date": d.published_date,
                    "content_length": len(d.content),
                }
                for d in self.collected_sources
            ],
            "failures": self.failed_sources,
        }
