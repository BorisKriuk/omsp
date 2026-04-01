"""
OMSP v2 — Flask application
Run:  python app.py
"""

import logging

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from storage.memory_store import MemoryStore
from classifiers.registry import ClassifierRegistry
from classifiers.terrorist import TerroristClassifier
from classifiers.fraud import FraudClassifier
from classifiers.grooming import GroomingClassifier
from classifiers.self_harm import SelfHarmClassifier
from classifiers.radicalization import RadicalizationClassifier
from classifiers.spam import SpamClassifier
from pipeline.processor import MessageProcessor
from encoder.backend import EncoderBackend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── bootstrap ────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── encoder (shared by all classifiers) ─────────────────────
encoder_backend = None
if Config.ENCODER_ENABLED:
    encoder_backend = EncoderBackend()
    ok = encoder_backend.initialize(
        model_name=Config.ENCODER_MODEL,
        device=Config.ENCODER_DEVICE,
    )
    if ok:
        logger.info("Encoder ready — classifiers use Tier-2 NLI")
    else:
        logger.warning("Encoder failed to load — falling back to keyword-only mode")
        encoder_backend = None
else:
    logger.info("Encoder disabled (OMSP_ENCODER_ENABLED=false) — keyword-only mode")

# ── store + classifiers ─────────────────────────────────────
store = MemoryStore(max_alerts=Config.MAX_ALERTS)
registry = ClassifierRegistry()

for clf_class in [
    TerroristClassifier,
    FraudClassifier,
    GroomingClassifier,
    SelfHarmClassifier,
    RadicalizationClassifier,
    SpamClassifier,
]:
    registry.register(clf_class())

processor = MessageProcessor(store=store, registry=registry)


# ── helpers ──────────────────────────────────────────────────

def _validate_message_fields(data: dict) -> str | None:
    """Return an error string, or None if valid."""
    for field in ("chat_id", "user_id", "user_status", "message"):
        if field not in data:
            return f"missing field: {field}"
    try:
        int(data["user_status"])
    except (ValueError, TypeError):
        return "user_status must be an integer"
    if len(str(data["message"])) > Config.MAX_MESSAGE_LENGTH:
        return (
            f"message exceeds maximum length of "
            f"{Config.MAX_MESSAGE_LENGTH} characters"
        )
    return None


# ── routes ───────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "version": "2.1.0",
        "encoder_ready": encoder_backend.is_ready if encoder_backend else False,
        "encoder_model": encoder_backend.model_name if encoder_backend else None,
        **store.stats(),
    })


@app.route("/api/v1/message", methods=["POST"])
def process_message():
    """Process a single message through the full pipeline."""
    data = request.get_json(force=True)
    err = _validate_message_fields(data)
    if err:
        return jsonify({"error": err}), 400

    result = processor.process(
        chat_id=str(data["chat_id"]),
        user_id=str(data["user_id"]),
        user_status=int(data["user_status"]),
        message=str(data["message"]),
    )
    return jsonify(result)


@app.route("/api/v1/batch", methods=["POST"])
def process_batch():
    """Process a list of messages."""
    data = request.get_json(force=True)
    messages = data.get("messages")
    if not messages or not isinstance(messages, list):
        return jsonify({"error": "provide a 'messages' list"}), 400

    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            return jsonify({"error": f"message {i}: must be an object"}), 400
        err = _validate_message_fields(m)
        if err:
            return jsonify({"error": f"message {i}: {err}"}), 400

    results = processor.process_batch(messages)
    return jsonify({"count": len(results), "results": results})


@app.route("/api/v1/profile/<anon_user_id>", methods=["GET"])
def get_profile(anon_user_id):
    profile = store.get_profile(anon_user_id)
    if not profile:
        return jsonify({"error": "not found"}), 404
    return jsonify(profile.to_dict())


@app.route("/api/v1/profiles", methods=["GET"])
def list_profiles():
    limit = request.args.get("limit", 50, type=int)
    return jsonify({"profiles": store.list_profiles(limit)})


@app.route("/api/v1/alerts", methods=["GET"])
def get_alerts():
    chat_id = request.args.get("chat_id")
    user_id = request.args.get("user_id")
    limit = request.args.get("limit", 200, type=int)
    alerts = store.get_alerts(chat_id=chat_id, user_id=user_id, limit=limit)
    return jsonify({"count": len(alerts), "alerts": alerts})


@app.route("/api/v1/classifiers", methods=["GET"])
def list_classifiers():
    return jsonify({"classifiers": registry.list_classifiers()})


# ── run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.warning(
        "Starting Flask development server. For production use: "
        "gunicorn -w 4 -b %s:%s app:app", Config.HOST, Config.PORT,
    )
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)