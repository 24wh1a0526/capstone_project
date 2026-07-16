"""
writer.py
---------
Writer Agent:
- Takes structured analysis from the Analyst
- Generates a professional competitive intelligence briefing
- Every factual statement MUST contain a citation
- Report sections: Executive Summary, Competitor Pricing, Product Updates,
  Market Signals, Recommendations, References, Run Metadata
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class WriterAgent:
    """
    Generates a professional competitive intelligence report from analysis.

    The writer enforces citation requirements — any claim without a citation
    is replaced with the governance notice:
    "Unverified information — omitted from final report."
    """

    SYSTEM_PROMPT = """You are a Senior Competitive Intelligence Report Writer.

Write a professional, structured competitive intelligence briefing based on the
provided research analysis. Follow STRICT governance rules:

GOVERNANCE RULES:
1. Every factual statement MUST include an inline citation: [Source: Title](URL)
2. NEVER fabricate facts, statistics, or quotes.
3. If information cannot be verified from the provided data, write:
   "Unverified information — omitted from final report."
4. Do NOT include rumors, gossip, speculation, or bankruptcy claims
   unless they are from official, verifiable sources.
5. Use professional business language throughout.

REPORT STRUCTURE (use these exact section headers with ##):

## Executive Summary
A 3–5 sentence overview of the competitive landscape. Include key findings.

## Competitor Pricing
Detail each competitor's pricing tiers and plans. Cite every figure.

## Competitor Product Updates
Recent product launches, feature releases, and roadmap announcements. Cite each.

## Market Signals
Industry trends, technology shifts, and strategic signals. Cite each.

## Strategic Recommendations
3–5 actionable recommendations based ONLY on verified findings.

## References
Numbered list of all cited sources with title and URL.

## Run Metadata
- Topic: ...
- Report generated: ...
- Sources used: ...
- Failed sources: ...
- Step count: ...

Produce the report in clean Markdown format.
"""

    def __init__(self, model: Optional[str] = None):
        self.model = model or OPENROUTER_MODEL
        self._llm = ChatOpenAI(
            model=self.model,
            temperature=0.3,
            max_tokens=6000,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "CI Briefing Crew"),
            },
        )
        self._last_report: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_report(
        self,
        topic: str,
        analysis: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Generate the full competitive intelligence briefing.

        Args:
            topic: Original research topic
            analysis: Structured analysis from the Analyst Agent
            metadata: Run metadata (sources, failures, elapsed time, steps)

        Returns:
            Full report as a Markdown string
        """
        analysis_text = self._format_analysis(analysis)

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Research Topic: {topic}\n\n"
                f"Analysis Data:\n{analysis_text}\n\n"
                f"Run Metadata:\n"
                f"- Sources collected: {metadata.get('total_sources', 0)}\n"
                f"- Failed sources: {metadata.get('failed_sources', 0)}\n"
                f"- Execution steps: {metadata.get('step_count', 0)}\n"
                f"- Execution time: {metadata.get('elapsed_seconds', 0):.1f}s\n"
                f"- Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                "Write the full competitive intelligence briefing report now."
            )),
        ]

        try:
            response = self._llm.invoke(messages)
            report = response.content.strip()
        except Exception as e:
            print(f"[Writer] Report generation failed: {e}")
            report = self._fallback_report(topic, analysis, metadata, str(e))

        # Post-process: ensure governance notice for any empty sections
        report = self._enforce_governance(report)
        self._last_report = report
        return report

    def count_citations(self, report: str) -> int:
        """Count the number of citations in the report."""
        import re
        # Match [Source: ...](url) or [N] or (Source: ...) patterns
        patterns = [
            r'\[Source:.*?\]\(https?://.*?\)',
            r'\[(\d+)\]\s*https?://',
            r'\[(\d+)\]',
        ]
        total = 0
        for pattern in patterns:
            total += len(re.findall(pattern, report))
        return total

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format the analysis dict into readable text for the LLM."""
        parts = []

        pricing = analysis.get("competitor_pricing", [])
        if pricing:
            parts.append("COMPETITOR PRICING:")
            for item in pricing:
                citation = item.get("citation", {})
                parts.append(
                    f"  - {item.get('company', 'Unknown')}: {item.get('detail', '')}\n"
                    f"    [Source: {citation.get('title', '')}]({citation.get('url', '')})"
                )

        updates = analysis.get("product_updates", [])
        if updates:
            parts.append("\nPRODUCT UPDATES:")
            for item in updates:
                citation = item.get("citation", {})
                parts.append(
                    f"  - {item.get('company', 'Unknown')}: {item.get('update', '')}\n"
                    f"    [Source: {citation.get('title', '')}]({citation.get('url', '')})"
                )

        signals = analysis.get("market_signals", [])
        if signals:
            parts.append("\nMARKET SIGNALS:")
            for item in signals:
                citation = item.get("citation", {})
                parts.append(
                    f"  - {item.get('signal', '')}\n"
                    f"    [Source: {citation.get('title', '')}]({citation.get('url', '')})"
                )

        trends = analysis.get("trends", [])
        if trends:
            parts.append("\nTRENDS:")
            for item in trends:
                citation = item.get("citation", {})
                parts.append(
                    f"  - {item.get('trend', '')}\n"
                    f"    [Source: {citation.get('title', '')}]({citation.get('url', '')})"
                )

        removed = analysis.get("removed_claims", [])
        if removed:
            parts.append(f"\nREMOVED CLAIMS ({len(removed)}):")
            for item in removed:
                parts.append(f"  - [{item.get('reason', 'Unverified')}] {item.get('claim', '')}")

        violations = analysis.get("governance_violations", [])
        if violations:
            parts.append(f"\nGOVERNANCE VIOLATIONS ({len(violations)}):")
            for item in violations:
                parts.append(f"  - REJECTED: {item.get('claim', '')} ({item.get('reason', '')})")

        return "\n".join(parts) if parts else "No structured analysis available."

    def _enforce_governance(self, report: str) -> str:
        """
        Post-process the report to add governance notices for empty sections.
        """
        sections_to_check = [
            "## Competitor Pricing",
            "## Competitor Product Updates",
            "## Market Signals",
        ]

        lines = report.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            result_lines.append(lines[i])

            # Check if current line is a section header we care about
            current_section = lines[i].strip()
            if current_section in sections_to_check:
                # Look ahead — if next non-empty content line is another ## header,
                # then this section is empty
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1

                if j < len(lines) and lines[j].strip().startswith("##"):
                    result_lines.append(
                        "\n*Unverified information — omitted from final report.*\n"
                    )
            i += 1

        return "\n".join(result_lines)

    def _fallback_report(
        self,
        topic: str,
        analysis: Dict[str, Any],
        metadata: Dict[str, Any],
        error: str,
    ) -> str:
        """Generate a minimal report when the LLM call fails."""
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        pricing = analysis.get("competitor_pricing", [])
        updates = analysis.get("product_updates", [])
        signals = analysis.get("market_signals", [])

        lines = [
            f"# Competitive Intelligence Briefing: {topic}",
            f"*Generated: {now}*\n",
            "## Executive Summary",
            f"Research was completed for the topic: **{topic}**. "
            f"A total of {metadata.get('total_sources', 0)} sources were analyzed. "
            "Full LLM report generation encountered an error — raw findings are shown below.\n",
        ]

        if pricing:
            lines.append("## Competitor Pricing")
            for item in pricing:
                c = item.get("citation", {})
                lines.append(
                    f"- **{item.get('company', '')}**: {item.get('detail', '')} "
                    f"([{c.get('title', '')}]({c.get('url', '')}))"
                )

        if updates:
            lines.append("\n## Competitor Product Updates")
            for item in updates:
                c = item.get("citation", {})
                lines.append(
                    f"- **{item.get('company', '')}**: {item.get('update', '')} "
                    f"([{c.get('title', '')}]({c.get('url', '')}))"
                )

        if signals:
            lines.append("\n## Market Signals")
            for item in signals:
                c = item.get("citation", {})
                lines.append(
                    f"- {item.get('signal', '')} "
                    f"([{c.get('title', '')}]({c.get('url', '')}))"
                )

        lines.extend([
            "\n## References",
            "*See individual source citations above.*",
            "\n## Run Metadata",
            f"- Topic: {topic}",
            f"- Generated: {now}",
            f"- Sources used: {metadata.get('total_sources', 0)}",
            f"- Failed sources: {metadata.get('failed_sources', 0)}",
            f"- Execution steps: {metadata.get('step_count', 0)}",
            f"- Error: {error}",
        ])

        return "\n".join(lines)