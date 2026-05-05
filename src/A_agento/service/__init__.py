"""AgentService — orchestration for AI-powered email assistance.

Coordinates between LLM providers and A modules (email, calendar, todos, knowledge).

Service contract with A-lien is documented in contract.py.

Usage:
    from A_agento.service import get_agent_service

    agent = get_agent_service()
    summaries = agent.summarize_emails(provider, unread_only=True)
    reply = agent.generate_reply(provider, email_uuid, tone="courteous")
    actions = agent.extract_actions(provider, email_uuid)
"""

from __future__ import annotations

from A_agento.service.agent_service import AgentService
from A_agento.service.helpers import EmailSummary, ActionSuggestion

# Singleton
_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    """Get the singleton AgentService.

    Returns:
        AgentService instance
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service


__all__ = [
    "AgentService",
    "EmailSummary",
    "ActionSuggestion",
    "get_agent_service",
]
