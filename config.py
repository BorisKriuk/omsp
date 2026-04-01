import os
import secrets
import logging

logger = logging.getLogger(__name__)

_env_salt = os.environ.get("OMSP_SALT", "")
if not _env_salt:
    _env_salt = secrets.token_hex(32)
    logger.warning(
        "OMSP_SALT not set — generated ephemeral salt for this process. "
        "Hashes will not survive restarts. Set OMSP_SALT for persistence."
    )


class Config:
    DEBUG = os.environ.get("OMSP_DEBUG", "false").lower() == "true"
    SECRET_SALT = _env_salt
    PROFILE_DECAY = float(os.environ.get("OMSP_PROFILE_DECAY", "0.15"))
    ALERT_THRESHOLD = float(os.environ.get("OMSP_ALERT_THRESHOLD", "0.5"))
    HOST = os.environ.get("OMSP_HOST", "0.0.0.0")
    PORT = int(os.environ.get("OMSP_PORT", "80"))

    # ── limits ───────────────────────────────────────────────
    MAX_MESSAGE_LENGTH = int(os.environ.get("OMSP_MAX_MESSAGE_LENGTH", "10000"))
    MAX_ALERTS = int(os.environ.get("OMSP_MAX_ALERTS", "10000"))

    # ── encoder settings ─────────────────────────────────────
    ENCODER_MODEL = os.environ.get(
        "OMSP_ENCODER_MODEL",
        "MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
    )
    ENCODER_DEVICE = os.environ.get("OMSP_ENCODER_DEVICE", "cpu")
    ENCODER_ENABLED = os.environ.get("OMSP_ENCODER_ENABLED", "true").lower() == "true"