"""
workflow.py
-----------
LangGraph Workflow Orchestration for the Competitive Intelligence Briefing Crew.

Pipeline:
  START → supervisor_plan → research → analyze → write → END

State machine using LangGraph's StateGraph:
- Each node is one agent's execution step
- Step counter enforced at every transition
- Partial failures are captured in state and passed forward
"""

from __future__ import annotations

import os
import time
from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from agents.supervisor import SupervisorAgent
from agents.researcher import ResearcherAgent
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent
from tools.rag import RAGTool
from tools.web_search import SourceDocument

load_dotenv()

MAX_STEPS = int(os.getenv("MAX_STEPS", 40))


# ──────────────────────────────────────────────
# Shared State Definition
# ──────────────────────────────────────────────

class WorkflowState(TypedDict):
    """The shared state that flows through the LangGraph pipeline."""
    # Input
    topic: str

    # Planning
    search_queries: List[str]

    # Research
    sources: List[Dict[str, Any]]          # Serialised SourceDocument dicts
    failed_sources: List[Dict[str, Any]]

    # Analysis
    analysis: Dict[str, Any]

    # Report
    report: str

    # Governance
    governance_flags: List[str]

    # Execution tracking
    step_count: int
    start_time: float
    elapsed_seconds: float
    status: str                            # "running" | "completed" | "stopped_step_limit" | "error"
    errors: List[str]

    # Agent trace (for evaluation dashboard)
    agent_trace: List[Dict[str, Any]]


# ──────────────────────────────────────────────
# Node Implementations
# ──────────────────────────────────────────────

def supervisor_plan_node(state: WorkflowState) -> WorkflowState:
    """Step 1 — Supervisor plans the search queries."""
    step = state["step_count"] + 1
    trace = state["agent_trace"] + [{"step": step, "agent": "Supervisor", "action": "planning"}]
    print(f"\n[Workflow] Step {step}: Supervisor planning for topic: {state['topic']}")

    if not _check_steps(step, state):
        return {**state, "step_count": step, "agent_trace": trace, "status": "stopped_step_limit"}

    try:
        supervisor = SupervisorAgent()
        queries = supervisor.plan(state["topic"])
        print(f"[Workflow] Supervisor generated {len(queries)} search queries.")
        trace[-1]["result"] = f"Generated {len(queries)} queries"
        return {
            **state,
            "search_queries": queries,
            "step_count": step,
            "agent_trace": trace,
        }
    except Exception as e:
        errors = state["errors"] + [f"Supervisor error: {str(e)}"]
        trace[-1]["error"] = str(e)
        return {
            **state,
            "step_count": step,
            "errors": errors,
            "status": "error",
            "agent_trace": trace,
        }


def research_node(state: WorkflowState) -> WorkflowState:
    """Step 2 — Researcher collects web sources."""
    step = state["step_count"] + 1
    trace = state["agent_trace"] + [{"step": step, "agent": "Researcher", "action": "web_search"}]
    print(f"\n[Workflow] Step {step}: Researcher starting web search...")

    if not _check_steps(step, state):
        return {**state, "step_count": step, "agent_trace": trace, "status": "stopped_step_limit"}

    try:
        researcher = ResearcherAgent()
        rag = RAGTool()

        docs, failures = researcher.research(state["search_queries"])

        # Store in RAG
        chunks_stored = researcher.store_in_rag(rag)
        print(f"[Workflow] Researcher stored {chunks_stored} chunks in RAG.")

        # Serialise SourceDocument objects to dicts
        serialised = [d.to_dict() for d in docs]

        trace[-1]["result"] = f"{len(docs)} sources, {len(failures)} failures"
        return {
            **state,
            "sources": serialised,
            "failed_sources": failures,
            "step_count": step,
            "agent_trace": trace,
        }
    except Exception as e:
        errors = state["errors"] + [f"Researcher error: {str(e)}"]
        trace[-1]["error"] = str(e)
        return {
            **state,
            "step_count": step,
            "errors": errors,
            "status": "error",
            "agent_trace": trace,
        }


def analyze_node(state: WorkflowState) -> WorkflowState:
    """Step 3 — Analyst processes collected sources."""
    step = state["step_count"] + 1
    trace = state["agent_trace"] + [{"step": step, "agent": "Analyst", "action": "analysis"}]
    print(f"\n[Workflow] Step {step}: Analyst processing {len(state['sources'])} sources...")

    if not _check_steps(step, state):
        return {**state, "step_count": step, "agent_trace": trace, "status": "stopped_step_limit"}

    try:
        analyst = AnalystAgent()
        rag = RAGTool()

        # Reconstruct lightweight source objects from serialised dicts
        docs = [_dict_to_source(d) for d in state["sources"]]

        analysis = analyst.analyze(docs, state["topic"], rag_tool=rag)

        # The Analyst catches its own LLM-call failures and returns an
        # empty-but-valid structure with an "error" key rather than raising —
        # surface that here so it isn't silently treated as a clean run.
        errors = state["errors"]
        if analysis.get("error"):
            errors = errors + [f"Analyst error: {analysis['error']}"]
            print(f"[Workflow] ⚠ Analyst returned an error: {analysis['error']}")

        governance_flags = [
            v.get("claim", "") for v in analysis.get("governance_violations", [])
        ]

        removed_count = len(analysis.get("removed_claims", []))
        violations_count = len(analysis.get("governance_violations", []))
        trace[-1]["result"] = (
            f"Pricing: {len(analysis.get('competitor_pricing', []))}, "
            f"Updates: {len(analysis.get('product_updates', []))}, "
            f"Signals: {len(analysis.get('market_signals', []))}, "
            f"Removed: {removed_count}, Violations: {violations_count}"
        )

        return {
            **state,
            "analysis": analysis,
            "governance_flags": governance_flags,
            "step_count": step,
            "errors": errors,
            "agent_trace": trace,
        }
    except Exception as e:
        errors = state["errors"] + [f"Analyst error: {str(e)}"]
        trace[-1]["error"] = str(e)
        return {
            **state,
            "step_count": step,
            "errors": errors,
            "status": "error",
            "agent_trace": trace,
        }


def write_node(state: WorkflowState) -> WorkflowState:
    """Step 4 — Writer generates the final report."""
    step = state["step_count"] + 1
    trace = state["agent_trace"] + [{"step": step, "agent": "Writer", "action": "report_generation"}]
    print(f"\n[Workflow] Step {step}: Writer generating final report...")

    if not _check_steps(step, state):
        return {**state, "step_count": step, "agent_trace": trace, "status": "stopped_step_limit"}

    try:
        writer = WriterAgent()
        elapsed = time.time() - state["start_time"]

        metadata = {
            "total_sources": len(state["sources"]),
            "failed_sources": len(state["failed_sources"]),
            "step_count": step,
            "elapsed_seconds": elapsed,
            "governance_flags": state["governance_flags"],
        }

        report = writer.write_report(
            topic=state["topic"],
            analysis=state["analysis"],
            metadata=metadata,
        )

        citation_count = writer.count_citations(report)
        trace[-1]["result"] = f"Report: {len(report)} chars, {citation_count} citations"

        return {
            **state,
            "report": report,
            "elapsed_seconds": elapsed,
            "step_count": step,
            "status": "completed",
            "agent_trace": trace,
        }
    except Exception as e:
        errors = state["errors"] + [f"Writer error: {str(e)}"]
        trace[-1]["error"] = str(e)
        return {
            **state,
            "step_count": step,
            "errors": errors,
            "status": "error",
            "elapsed_seconds": time.time() - state["start_time"],
            "agent_trace": trace,
        }


# ──────────────────────────────────────────────
# Routing Logic
# ──────────────────────────────────────────────

def route_after_planning(state: WorkflowState) -> str:
    """Route after supervisor planning — halt if step limit or error."""
    if state["status"] in ("stopped_step_limit", "error"):
        return END
    return "research"


def route_after_research(state: WorkflowState) -> str:
    """Route after research — continue even if some sources failed."""
    if state["status"] in ("stopped_step_limit", "error"):
        return END
    if not state["sources"]:
        # No sources at all — skip analysis and write an empty report
        print("[Workflow] No sources collected. Skipping analysis.")
        return END
    return "analyze"


def route_after_analysis(state: WorkflowState) -> str:
    """Route after analysis."""
    if state["status"] in ("stopped_step_limit", "error"):
        return END
    return "write"


def route_after_writing(state: WorkflowState) -> str:
    """Route after writing — always end."""
    return END


# ──────────────────────────────────────────────
# Graph Assembly
# ──────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """Assemble and compile the LangGraph workflow."""
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("supervisor_plan", supervisor_plan_node)
    graph.add_node("research", research_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("write", write_node)

    # Set entry point
    graph.set_entry_point("supervisor_plan")

    # Add conditional edges
    graph.add_conditional_edges("supervisor_plan", route_after_planning)
    graph.add_conditional_edges("research", route_after_research)
    graph.add_conditional_edges("analyze", route_after_analysis)
    graph.add_conditional_edges("write", route_after_writing)

    return graph.compile()


# ──────────────────────────────────────────────
# Public Entry Point
# ──────────────────────────────────────────────

def run_workflow(topic: str) -> Dict[str, Any]:
    """
    Run the full competitive intelligence workflow for a topic.

    Args:
        topic: The competitive intelligence research topic

    Returns:
        Final WorkflowState as a plain dict
    """
    print(f"\n{'='*60}")
    print(f"  Competitive Intelligence Briefing Crew")
    print(f"  Topic: {topic}")
    print(f"{'='*60}\n")

    initial_state: WorkflowState = {
        "topic": topic,
        "search_queries": [],
        "sources": [],
        "failed_sources": [],
        "analysis": {},
        "report": "",
        "governance_flags": [],
        "step_count": 0,
        "start_time": time.time(),
        "elapsed_seconds": 0.0,
        "status": "running",
        "errors": [],
        "agent_trace": [],
    }

    workflow = build_workflow()

    try:
        final_state = workflow.invoke(initial_state)
    except Exception as e:
        print(f"[Workflow] Fatal error: {e}")
        final_state = {
            **initial_state,
            "status": "error",
            "errors": [str(e)],
            "elapsed_seconds": time.time() - initial_state["start_time"],
        }

    status = final_state.get("status", "unknown")
    elapsed = final_state.get("elapsed_seconds", 0.0)
    print(f"\n[Workflow] Completed — Status: {status}, Time: {elapsed:.1f}s")
    return final_state


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _check_steps(step: int, state: WorkflowState) -> bool:
    """Return False (and update status) if MAX_STEPS is exceeded."""
    if step > MAX_STEPS:
        print(f"[Workflow] ⚠ Step limit ({MAX_STEPS}) exceeded at step {step}. Halting.")
        state["status"] = "stopped_step_limit"
        return False
    return True


def _dict_to_source(d: dict):
    """Convert a serialised source dict back to a lightweight source object."""
    from tools.web_search import SourceDocument
    return SourceDocument(
        title=d.get("title", ""),
        url=d.get("url", ""),
        content=d.get("content", ""),
        published_date=d.get("published_date"),
        retrieved_at=d.get("retrieved_at", ""),
        score=d.get("score", 0.0),
    )