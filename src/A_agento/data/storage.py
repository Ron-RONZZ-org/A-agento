"""SQLite storage for A-agento.

Provides database for agent metadata, prompt templates, and generation history.
"""

from __future__ import annotations

from A_agento.data._storage_base import get_db, close_db
from A_agento.data._storage_history import (
    add_history,
    get_history,
    list_history,
    delete_history,
    clear_history,
)
from A_agento.data._storage_templates import (
    add_template,
    get_template,
    list_templates,
    update_template,
    delete_template,
)
from A_agento.data._storage_samples import (
    add_style_sample,
    get_active_samples,
    list_style_samples,
    delete_style_sample,
    set_sample_active,
    search_similar_samples,
)

__all__ = [
    "get_db",
    "close_db",
    "add_history",
    "get_history",
    "list_history",
    "delete_history",
    "clear_history",
    "add_template",
    "get_template",
    "list_templates",
    "update_template",
    "delete_template",
    "add_style_sample",
    "get_active_samples",
    "list_style_samples",
    "delete_style_sample",
    "set_sample_active",
    "search_similar_samples",
]
