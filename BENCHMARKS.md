# OMSP Benchmarks

Benchmark results from the OMSP load test suite against a 1,000-message
evaluation dataset containing 600 threat messages (100 per category across
obvious, subtle, and edge-case sub-types) and 400 clean messages.

## Environment

| Parameter       | Value                                            |
|-----------------|--------------------------------------------------|
| Platform        | Apple Silicon (aarch64), Docker, CPU-only         |
| Model           | MoritzLaurer/deberta-v3-large-zeroshot-v2.0       |
| Precision       | float32                                           |
| Workers         | 2 (gthread, 2 threads each)                       |
| Dataset         | 1,000 messages (600 threat + 400 clean)           |

## Overall Performance

| Metric           | Value  |
|------------------|--------|
| Accuracy         | 0.788  |
| Macro Precision  | 0.907  |
| Macro Recall     | 0.647  |
| Macro F1         | 0.755  |
| Clean Accuracy   | 1.000  |
| False Positives  | 40     |

## Per-Category Results

| Category       | Precision | Recall | F1     |
|----------------|-----------|--------|--------|
| Fraud          | 1.000     | 0.680  | 0.810  |
| Self-Harm      | 0.920     | 0.690  | 0.789  |
| Spam           | 0.919     | 0.680  | 0.782  |
| Radicalization | 0.833     | 0.650  | 0.730  |
| Grooming       | 1.000     | 0.550  | 0.710  |
| Terrorist      | 0.808     | 0.630  | 0.708  |

## Detection by Difficulty

| Difficulty | Avg Detection Rate | Notes                              |
|------------|--------------------|------------------------------------|
| Obvious    | 0.963              | Direct, explicit threat language    |
| Subtle     | 0.575              | Indirect phrasing, coded language   |
| Edge       | 0.175              | Benign-looking with ambiguous terms |

The low edge-case detection rate is by design — these are intentionally
ambiguous messages (e.g., "The football team really bombed last night")
where false positives would be worse than missed detections. OMSP
prioritizes precision over recall at the boundary.

This is where Tier 3 (behavioural profiling) compensates over time: a user
who consistently sends subtle threat messages will accumulate risk in their
local profile dimensions, eventually triggering alerts even when individual
messages fall below the per-message threshold. The benchmarks above measure
single-message detection only and do not reflect the longitudinal
improvement from profiling.

## Latency (CPU, ARM64)

| Percentile | Latency     |
|------------|-------------|
| Min        | 2,440 ms    |
| p50        | 5,409 ms    |
| Mean       | 5,985 ms    |
| p90        | 10,342 ms   |
| p95        | 11,585 ms   |
| p99        | 13,407 ms   |
| Max        | 16,325 ms   |
| Throughput | 0.33 msg/s  |

These numbers reflect CPU-only inference on Apple Silicon. On a GPU-equipped
server, expect 10–100× improvement in both latency and throughput.

For on-device keyword-only mode (`OMSP_ENCODER_ENABLED=false`), classification
completes in under 5 ms per message.

## Interpreting These Numbers

OMSP's hybrid approach yields high precision (few false accusations) with
moderate recall. The system is tuned to err on the side of caution: it is
better to miss an ambiguous edge case than to incorrectly flag a legitimate
user. For applications requiring higher recall, confidence thresholds can be
lowered via classifier configuration at the cost of more false positives.

This trade-off is central to the protocol's political viability. High
precision means platforms can point to low false-positive rates and
demonstrate that innocent users are not being flagged. The behavioural
profiling layer mitigates the recall gap over time without sacrificing
the per-message precision guarantee.