"""
supervisor.py
-------------
Supervisor Agent:
- Receives the research topic
- Plans execution by generating targeted search queries
- Delegates work to Researcher → Analyst → Writer
- Monitors step count and halts if MAX_STEPS is exceeded
- Reports governance violations and failed sources
"""

from __future__ import annotations

import os
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

MAX_STEPS = int(os.getenv("MAX_STEPS", 40))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class SupervisorAgent:
    """
    Plans the research workflow and enforces execution limits.

    The Supervisor does NOT perform research itself — it generates the
    search query plan and monitors the overall execution state.
    """

    SYSTEM_PROMPT = """You are a Senior Competitive Intelligence Supervisor.

Your responsibilities:
1. Receive a research topic from the user
2. Generate a precise, targeted set of search queries to cover:
   - Competitor pricing and plans
   - Recent product launches and feature updates
   - Market trends and industry signals
   - Key players and their strategic moves
3. Return 5–8 distinct, specific search queries — not generic ones.
4. Do NOT include rumors, speculation, or unverified claims in your plan.

Output format (JSON array of query strings):
["query 1", "query 2", "query 3", ...]
"""

    def __init__(self, model: Optional[str] = None):
        self.model = model or OPENROUTER_MODEL
        self.max_steps = MAX_STEPS
        self._llm = ChatOpenAI(
            model=self.model,
            temperature=0.2,
            max_tokens=1024,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "CI Briefing Crew"),
            },
        )

    def plan(self, topic: str) -> List[str]:
        """
        Generate a list of targeted search queries for the topic.

        Args:
            topic: The competitive intelligence research topic

        Returns:
            List of search query strings
        """
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=f"Research topic: {topic}"),
        ]

        try:
            response = self._llm.invoke(messages)
            content = response.content.strip()
            queries = self._parse_queries(content)
            return queries
        except Exception as e:
            # Fallback to simple queries if LLM call fails
            print(f"[Supervisor] Plan generation failed: {e}. Using fallback queries.")
            return self._fallback_queries(topic)

    def check_step_limit(self, current_step: int) -> bool:
        """
        Check whether execution should continue.

        Args:
            current_step: The current step count

        Returns:
            True if execution should continue, False if limit reached
        """
        if current_step >= self.max_steps:
            print(
                f"[Supervisor] Step limit reached ({current_step}/{self.max_steps}). "
                "Halting execution to prevent infinite loop."
            )
            return False
        return True

    def assess_governance(self, claims: List[str]) -> dict:
        """
        Review a list of factual claims and flag any that lack citations
        or appear to be hallucinated/speculative.

        Args:
            claims: List of claim strings from the analyst/writer

        Returns:
            dict with 'approved', 'rejected', and 'warnings' lists
        """
        if not claims:
            return {"approved": [], "rejected": [], "warnings": []}

        messages = [
            SystemMessage(content=(
                "You are a governance reviewer. For each claim below, determine if it is:\n"
                "- APPROVED: Factual and likely verifiable\n"
                "- REJECTED: Speculative, rumor, or hallucinated\n"
                "Return a JSON object with keys 'approved', 'rejected', 'warnings'.\n"
                "Each value is a list of claim strings.\n"
                "IMPORTANT: Never approve claims about bankruptcy, legal issues, or "
                "personal scandals unless they are cited facts."
            )),
            HumanMessage(content="\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))),
        ]

        try:
            response = self._llm.invoke(messages)
            import json
            result = json.loads(response.content.strip())
            return result
        except Exception:
            # If governance check fails, approve all with a warning
            return {
                "approved": claims,
                "rejected": [],
                "warnings": ["Governance check failed — manual review recommended."],
            }

    def _parse_queries(self, content: str) -> List[str]:
        """Parse LLM output into a list of query strings."""
        import json
        import re

        # Try direct JSON parse
        try:
            queries = json.loads(content)
            if isinstance(queries, list):
                return [q for q in queries if isinstance(q, str) and q.strip()]
        except json.JSONDecodeError:
            pass

        # Try extracting JSON array from mixed content
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            try:
                queries = json.loads(match.group())
                if isinstance(queries, list):
                    return [q for q in queries if isinstance(q, str) and q.strip()]
            except json.JSONDecodeError:
                pass

        # Last resort: split by newlines
        lines = [line.strip().strip('"').strip("'").strip("-").strip()
                 for line in content.splitlines() if line.strip()]
        return [l for l in lines if len(l) > 5][:8]

    @staticmethod
    def _fallback_queries(topic: str) -> List[str]:
        """Generate basic queries when the LLM is unavailable."""
        return [
            f"{topic} pricing plans 2024",
            f"{topic} competitors comparison",
            f"{topic} product updates news",
            f"{topic} market trends",
            f"{topic} key players analysis",
        ]