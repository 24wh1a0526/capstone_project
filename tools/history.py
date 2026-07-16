"""
history.py
----------
Briefing history store.

- Persists every completed run (report + structured analysis + metadata)
  to disk as JSON, keyed by a normalised topic key.
- Lets the workflow look up the most recent prior briefing(s) for the
  same topic so the Analyst/Writer can flag what changed.

This is intentionally file-based (no DB dependency) so it drops into
the existing project with zero new infrastructure. Swap _HistoryBackend
for a DB-backed one later without touching the call sites.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

HISTORY_DIR = os.getenv("BRIEFING_HISTORY_DIR", "./logs/briefings")


def _topic_key(topic: str) -> str:
    """Stable, filesystem-safe key for a topic (case/whitespace-insensitive)."""
    normalized = " ".join(topic.lower().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


class HistoryStore:
    """
    Reads and writes past briefings to a local JSON-file store.

    Usage:
        history = HistoryStore()
        previous = history.get_latest(topic)          # dict or None
        history.save(topic, report, analysis, metadata)
    """

    def __init__(self, directory: Optional[str] = None):
        self.directory = directory or HISTORY_DIR

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(
        self,
        topic: str,
        report: str,
        analysis: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Persist a completed briefing run.

        Returns:
            The path the briefing was written to.
        """
        os.makedirs(self.directory, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        key = _topic_key(topic)
        filename = f"{key}__{timestamp}.json"
        path = os.path.join(self.directory, filename)

        record = {
            "topic": topic,
            "topic_key": key,
            "generated_at": timestamp,
            "report": report,
            "analysis": analysis,
            "metadata": metadata,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, default=str)
        except Exception as e:
            print(f"[History] Failed to save briefing: {e}")
            return ""

        print(f"[History] Saved briefing for '{topic}' -> {path}")
        return path

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_for_topic(self, topic: str) -> List[str]:
        """Return filenames for a topic, most recent first."""
        if not os.path.isdir(self.directory):
            return []
        key = _topic_key(topic)
        matches = [
            f for f in os.listdir(self.directory)
            if f.startswith(f"{key}__") and f.endswith(".json")
        ]
        return sorted(matches, reverse=True)

    def get_latest(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Return the most recent prior briefing record for this topic,
        or None if there isn't one yet (e.g. first run).
        """
        matches = self.list_for_topic(topic)
        if not matches:
            return None
        return self._load(matches[0])

    def get_recent(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Return up to `limit` prior briefings for this topic, most recent first."""
        matches = self.list_for_topic(topic)[:limit]
        records = []
        for fname in matches:
            record = self._load(fname)
            if record:
                records.append(record)
        return records

    def _load(self, filename: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.directory, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[History] Failed to load {path}: {e}")
            return None