from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ConversationState:
    conversation_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    merchant_url: Optional[str] = None
    ucp_profile: Optional[dict] = None
    mcp_endpoint: Optional[str] = None
    capabilities_intersection: list = field(default_factory=list)

    merchant_tools: list = field(default_factory=list)  # raw MCP tool schemas from tools/list

    cart_id: Optional[str] = None
    checkout_id: Optional[str] = None
    checkout_status: Optional[str] = None
    checkout_total_minor: int = 0
    checkout_currency: str = "USD"

    history: list = field(default_factory=list)


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, ConversationState] = {}

    def get_or_create(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = ConversationState(conversation_id=conversation_id)
        return self._sessions[conversation_id]

    def get(self, conversation_id: str) -> Optional[ConversationState]:
        return self._sessions.get(conversation_id)


store = SessionStore()
