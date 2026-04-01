from __future__ import annotations
import threading
import numpy as np
from config import Config
from profiler.dimensions import PROFILE_DIMENSIONS


class UserProfile:
    """Multi-dimensional user vector, updated with every message via EMA."""

    __slots__ = (
        "anon_user_id",
        "dimensions",
        "message_count",
        "chat_ids",
        "interaction_diversity",
        "_lock",
    )

    def __init__(self, anon_user_id: str) -> None:
        self._lock = threading.Lock()
        self.anon_user_id = anon_user_id
        self.dimensions: dict[str, float] = {
            dim: 0.0 for dim in PROFILE_DIMENSIONS
        }
        self.message_count: int = 0
        self.chat_ids: set[str] = set()
        self.interaction_diversity: float = 0.0

    def update(self, clean_message: str, anon_chat_id: str) -> None:
        with self._lock:
            self.message_count += 1
            self.chat_ids.add(anon_chat_id)
            # diversity = how many distinct chats (capped at 1.0)
            self.interaction_diversity = min(len(self.chat_ids) / 20.0, 1.0)

            decay = Config.PROFILE_DECAY
            text_lower = clean_message.lower()

            for dim_name, dim_cfg in PROFILE_DIMENSIONS.items():
                keywords = dim_cfg["keywords"]
                hits = sum(1 for kw in keywords if kw in text_lower)
                # normalise: if you hit ≥15 % of keywords → full signal
                signal = min(hits / max(len(keywords) * 0.15, 1.0), 1.0)
                # exponential moving average
                self.dimensions[dim_name] = (
                    (1 - decay) * self.dimensions[dim_name] + decay * signal
                )

    def get_vector(self) -> np.ndarray:
        with self._lock:
            return np.array(list(self.dimensions.values()), dtype=np.float32)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "anon_user_id": self.anon_user_id,
                "message_count": self.message_count,
                "interaction_diversity": round(self.interaction_diversity, 4),
                "dimensions": {k: round(v, 4) for k, v in self.dimensions.items()},
                "vector": [round(v, 4) for v in self.dimensions.values()],
            }


class ProfileEngine:
    """Thin convenience wrapper (room for future batch ops)."""

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)