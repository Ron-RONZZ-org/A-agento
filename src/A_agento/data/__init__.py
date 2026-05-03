"""Data package for A-agento."""

from A_agento.data.storage import (
    get_db,
    close_db,
    add_history,
    get_history,
    list_history,
    delete_history,
    clear_history,
    add_template,
    get_template,
    list_templates,
    update_template,
    delete_template,
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
]