"""
analyst.py
----------
Analyst Agent:
- Processes collected research documents
- Deduplicates information
- Identifies competitor trends and market signals
- Removes unsupported claims
- Produces structured insights with source citations
"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from tools.web_search import SourceDocument

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ANALYST_MAX_TOKENS = int(os.getenv("ANALYST_MAX_TOKENS", 2500))


class AnalystAgent:
    """
    Analyzes raw research documents and produces structured competitive insights.

    Output structure:
    {
        "competitor_pricing": [...],
        "product_updates": [...],
        "market_signals": [...],
        "trends": [...],
        "removed_claims": [...],
        "citations": {claim_id: {title, url}}
    }
    """

    SYSTEM_PROMPT = """You are a Senior Competitive Intelligence Analyst.

Your job is to analyze raw research documents and extract structured, factual insights.

RULES (STRICT):
1. ONLY include claims that are supported by the provided source documents.
2. Every claim MUST include a citation: the source title and URL.
3. If a claim cannot be verified from the sources, mark it as UNVERIFIED and OMIT it.
4. REMOVE duplicate information — keep the most recent/authoritative version.
5. NEVER include rumors, speculation, or unverified news.
6. If a source mentions a company's bankruptcy, fraud, or legal trouble without a
   credible citation, REJECT it entirely and flag it as a governance violation.
7. Before leaving "product_updates" empty, re-scan every source for feature
   releases, version launches, roadmap announcements, or partnership news —
   these are often mentioned in passing rather than being the article's main
   subject. Only leave the category empty if truly no source mentions one.
8. If a PREVIOUS BRIEFING is supplied below, compare your new findings
   against it and populate "changes_since_last_briefing":
   - "new": findings that did not appear in the previous briefing.
   - "updated": findings on the same company/topic whose detail changed
     (e.g. a new price, a superseded product update).
   - "unchanged_count": a rough count of findings that still hold and were
     simply reconfirmed by newer sources.
   Do NOT guess at changes if no previous briefing is supplied — return
   empty lists in that case.

OUTPUT FORMAT (valid JSON only):
{
  "competitor_pricing": [
    {"company": "...", "detail": "...", "citation": {"title": "...", "url": "..."}}
  ],
  "product_updates": [
    {"company": "...", "update": "...", "citation": {"title": "...", "url": "..."}}
  ],
  "market_signals": [
    {"signal": "...", "citation": {"title": "...", "url": "..."}}
  ],
  "trends": [
    {"trend": "...", "citation": {"title": "...", "url": "..."}}
  ],
  "removed_claims": [
    {"claim": "...", "reason": "..."}
  ],
  "governance_violations": [
    {"claim": "...", "reason": "..."}
  ],
  "changes_since_last_briefing": {
    "new": [{"summary": "...", "citation": {"title": "...", "url": "..."}}],
    "updated": [{"summary": "...", "was": "...", "now": "...", "citation": {"title": "...", "url": "..."}}],
    "unchanged_count": 0
  }
}
"""

    def __init__(self, model: Optional[str] = None):
        self.model = model or OPENROUTER_MODEL
        self._llm = ChatOpenAI(
            model=self.model,
            temperature=0.1,
            max_tokens=ANALYST_MAX_TOKENS,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "CI Briefing Crew"),
            },
        )
        self._last_analysis: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        documents: List[SourceDocument],
        topic: str,
        rag_tool=None,
        previous_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze source documents and return structured competitive insights.

        Args:
            documents: List of SourceDocument from the Researcher
            topic: The original research topic
            rag_tool: Optional RAGTool for context retrieval
            previous_analysis: The Analyst's structured output from the most
                recent prior briefing on this topic, if one exists. Used to
                populate "changes_since_last_briefing". Pass None on a
                topic's first run.

        Returns:
            Structured analysis dict
        """
        if not documents:
            return self._empty_analysis()

        # Build context from documents (+ optional RAG retrieval)
        context = self._build_context(documents, topic, rag_tool)
        previous_context = self._format_previous_analysis(previous_analysis)

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Research Topic: {topic}\n\n"
                f"Source Documents:\n{context}\n\n"
                f"Previous Briefing (for change-tracking):\n{previous_context}\n\n"
                "Analyze the above documents and return structured insights in the required JSON format."
            )),
        ]

        try:
            response = self._llm.invoke(messages)
            analysis = self._parse_analysis(response.content)
        except Exception as e:
            print(f"[Analyst] Analysis failed: {e}")
            analysis = self._empty_analysis()
            analysis["error"] = str(e)

        self._last_analysis = analysis

        # Log removed/governance-violating claims
        removed = analysis.get("removed_claims", [])
        violations = analysis.get("governance_violations", [])
        if removed:
            print(f"[Analyst] Removed {len(removed)} unsupported claims.")
        if violations:
            print(f"[Analyst] Governance violations found: {len(violations)}")

        return analysis

    def deduplicate(self, documents: List[SourceDocument]) -> List[SourceDocument]:
        """
        Remove duplicate documents based on URL similarity.

        Args:
            documents: Raw list of SourceDocuments

        Returns:
            Deduplicated list
        """
        seen_urls = set()
        unique = []
        for doc in documents:
            normalized = doc.url.rstrip("/").lower()
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique.append(doc)
        return unique

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context(
        self,
        documents: List[SourceDocument],
        topic: str,
        rag_tool=None,
        max_docs: int = None,
    ) -> str:
        """
        Build a text context block from documents.
        Optionally supplements with RAG-retrieved chunks.
        """
        # Deduplicate first
        docs = self.deduplicate(documents)
        max_docs = max_docs or int(os.getenv("MAX_SOURCES", 20))

        # If we have a RAG tool, retrieve topic-specific chunks
        rag_chunks = []
        if rag_tool is not None:
            try:
                rag_chunks = rag_tool.retrieve(topic, k=5)
            except Exception:
                pass

        context_parts = []

        # Add direct documents (up to max_docs)
        for i, doc in enumerate(docs[:max_docs]):
            context_parts.append(
                f"[Source {i+1}] {doc.title}\n"
                f"URL: {doc.url}\n"
                f"Date: {doc.published_date or 'Unknown'}\n"
                f"Content: {doc.content[:3000]}\n"
                f"---"
            )

        # Add RAG chunks as supplemental context
        for chunk in rag_chunks:
            meta = chunk.get("metadata", {})
            context_parts.append(
                f"[RAG Chunk] {meta.get('title', '')}\n"
                f"URL: {meta.get('url', '')}\n"
                f"Content: {chunk.get('content', '')[:500]}\n"
                f"---"
            )

        return "\n\n".join(context_parts)

    def _format_previous_analysis(self, previous_analysis: Optional[Dict[str, Any]]) -> str:
        """Format the prior briefing's structured analysis for change-tracking context."""
        if not previous_analysis:
            return "None — this is the first briefing for this topic. Leave changes_since_last_briefing empty."

        parts = []
        for key, label in (
            ("competitor_pricing", "PRICING"),
            ("product_updates", "PRODUCT UPDATES"),
            ("market_signals", "MARKET SIGNALS"),
            ("trends", "TRENDS"),
        ):
            items = previous_analysis.get(key, [])
            if not items:
                continue
            parts.append(f"{label}:")
            for item in items:
                detail = item.get("detail") or item.get("update") or item.get("signal") or item.get("trend") or ""
                parts.append(f"  - {item.get('company', '')} {detail}".strip())
        return "\n".join(parts) if parts else "Previous briefing had no structured findings."

    def _parse_analysis(self, content: str) -> Dict[str, Any]:
        """Parse LLM output into structured analysis dict."""
        import re

        # Try direct JSON parse
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block from markdown code fences
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Return empty structure with raw content for debugging
        print("[Analyst] Could not parse analysis JSON. Returning raw.")
        return {
            **self._empty_analysis(),
            "raw_response": content[:2000],
        }

    @staticmethod
    def _empty_analysis() -> Dict[str, Any]:
        return {
            "competitor_pricing": [],
            "product_updates": [],
            "market_signals": [],
            "trends": [],
            "removed_claims": [],
            "governance_violations": [],
            "changes_since_last_briefing": {"new": [], "updated": [], "unchanged_count": 0},
        }