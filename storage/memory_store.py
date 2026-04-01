from __future__ import annotations
import threading
from collections import deque
from profiler.engine import UserProfile


class MemoryStore:
    """
    In-memory store for v1.  Swap for Redis / Postgres later —
    the interface stays the same.
    """

    def __init__(self, max_alerts: int = 10_000) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._alerts: deque[dict] = deque(maxlen=max_alerts)
        self._lock = threading.Lock()

    # ── profiles ─────────────────────────────────────────────
    def get_or_create_profile(self, anon_user_id: str) -> UserProfile:
        with self._lock:
            if anon_user_id not in self._profiles:
                self._profiles[anon_user_id] = UserProfile(anon_user_id)
            return self._profiles[anon_user_id]

    def get_profile(self, anon_user_id: str) -> UserProfile | None:
        with self._lock:
            return self._profiles.get(anon_user_id)

    def list_profiles(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return [
                p.to_dict()
                for p in list(self._profiles.values())[:limit]
            ]

    # ── alerts ───────────────────────────────────────────────
    def store_alert(self, alert: dict) -> None:
        with self._lock:
            self._alerts.append(alert)

    def get_alerts(
        self,
        chat_id: str | None = None,
        user_id: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        with self._lock:
            out = list(self._alerts)
            if chat_id:
                out = [a for a in out if a.get("anon_chat_id") == chat_id]
            if user_id:
                out = [a for a in out if a.get("anon_user_id") == user_id]
            return out[-limit:]

    # ── stats ────────────────────────────────────────────────
    def stats(self) -> dict:
        with self._lock:
            return {
                "total_profiles": len(self._profiles),
                "total_alerts": len(self._alerts),
            }