import hashlib
import re
import time
from config import Config


class Anonymizer:
    """
    Strips PII from messages and hashes all identifiers
    before anything touches the classification pipeline.
    """

    def __init__(self, salt: str | None = None):
        self.salt = salt or Config.SECRET_SALT

        # order matters — longer / more specific patterns first
        self._pii_patterns: list[tuple[str, str]] = [
            # credit / debit cards
            (r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b", "[CARD]"),
            # SSN (US)
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
            # email
            (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
            # international phone (broad)
            (r"\b\+?\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{1,4}[\s\-.]?\d{1,9}\b", "[PHONE]"),
            # IPv4
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]"),
            # URLs
            (r"https?://\S+", "[URL]"),
        ]

    # ── hashing ──────────────────────────────────────────────
    def hash_id(self, raw_id: str) -> str:
        return hashlib.sha256(
            f"{self.salt}:{raw_id}".encode("utf-8")
        ).hexdigest()[:16]

    # ── PII stripping ────────────────────────────────────────
    def strip_pii(self, text: str) -> str:
        cleaned = text
        for pattern, placeholder in self._pii_patterns:
            cleaned = re.sub(pattern, placeholder, cleaned)
        return cleaned

    # ── public entry point ───────────────────────────────────
    def anonymize(
        self,
        chat_id: str,
        user_id: str,
        user_status: int,
        message: str,
    ) -> dict:
        clean_message = self.strip_pii(message)
        return {
            "anon_chat_id": self.hash_id(chat_id),
            "anon_user_id": self.hash_id(user_id),
            "user_status": user_status,
            "clean_message": clean_message,
            "pii_stripped": clean_message != message,
            "original_length": len(message),
            "ts": time.time(),
        }