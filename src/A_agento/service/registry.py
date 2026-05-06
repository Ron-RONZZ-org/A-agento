"""Runtime-detected service registry for cross-module access.

Lazy-loads services from optional A-modules:
- A-lien (email)
- A-organizi (calendar, todos)
- A-encik (knowledge)
"""

from __future__ import annotations

# Cross-module singletons
_a_lien = None
_kalendaro_service = None
_todo_service = None
_encik_service = None


def get_lien_service():
    """Get RetpostoService from A-lien if available."""
    global _a_lien
    if _a_lien is None:
        try:
            from A_lien.service import get_retposto_service

            _a_lien = get_retposto_service()
        except ImportError:
            pass
    return _a_lien


def get_calendar_service():
    """Get EventService from A-organizi if available."""
    global _kalendaro_service
    if _kalendaro_service is None:
        try:
            from A_organizi.service import get_kalendaro_service

            _kalendaro_service = get_kalendaro_service()
        except ImportError:
            pass
    return _kalendaro_service


def get_todo_service():
    """Get TodoService from A-organizi if available."""
    global _todo_service
    if _todo_service is None:
        try:
            from A_organizi.service import get_todo_service

            _todo_service = get_todo_service()
        except ImportError:
            pass
    return _todo_service


def get_encik_service():
    """Get EncikService from A-encik if available."""
    global _encik_service
    if _encik_service is None:
        try:
            from A_encik.service import get_service

            _encik_service = get_service()
        except ImportError:
            pass
    return _encik_service


__all__ = [
    "get_lien_service",
    "get_calendar_service",
    "get_todo_service",
    "get_encik_service",
]
