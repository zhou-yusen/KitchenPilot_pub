from collections import deque
from collections.abc import Mapping
from threading import Lock
from typing import Any
from uuid import uuid4

from kitchenpilot.schemas.enums import IntentType


class ConversationMemoryService:
    """Keep short-lived per-session conversation memory in process memory."""

    def __init__(self, max_turns: int = 8) -> None:
        """Initialize an in-memory session store."""
        self.max_turns = max_turns
        self._sessions: dict[str, deque[dict[str, object]]] = {}
        self._lock = Lock()

    def ensure_session_id(self, session_id: str | None = None) -> str:
        """Return an existing session id or create a new one."""
        clean_id = (session_id or "").strip()
        return clean_id or f"session_{uuid4().hex}"

    def load(self, session_id: str) -> list[dict[str, object]]:
        """Return recent turns for a session."""
        with self._lock:
            return [dict(turn) for turn in self._sessions.get(session_id, deque())]

    def delete(self, session_id: str) -> bool:
        """Delete one session and return whether it existed."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def save(self, state: Mapping[str, Any]) -> None:
        """Append one completed turn to a session."""
        session_id = self.ensure_session_id(state.get("session_id"))
        sources = state.get("retrieved_context", [])
        source_summaries = [
            {
                "recipe_name": source.recipe_name,
                "chunk_type": str(source.chunk_type),
                "score": source.score,
            }
            for source in sources[:3]
        ]
        turn = {
            "query": state.get("query", ""),
            "answer": state.get("final_answer", ""),
            "intent": str(state.get("intent", IntentType.FALLBACK)),
            "recommendation_type": (
                str(state.get("recommendation_type"))
                if state.get("recommendation_type")
                else None
            ),
            "active_recipe": state.get("active_recipe"),
            "rewritten_query": state.get("rewritten_query"),
            "is_follow_up": state.get("is_follow_up", False),
            "sources": source_summaries,
        }
        with self._lock:
            session = self._sessions.setdefault(session_id, deque(maxlen=self.max_turns))
            session.append(turn)

    def last_active_recipe(self, session_id: str) -> str | None:
        """Return the latest recipe QA active recipe for a session."""
        for turn in reversed(self.load(session_id)):
            if turn.get("intent") == str(IntentType.RECIPE_QA) and turn.get("active_recipe"):
                return str(turn["active_recipe"])
        return None

    def clear(self) -> None:
        """Clear all sessions. Intended for tests."""
        with self._lock:
            self._sessions.clear()


conversation_memory_service = ConversationMemoryService()
