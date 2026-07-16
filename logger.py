"""
logger.py
---------
Logging system for the Competitive Intelligence Briefing Crew.

Saves:
  - logs/research_log.json      — sources collected and failed sources
  - logs/analysis_log.json      — structured analysis output
  - logs/writer_log.json        — report metadata and governance summary
  - logs/execution_trace.json   — full agent trace and workflow state

All logs are timestamped. Existing logs are appended (not overwritten),
keeping a complete audit trail.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

LOG_DIR = Path(os.getenv("LOG_DIR", "./logs")).resolve()


def _ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_existing(path: Path) -> List[Dict]:
    """Load existing log entries (returns empty list if file missing/corrupt)."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _write_log(path: Path, entries: List[Dict]):
    """Write log entries to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, default=str, ensure_ascii=False)


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ──────────────────────────────────────────────
# Individual Log Writers
# ──────────────────────────────────────────────

def save_research_log(result: Dict[str, Any], topic: str):
    """
    Save research phase data to research_log.json.
    Includes: topic, sources collected, failed sources, query list.
    """
    _ensure_log_dir()
    path = LOG_DIR / "research_log.json"
    entries = _load_existing(path)

    entry = {
        "timestamp": _timestamp(),
        "topic": topic,
        "total_sources": len(result.get("sources", [])),
        "failed_sources_count": len(result.get("failed_sources", [])),
        "search_queries": result.get("search_queries", []),
        "sources": [
            {
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "published_date": s.get("published_date", ""),
                "content_length": len(s.get("content", "")),
                "score": s.get("score", 0),
            }
            for s in result.get("sources", [])
        ],
        "failed_sources": result.get("failed_sources", []),
    }

    entries.append(entry)
    _write_log(path, entries)
    print(f"[Logger] Research log saved: {path}")


def save_analysis_log(result: Dict[str, Any], topic: str):
    """
    Save analysis phase data to analysis_log.json.
    Includes: topic, structured analysis, removed claims, governance violations.
    """
    _ensure_log_dir()
    path = LOG_DIR / "analysis_log.json"
    entries = _load_existing(path)

    analysis = result.get("analysis", {})
    entry = {
        "timestamp": _timestamp(),
        "topic": topic,
        "competitor_pricing_count": len(analysis.get("competitor_pricing", [])),
        "product_updates_count": len(analysis.get("product_updates", [])),
        "market_signals_count": len(analysis.get("market_signals", [])),
        "trends_count": len(analysis.get("trends", [])),
        "removed_claims_count": len(analysis.get("removed_claims", [])),
        "governance_violations_count": len(analysis.get("governance_violations", [])),
        "analysis": analysis,
        "governance_flags": result.get("governance_flags", []),
    }

    entries.append(entry)
    _write_log(path, entries)
    print(f"[Logger] Analysis log saved: {path}")


def save_writer_log(result: Dict[str, Any], topic: str):
    """
    Save writer phase data to writer_log.json.
    Includes: topic, report word count, citation count, governance summary.
    """
    _ensure_log_dir()
    path = LOG_DIR / "writer_log.json"
    entries = _load_existing(path)

    report = result.get("report", "")
    # Count citations
    import re
    citation_count = len(re.findall(r'\[Source:.*?\]\(https?://.*?\)', report))
    citation_count += len(re.findall(r'\[(\d+)\]', report))

    entry = {
        "timestamp": _timestamp(),
        "topic": topic,
        "report_word_count": len(report.split()),
        "report_char_count": len(report),
        "citation_count": citation_count,
        "governance_flags": result.get("governance_flags", []),
        "removed_claims": result.get("analysis", {}).get("removed_claims", []),
        "governance_violations": result.get("analysis", {}).get("governance_violations", []),
        "status": result.get("status", "unknown"),
        "errors": result.get("errors", []),
    }

    entries.append(entry)
    _write_log(path, entries)
    print(f"[Logger] Writer log saved: {path}")


def save_execution_trace(result: Dict[str, Any], topic: str):
    """
    Save full execution trace to execution_trace.json.
    Includes: full agent trace, workflow state, timing, step count.
    """
    _ensure_log_dir()
    path = LOG_DIR / "execution_trace.json"
    entries = _load_existing(path)

    entry = {
        "timestamp": _timestamp(),
        "topic": topic,
        "status": result.get("status", "unknown"),
        "step_count": result.get("step_count", 0),
        "elapsed_seconds": result.get("elapsed_seconds", 0),
        "errors": result.get("errors", []),
        "agent_trace": result.get("agent_trace", []),
        "search_queries": result.get("search_queries", []),
        "total_sources": len(result.get("sources", [])),
        "failed_sources_count": len(result.get("failed_sources", [])),
        "governance_flags": result.get("governance_flags", []),
    }

    entries.append(entry)
    _write_log(path, entries)
    print(f"[Logger] Execution trace saved: {path}")


# ──────────────────────────────────────────────
# Master Save Function
# ──────────────────────────────────────────────

def save_all_logs(result: Dict[str, Any], topic: str):
    """
    Save all four log files for a completed workflow run.

    Args:
        result: The final workflow state dict from run_workflow()
        topic: The research topic string
    """
    try:
        save_research_log(result, topic)
    except Exception as e:
        print(f"[Logger] Warning: research_log failed: {e}")

    try:
        save_analysis_log(result, topic)
    except Exception as e:
        print(f"[Logger] Warning: analysis_log failed: {e}")

    try:
        save_writer_log(result, topic)
    except Exception as e:
        print(f"[Logger] Warning: writer_log failed: {e}")

    try:
        save_execution_trace(result, topic)
    except Exception as e:
        print(f"[Logger] Warning: execution_trace failed: {e}")

    print(f"[Logger] All logs saved to: {LOG_DIR}")


def load_log(log_name: str) -> List[Dict]:
    """
    Load a specific log file by name.

    Args:
        log_name: One of 'research', 'analysis', 'writer', 'execution_trace'

    Returns:
        List of log entry dicts
    """
    filename_map = {
        "research": "research_log.json",
        "analysis": "analysis_log.json",
        "writer": "writer_log.json",
        "execution_trace": "execution_trace.json",
    }
    filename = filename_map.get(log_name, f"{log_name}.json")
    path = LOG_DIR / filename
    return _load_existing(path)
