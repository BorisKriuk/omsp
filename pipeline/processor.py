from __future__ import annotations
import time
import logging
from anonymizer.engine import Anonymizer
from classifiers.registry import ClassifierRegistry
from storage.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Single entry-point for the full pipeline:
        raw message → anonymise → classify → profile update → alerts
    """

    def __init__(
        self,
        store: MemoryStore,
        registry: ClassifierRegistry,
    ) -> None:
        self.anonymizer = Anonymizer()
        self.store = store
        self.registry = registry

    # ── single message ───────────────────────────────────────
    def process(
        self,
        chat_id: str,
        user_id: str,
        user_status: int,
        message: str,
    ) -> dict:
        ts = time.time()

        # 1 — anonymise
        anon = self.anonymizer.anonymize(chat_id, user_id, user_status, message)

        # 2 — classify (on cleaned text only)
        t0 = time.time()
        classifications = self.registry.classify_all(
            anon["clean_message"],
            context={
                "user_status": user_status,
                "anon_chat_id": anon["anon_chat_id"],
            },
        )
        t_classify = time.time() - t0
        logger.info("classify_all took %.3fs for %d chars", t_classify, len(message))

        # 3 — update user profile
        profile = self.store.get_or_create_profile(anon["anon_user_id"])
        profile.update(anon["clean_message"], anon["anon_chat_id"])

        # 4 — persist any alerts that fired
        any_alert = False
        for clf_name, result in classifications.items():
            if result["flag"] == 1:
                any_alert = True
                self.store.store_alert(
                    {
                        "timestamp": ts,
                        "anon_chat_id": anon["anon_chat_id"],
                        "anon_user_id": anon["anon_user_id"],
                        "classifier": clf_name,
                        "confidence": result["confidence"],
                        "details": result["details"],
                    }
                )

        return {
            "timestamp": ts,
            "anon_chat_id": anon["anon_chat_id"],
            "anon_user_id": anon["anon_user_id"],
            "user_status": user_status,
            "pii_stripped": anon["pii_stripped"],
            "classifications": classifications,
            "any_alert": any_alert,
            "profile_snapshot": profile.to_dict(),
        }

    # ── batch ────────────────────────────────────────────────
    def process_batch(self, messages: list[dict]) -> list[dict]:
        return [
            self.process(
                chat_id=m["chat_id"],
                user_id=m["user_id"],
                user_status=int(m["user_status"]),
                message=m["message"],
            )
            for m in messages
        ]