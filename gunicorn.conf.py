"""Gunicorn production config for OMSP."""

import os

bind = f"0.0.0.0:{os.getenv('OMSP_PORT', '80')}"

# Each worker loads its own copy of the model (~1.7 GB for deberta-v3-large).
# 2 workers ≈ 5 GB RAM. Scale horizontally, not vertically.
workers = int(os.getenv("OMSP_WORKERS", "2"))
worker_class = "gthread"
threads = 2             # 2 threads per worker for I/O overlap
worker_tmp_dir = "/dev/shm"

timeout = 300           # cold-start model load can take 30-60s
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("OMSP_LOG_LEVEL", "info").lower()


def on_starting(server):
    server.log.info("OMSP starting")


def post_fork(server, worker):
    server.log.info(f"Worker {worker.pid} spawned")


def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited")