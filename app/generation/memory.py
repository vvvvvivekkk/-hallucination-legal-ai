from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from ..core.utils import now_iso


@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class ConversationMemory:
    """Thread-safe per-session ring buffer of conversation turns.

    Applies a maximum turn count and a character budget, pruning the oldest
    turns first so prompts stay within the LLM context window.
    """

    def __init__(
        self,
        max_turns: int = 20,
        max_chars: int = 12000,
        max_sessions: int = 1000,
    ) -> None:
        self._max_turns = max(1, max_turns)
        self._max_chars = max(256, max_chars)
        self._max_sessions = max(1, max_sessions)
        self._sessions: dict[str, list[ConversationTurn]] = {}
        self._lock = threading.RLock()

    def add(self, session_id: str, role: str, content: str) -> ConversationTurn:
        if not content:
            raise ValueError("conversation turn content must not be empty")
        if role not in {"user", "assistant"}:
            raise ValueError(f"invalid conversation role: {role}")
        turn = ConversationTurn(role=role, content=content)
        with self._lock:
            self._prune_sessions()
            turns = self._sessions.setdefault(session_id, [])
            turns.append(turn)
            self._prune_turns(session_id, turns)
        return turn

    def get(self, session_id: str) -> list[ConversationTurn]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def messages(self, session_id: str) -> list[dict[str, str]]:
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.get(session_id)
        ]

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def _prune_turns(self, session_id: str, turns: list[ConversationTurn]) -> None:
        while len(turns) > self._max_turns:
            turns.pop(0)
        budget = self._max_chars
        if sum(len(turn.content) for turn in turns) <= budget:
            return
        pruned: list[ConversationTurn] = []
        used = 0
        for turn in reversed(turns):
            if used + len(turn.content) <= budget or not pruned:
                pruned.insert(0, turn)
                used += len(turn.content)
            else:
                break
        self._sessions[session_id] = pruned

    def _prune_sessions(self) -> None:
        if len(self._sessions) <= self._max_sessions:
            return
        for session_id in list(self._sessions)[: len(self._sessions) - self._max_sessions]:
            del self._sessions[session_id]
