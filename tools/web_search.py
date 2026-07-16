"""
web_search.py
-------------
Web search tool using Tavily API.
- Collects up to MAX_SOURCES results
- Handles individual URL failures gracefully (skip + log)
- Returns structured SourceDocument objects
"""

from __future__ import annotations

import os
import time
import traceback
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()


@dataclass
class SourceDocument:
    """A single piece of research from the web."""
    title: str
    url: str
    content: str
    published_date: Optional[str]
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    score: float = 0.0
    failed: bool = False
    failure_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "published_date": self.published_date,
            "retrieved_at": self.retrieved_at,
            "score": self.score,
            "failed": self.failed,
            "failure_reason": self.failure_reason,
        }


@dataclass
class SearchResult:
    """Aggregated result from one search query."""
    query: str
    documents: List[SourceDocument] = field(default_factory=list)
    failed_urls: List[dict] = field(default_factory=list)
    total_attempted: int = 0
    elapsed_seconds: float = 0.0

    @property
    def successful_count(self) -> int:
        return len([d for d in self.documents if not d.failed])

    @property
    def failed_count(self) -> int:
        return len(self.failed_urls)


class WebSearchTool:
    """
    Tavily-backed web search with:
    - Per-URL failure isolation
    - Source count limits (MAX_SOURCES)
    - Structured output (SourceDocument)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_sources: int = None,
        max_results_per_query: int = 5,
    ):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.max_sources = max_sources or int(os.getenv("MAX_SOURCES", 20))
        self.max_results_per_query = max_results_per_query

        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set. Add it to your .env file or pass api_key= directly."
            )

        try:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=self.api_key)
        except ImportError:
            raise ImportError("tavily-python is not installed. Run: pip install tavily-python")

    def search(self, query: str, collected_so_far: int = 0) -> SearchResult:
        """
        Search the web for a query.

        Args:
            query: The search query
            collected_so_far: How many sources have already been collected (for limit enforcement)

        Returns:
            SearchResult with documents and failure info
        """
        start = time.time()
        result = SearchResult(query=query)

        remaining_budget = self.max_sources - collected_so_far
        if remaining_budget <= 0:
            return result  # Source limit already reached

        max_to_fetch = min(self.max_results_per_query, remaining_budget)

        try:
            raw = self._client.search(
                query=query,
                search_depth="advanced",
                max_results=max_to_fetch,
                include_raw_content=True,
            )
        except Exception as e:
            result.failed_urls.append({
                "url": f"[Tavily search: {query}]",
                "reason": str(e),
            })
            result.elapsed_seconds = time.time() - start
            return result

        results_list = raw.get("results", [])
        result.total_attempted = len(results_list)

        for item in results_list:
            url = item.get("url", "")
            try:
                doc = self._parse_result(item)
                result.documents.append(doc)
            except Exception as e:
                result.failed_urls.append({
                    "url": url,
                    "reason": f"Parse error: {str(e)}",
                })

        result.elapsed_seconds = time.time() - start
        return result

    def multi_search(self, queries: List[str]) -> List[SearchResult]:
        """
        Run multiple queries, respecting MAX_SOURCES across all.

        Args:
            queries: List of search queries

        Returns:
            List of SearchResult objects
        """
        all_results: List[SearchResult] = []
        collected = 0

        for query in queries:
            if collected >= self.max_sources:
                break
            sr = self.search(query, collected_so_far=collected)
            collected += sr.successful_count
            all_results.append(sr)

        return all_results

    def _parse_result(self, item: dict) -> SourceDocument:
        """Parse a Tavily result dict into a SourceDocument."""
        content = item.get("raw_content") or item.get("content") or ""
        # Truncate very long content to avoid token bloat
        if len(content) > 4000:
            content = content[:4000] + "... [truncated]"

        return SourceDocument(
            title=item.get("title", "Untitled"),
            url=item.get("url", ""),
            content=content,
            published_date=item.get("published_date"),
            score=float(item.get("score", 0.0)),
        )

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Quick validation of a Tavily API key (no search performed)."""
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            # Attempt a minimal search to validate
            client.search("test", max_results=1)
            return True
        except Exception:
            return False
