"""ActionMixin — execute AI-suggested actions (calendar, todo, knowledge).

Mixed into AgentService to provide write operations with
cross-module integration.
"""

from __future__ import annotations

import json
from typing import Any

from A import info, tr_multi

from A_agento.service.registry import (
    get_calendar_service,
    get_todo_service,
    get_encik_service,
)


class ActionMixin:
    """Mixin providing action execution for calendar, todo, and knowledge."""

    def create_calendar_event(
        self, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create calendar event (requires external confirmation).

        Args:
            metadata: Event metadata from action extraction

        Returns:
            Created event dict or None
        """
        cal_service = get_calendar_service()
        if cal_service is None:
            info(
                tr_multi(
                    "A-organizi ne estas instalita.",
                    "A-organizi is not installed.",
                    "A-organizi n'est pas installé.",
                )
            )
            return None

        event_data = {
            "titolo": metadata.get("title", ""),
            "komenco": metadata.get("start", ""),
            "fino": metadata.get("end", ""),
            "priskribo": metadata.get("description", ""),
            "loko": metadata.get("location", ""),
            "ripeto": metadata.get("ripeto", ""),
        }
        return cal_service.create(event_data)

    @staticmethod
    def _parse_remind_offset(remind_str: str) -> int | None:
        """Parse reminder offset string to seconds.

        Args:
            remind_str: String like "15m", "1h", "1d"

        Returns:
            Negative seconds before event, or None if invalid
        """
        import re

        match = re.match(r"^(\d+)(m|h|d)$", remind_str.strip().lower())
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "m":
            return -value * 60
        elif unit == "h":
            return -value * 3600
        elif unit == "d":
            return -value * 86400
        return None

    def create_todo(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Create todo (requires external confirmation).

        Args:
            metadata: Todo metadata from action extraction

        Returns:
            Created todo dict or None
        """
        try:
            todo_service = get_todo_service()
        except ImportError:
            info(
                tr_multi(
                    "A-organizi ne estas instalita.",
                    "A-organizi is not installed.",
                    "A-organizi n'est pas installé.",
                )
            )
            return None

        todo_data = {
            "titolo": metadata.get("title", ""),
            "prioritato": metadata.get("priority", "normal"),
            "deveno": metadata.get("due", ""),
        }
        return todo_service.create(todo_data)

    @staticmethod
    def _resolve_refs(metadata: dict[str, Any]) -> list[str]:
        """Resolve vt# and ec# references to full UUIDs.

        Args:
            metadata: Knowledge entry metadata

        Returns:
            List of resolved UUIDs
        """
        import re

        resolved: list[str] = []
        text = json.dumps(metadata)

        vt_pattern = re.compile(r"vt#([a-f0-9]+)")
        for match in vt_pattern.finditer(text):
            prefix = match.group(1)
            try:
                from A_vorto.service import get_service

                svc = get_service()
                entries = svc.list(limit=10)
                for e in entries:
                    if e.get("uuid", "").startswith(prefix):
                        resolved.append(e["uuid"])
                        break
            except (ImportError, AttributeError):
                pass

        ec_pattern = re.compile(r"ec#([a-f0-9]+)")
        for match in ec_pattern.finditer(text):
            prefix = match.group(1)
            try:
                from A_encik.service import get_service

                svc = get_service()
                entries = svc.list(limit=10)
                for e in entries:
                    if e.get("uuid", "").startswith(prefix):
                        resolved.append(e["uuid"])
                        break
            except (ImportError, AttributeError):
                pass

        return list(dict.fromkeys(resolved))

    @staticmethod
    def _find_potential_links(
        metadata: dict[str, Any],
    ) -> list[str]:
        """Find potential semantic links by keyword matching.

        Args:
            metadata: Knowledge entry metadata

        Returns:
            List of UUIDs that might be related
        """
        links: list[str] = []
        title = (metadata.get("title") or "").strip()
        content = (metadata.get("content") or "").strip()

        if not title:
            return links

        words = set()
        for word in title.split():
            clean = word.strip(".,!?;:()[]{}").lower()
            if len(clean) > 3:
                words.add(clean)

        if not words:
            return links

        try:
            from A_encik.service import get_service

            svc = get_service()
            entries = svc.list(limit=50)
            for entry in entries:
                entry_text = (
                    entry.get("titolo", "") + " " + entry.get("enhavo", "")
                ).lower()
                for word in words:
                    if word in entry_text and entry.get("uuid") not in links:
                        links.append(entry["uuid"])
                        break
        except (ImportError, AttributeError):
            pass

        return links[:10]

    def create_knowledge_entry(
        self, metadata: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create knowledge entry (requires external confirmation).

        Args:
            metadata: Knowledge metadata from action extraction

        Returns:
            Created entry dict or None
        """
        encik_service = get_encik_service()
        if encik_service is None:
            info(
                tr_multi(
                    "A-encik ne estas instalita.",
                    "A-encik is not installed.",
                    "A-encik n'est pas installé.",
                )
            )
            return None

        resolved = self._resolve_refs(metadata)
        potential = self._find_potential_links(metadata)
        ligilo = list(dict.fromkeys(resolved + potential))[:10]

        superklaso = metadata.get("superklaso", [])
        if isinstance(superklaso, str):
            superklaso = [superklaso]

        entry_data: dict[str, Any] = {
            "titolo": metadata.get("title", ""),
            "enhavo": metadata.get("content", ""),
        }
        if ligilo:
            entry_data["ligilo"] = ligilo
        if superklaso:
            entry_data["superklaso"] = superklaso

        result = encik_service.create(entry_data)
        return result


__all__ = [
    "ActionMixin",
]
