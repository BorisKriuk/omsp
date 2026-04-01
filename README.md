# 🛡️ OMSP — Open Messenger Safety Protocol

<p align="center">
  <em>🔒 Safety without surveillance. Classification without compromise.</em>
</p>

---

OMSP is an open, auditable protocol for detecting harmful content in messaging
platforms **without breaking end-to-end encryption**. The safety classifier
runs directly on the user's device or the platform's local node — messages are
analyzed locally, and content never leaves the endpoint. Encryption stays
completely intact. The safety layer sits *inside* the endpoint, not between
endpoints.

This repository contains the reference implementation: a self-hosted,
CPU-friendly safety API using a hybrid pipeline.
It requires no external API keys and returns structured risk assessments
in a single JSON response.

---

## 🧭 Design Philosophy - Now Proof Of Concept

Previous attempts at client-side safety (such as Apple's CSAM scanning) failed
because they were proprietary, centralized hash reporting, and lacked public
accountability. OMSP addresses all three failures:

1. **🔐 The data never moves.** Classification happens entirely on-device or on the
   platform's local node. Message content is never transmitted to any external
   server, government, or third party.

2. **📖 Detection rules are open source and human-readable.** Anyone can verify
   that no one has inserted "flag political dissent" into the keyword lists.
   Threat definitions are transparent, auditable, and versioned.

3. **🔔 Alerts, not wiretaps.** What leaves the device — periodically, not in
   real-time — is an anonymized statistical signal: a user hash triggered a
   specific classifier at a given confidence level, with an escalation pattern
   detected. No message content. No identifying information. Just a lead.
   Governments can investigate through legal channels, warrants, and courts.

> 💡 The periodic reporting delay is deliberate and philosophically significant:
> real-time reporting is surveillance; periodic aggregated alerts are safety
> reporting, closer to how a human moderator would flag concerns.


## Threat Categories

| Category           | Description                                                        |
|--------------------|--------------------------------------------------------------------|
| **Terrorist**      | Violent attacks, weapons, covert operational planning               |
| **Radicalization** | Extremist rhetoric, supremacist content, dehumanization             |
| **Fraud**          | Scams, phishing, financial manipulation                             |
| **Grooming**       | Adult manipulation of minors, inappropriate trust-building          |
| **Self-Harm**      | Suicidal ideation, self-injury, expressions of hopelessness         |
| **Spam**           | Unsolicited commercial content, link farming                        |

## How It Works

Every message passes through a three-tier pipeline locally:

1. **Tier 1 — Keyword & pattern matching** with obfuscation-aware normalization
   (leet-speak, Unicode substitution, whitespace insertion).
2. **Tier 2 — Zero-shot NLI** using
   [DeBERTa-v3-large](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
   for semantic understanding. A lightweight screening pass skips the encoder
   for clearly benign messages.
3. **Tier 3 — Behavioural profiling** that tracks per-user risk dimensions
   over time with exponential decay, catching patterns that no single message
   reveals. The profile itself never leaves the device — it is not a
   government dossier, but a local behavioural fingerprint.

Context is what separates the protocol from naive keyword scanning. A phrase
like "the brothers have trained well" is meaningless in isolation. But when
preceded by weeks of escalating rhetoric, obfuscation patterns, and
weapons-related discussion, the local profile captures that trajectory.
Classification operates per-pattern, not per-message.

Responses include per-category confidence scores, matched keywords, encoder
hypothesis scores, and a snapshot of the user's behavioural profile — giving
integrators full transparency into every decision.

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/BorisKriuk/omsp.git
cd omsp
docker compose up -d
```

The first launch downloads the model (~870 MB) and caches it inside the image.
Subsequent starts are fast. The API is available at `http://localhost:80`.

Verify it's running:

```bash
curl http://localhost/health
```

### Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python scripts/download_model.py \
    --model-name MoritzLaurer/deberta-v3-large-zeroshot-v2.0 \
    --model-dir models
python app.py
```

## API Reference

### `POST /api/v1/message`

Process a single message locally.

**Request:**

```json
{
  "chat_id": "chat_001",
  "user_id": "user_42",
  "user_status": 1,
  "message": "Hello, is anyone there?"
}
```

| Field         | Type   | Required | Description                                     |
|---------------|--------|----------|-------------------------------------------------|
| `chat_id`     | string | yes      | Conversation identifier                          |
| `user_id`     | string | yes      | User identifier (hashed internally, never stored raw) |
| `user_status` | int    | yes      | Application-defined user status code             |
| `message`     | string | yes      | Message text (max 10,000 chars by default)       |

**Response:**

```json
{
  "anon_chat_id": "2290581e9abb8e30",
  "anon_user_id": "a19dd12e4de15ffe",
  "any_alert": false,
  "classifications": {
    "fraud":          { "flag": 0, "confidence": 0.00, "matched": [], "encoder_scores": {}, "details": "..." },
    "grooming":       { "flag": 0, "confidence": 0.02, "matched": [], "encoder_scores": {}, "details": "..." },
    "radicalization": { "flag": 0, "confidence": 0.00, "matched": [], "encoder_scores": {}, "details": "..." },
    "self_harm":      { "flag": 0, "confidence": 0.00, "matched": [], "encoder_scores": {}, "details": "..." },
    "spam":           { "flag": 0, "confidence": 0.00, "matched": [], "encoder_scores": {}, "details": "..." },
    "terrorist":      { "flag": 0, "confidence": 0.01, "matched": [], "encoder_scores": {}, "details": "..." }
  },
  "pii_stripped": false,
  "profile_snapshot": {
    "anon_user_id": "a19dd12e4de15ffe",
    "message_count": 1,
    "dimensions": { "aggression": 0.0, "criminal": 0.0, "...": 0.0 },
    "interaction_diversity": 0.05,
    "vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  },
  "timestamp": 1775047065.38
}
```

Each classifier returns `"flag": 1` when confidence exceeds its threshold.
`"any_alert": true` means at least one category flagged.

### `POST /api/v1/batch`

Process multiple messages in one request.

```json
{
  "messages": [
    { "chat_id": "c1", "user_id": "u1", "user_status": 1, "message": "..." },
    { "chat_id": "c1", "user_id": "u2", "user_status": 1, "message": "..." }
  ]
}
```

Returns `{ "count": N, "results": [...] }`.

### `GET /api/v1/profile/<anon_user_id>`

Retrieve the behavioural profile for a given anonymized user ID.

### `GET /api/v1/alerts`

Query stored alerts. Supports optional query parameters: `chat_id`, `user_id`, `limit`.

### `GET /api/v1/classifiers`

List all registered classifiers and their metadata.

### `GET /health`

Returns service status, encoder readiness, and store statistics.

## Configuration

All configuration is via environment variables. Defaults are production-ready.

| Variable                  | Default                                             | Description                              |
|---------------------------|-----------------------------------------------------|------------------------------------------|
| `OMSP_PORT`               | `80`                                                | HTTP listen port                         |
| `OMSP_WORKERS`            | `2`                                                 | Gunicorn worker count                    |
| `OMSP_LOG_LEVEL`          | `INFO`                                              | Log verbosity                            |
| `OMSP_SALT`               | *(random per boot)*                                 | HMAC salt for user/chat ID anonymization. Set for persistence across restarts. |
| `OMSP_ENCODER_MODEL`      | `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`       | Hugging Face model name                  |
| `OMSP_ENCODER_DEVICE`     | `cpu`                                               | Inference device (`cpu` or `cuda`)       |
| `OMSP_ENCODER_ENABLED`    | `true`                                              | Set `false` for keyword-only mode        |
| `OMSP_MAX_MESSAGE_LENGTH` | `10000`                                             | Maximum input message length (chars)     |
| `OMSP_MAX_ALERTS`         | `10000`                                             | Maximum alerts held in memory            |
| `OMSP_PROFILE_DECAY`      | `0.15`                                              | Exponential decay factor for profile dimensions |
| `OMSP_ALERT_THRESHOLD`    | `0.5`                                               | Global alert threshold                   |
| `OMSP_REPORT_INTERVAL`    | `43200`                                             | Alert reporting interval in seconds (default: 12 hours) |
| `OMSP_DEBUG`              | `false`                                             | Enable Flask debug mode                  |

## Memory & Scaling

Each worker loads its own copy of the DeBERTa-v3-large model in float32
(~1.7 GB per worker). Plan accordingly:

| Workers | Approximate RAM |
|---------|-----------------|
| 1       | ~3 GB           |
| 2       | ~5 GB           |
| 4       | ~9 GB           |

For on-device deployments, a single worker with keyword-only mode
(`OMSP_ENCODER_ENABLED=false`) uses under 100 MB.

Scale horizontally (more containers) rather than vertically (more workers per
container) for better isolation and fault tolerance. Set `OMSP_WORKERS=1` on
machines with limited RAM.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Local Device / Platform Node                   │
│                                                                  │
│  Encrypted Message ──▶ Decrypt ──▶ Display to User               │
│                                      │                           │
│                                      ▼                           │
│                              MessageProcessor                    │
│                                      │                           │
│       ┌──────────────────────────────┼──────────────────┐        │
│       │                              │                  │        │
│       ▼                              ▼                  ▼        │
│  Anonymizer               ClassifierRegistry        Profiler     │
│  (HMAC-SHA256)            │                    (behavioural dims  │
│                           ├─ TerroristClassifier  + exp. decay)  │
│                           ├─ RadicalizationClassifier            │
│                           ├─ FraudClassifier                     │
│                           ├─ GroomingClassifier                  │
│                           ├─ SelfHarmClassifier                  │
│                           └─ SpamClassifier                      │
│                                │                                 │
│                      ┌─────────┴─────────┐                       │
│                      │                   │                       │
│                Tier 1: Keywords    Tier 2: NLI Encoder            │
│                + obfuscation       (DeBERTa, local)              │
│                      │                   │                       │
│                      └─────────┬─────────┘                       │
│                                │                                 │
│                                ▼                                 │
│                     Local MemoryStore                             │
│                    (alerts + profiles)                            │
│                         │                                        │
│                         ▼ (periodic, anonymized)                  │
│              ┌─────────────────────┐                              │
│              │  Anonymized Alert   │                              │
│              │  { user_hash,       │                              │
│              │    classifier,      │                              │
│              │    confidence,      │                              │
│              │    escalation }     │                              │
│              │  NO message content │                              │
│              └────────┬────────────┘                              │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │ every 12 hours
                        ▼
              Platform / Authority
              (lead, not wiretap)
```

## Project Structure

```
omsp/
├── app.py                  # Flask application & routes
├── config.py               # Environment-driven configuration
├── gunicorn.conf.py        # Production server settings
├── Dockerfile              # Multi-stage production build
├── docker-compose.yml      # One-command deployment
├── requirements.txt
├── classifiers/
│   ├── registry.py         # Classifier registration & dispatch
│   ├── base.py             # Base classifier interface
│   ├── terrorist.py
│   ├── radicalization.py
│   ├── fraud.py
│   ├── grooming.py
│   ├── self_harm.py
│   └── spam.py
├── encoder/
│   └── backend.py          # Singleton NLI encoder (DeBERTa)
├── pipeline/
│   └── processor.py        # Orchestrates classify → profile → store
├── storage/
│   └── memory_store.py     # In-memory alert & profile storage
├── anonymizer/             # HMAC-based ID anonymization
├── profiler/               # Behavioural dimension tracking
├── utils/                  # Shared helpers
└── scripts/
    └── download_model.py   # Pre-download model for Docker build
```

## Platform Notes

**Apple Silicon (ARM64):** The DeBERTa model's config specifies `torch_dtype: float16`,
but PyTorch's CPU backend does not fully support half-precision compute on ARM64.
OMSP forces float32 inference automatically. This is handled transparently —
no user action required.

**GPU acceleration:** Set `OMSP_ENCODER_DEVICE=cuda` and use a CUDA-capable
base image. Latency drops from ~5s to ~50ms per message.

**Keyword-only mode:** Set `OMSP_ENCODER_ENABLED=false` to skip model loading
entirely. Useful for on-device deployments, testing, development, or
resource-constrained environments. Detection quality will be lower
(no semantic understanding), but the behavioural profiler still operates.

## Legal Cover for Platforms

OMSP provides platforms with a verifiable safety posture that has never existed
before. Under this protocol, a platform can demonstrate — mathematically and
verifiably — exactly what safety measures are in place, their detection rates,
and their false positive rates. When a government asks how terrorist content
is handled, the answer is a repository link, a detection benchmark, and a
proof that message content was never accessed. Demanding more than that
requires a government to publicly argue for surveillance, which carries a
political cost most democracies are unwilling to pay.

## Security & Privacy Considerations

OMSP is designed so that the safety layer and the encryption layer never
conflict. All classification happens locally. No message content is ever
transmitted. The periodic alert reporting contains only anonymized statistical
signals.

User and chat IDs are anonymized with HMAC-SHA256 before any storage or
reporting. Set `OMSP_SALT` to a stable secret so anonymized IDs remain
consistent across restarts.

The encoder uses a smart-truncation strategy that preserves both the head
and tail of long messages, preventing adversarial padding attacks where
harmful content is hidden at the end of an otherwise benign message.

## License

MIT
