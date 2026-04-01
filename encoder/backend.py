"""
Singleton zero-shot NLI encoder backend.
Loads once, shared across all encoder-aware classifiers.
Falls back gracefully when transformers / torch are not installed.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_TRANSFORMERS_AVAILABLE = False
_torch = None
try:
    import torch as _torch
    from transformers import pipeline as _hf_pipeline  # noqa: F401

    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning(
        "transformers not installed — encoder classifiers will use keyword-only fallback"
    )


class EncoderBackend:
    """Thread-safe, lazy-loaded, singleton NLI encoder."""

    _instance = None
    _lock = threading.Lock()

    # ── singleton ────────────────────────────────────────────
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._pipe = None
                    inst._model_name = None
                    inst._device = None
                    inst._ready = False
                    inst._failed = False
                    cls._instance = inst
        return cls._instance

    # ── initialisation (call once at startup) ────────────────
    def initialize(self, model_name: str, device: str = "cpu") -> bool:
        """Load the model.  Returns True on success."""
        if self._ready and self._model_name == model_name:
            return True
        if not _TRANSFORMERS_AVAILABLE:
            logger.error("Cannot initialise encoder: transformers library missing")
            self._failed = True
            return False
        with self._lock:
            if self._ready and self._model_name == model_name:
                return True
            try:
                logger.info("Loading encoder  %s → %s …", model_name, device)
                self._pipe = _hf_pipeline(
                    "zero-shot-classification",
                    model=model_name,
                    device=device,
                    model_kwargs={"torch_dtype": _torch.float32},
                )
                self._model_name = model_name
                self._device = device
                self._ready = True
                logger.info("Encoder loaded ✓  (%s)", model_name)
                return True
            except Exception as exc:
                logger.error("Encoder load failed: %s", exc)
                self._failed = True
                return False

    # ── public API ───────────────────────────────────────────
    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def model_name(self) -> str | None:
        return self._model_name

    @staticmethod
    def _smart_truncate(text: str, max_len: int = 512) -> str:
        """Truncate keeping both head and tail of the text.

        A naive ``text[:512]`` allows an attacker to pad the beginning
        with innocuous content so the encoder never sees the harmful
        tail.  This method takes ~75 % from the head and ~25 % from
        the tail, joined by an ellipsis, ensuring both ends are
        represented in the encoder's context window.
        """
        if len(text) <= max_len:
            return text
        separator = " ... "
        head_len = (max_len * 3) // 4
        tail_len = max_len - head_len - len(separator)
        if tail_len < 1:
            return text[:max_len]
        return text[:head_len] + separator + text[-tail_len:]

    def classify_zero_shot(
        self,
        text: str,
        candidate_labels: list[str],
        multi_label: bool = True,
    ) -> dict[str, float]:
        """
        Run zero-shot NLI classification.
        Returns {label: score} dict, or empty dict on failure.
        """
        if not self._ready:
            return {}
        try:
            truncated = self._smart_truncate(text, max_len=512)
            result = self._pipe(
                truncated, candidate_labels, multi_label=multi_label
            )
            return dict(zip(result["labels"], result["scores"]))
        except Exception as exc:
            logger.warning("Encoder inference failed: %s", exc)
            return {}