# ============================================================
#  OMSP — Open Message Safety Protocol
#  Production Dockerfile (CPU inference)
# ============================================================

# --------------- stage 1: build & download models -----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch FIRST, then everything else
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

COPY scripts/download_model.py .
RUN python download_model.py \
        --model-name "MoritzLaurer/deberta-v3-large-zeroshot-v2.0" \
        --model-dir /models


# --------------- stage 2: runtime --------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=4 \
    TOKENIZERS_PARALLELISM=false \
    OMSP_ENV=production \
    OMSP_LOG_LEVEL=INFO \
    OMSP_ENCODER_MODEL=MoritzLaurer/deberta-v3-large-zeroshot-v2.0 \
    TRANSFORMERS_CACHE=/app/models \
    HF_HOME=/app/models \
    OMSP_PORT=80

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r omsp && useradd -r -g omsp -d /app -s /sbin/nologin omsp

# Python packages from builder (includes bin/gunicorn)
COPY --from=builder /usr/local /usr/local

# Cached model from builder
COPY --from=builder /models /app/models

# ── Application source (matches actual project layout) ──
COPY app.py            .
COPY config.py         .
COPY gunicorn.conf.py  .
COPY classifiers/      classifiers/
COPY encoder/          encoder/
COPY pipeline/         pipeline/
COPY storage/          storage/
COPY anonymizer/       anonymizer/
COPY profiler/         profiler/
COPY utils/            utils/

RUN chown -R omsp:omsp /app

USER omsp

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

ENTRYPOINT ["gunicorn", "app:app", "--config", "gunicorn.conf.py"]