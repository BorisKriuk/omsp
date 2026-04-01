import re
from abc import ABC, abstractmethod

from utils.text_normalizer import normalize as _normalize
from utils.text_normalizer import obfuscation_score as _obfuscation_score

# ── keyword pattern cache (module-level, populated lazily) ───
_KW_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _kw_pattern(keyword: str) -> re.Pattern:
    pat = _KW_PATTERN_CACHE.get(keyword)
    if pat is None:
        pat = re.compile(r"\b" + re.escape(keyword))
        _KW_PATTERN_CACHE[keyword] = pat
    return pat


class BaseClassifier(ABC):
    """
    Every safety classifier inherits from this.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def classify(self, text: str, context: dict | None = None) -> dict:
        ...

    # ── keyword lists (override in subclass) ─────────────────
    HIGH: list[str] = []
    MED: list[str] = []
    LOW: list[str] = []

    # ── NLI hypotheses (override in subclass) ────────────────
    HYPOTHESES: list[str] = []

    # ── two-phase encoder screening ──────────────────────────
    SCREEN_HYPOTHESIS: str = ""
    SCREEN_THRESHOLD: float = 0.20

    # Per-classifier bypass: if kw_score >= this, skip screen
    # and go straight to detail.  Safety-critical classifiers
    # lower this so even a single LOW keyword triggers full eval.
    DETAIL_KW_BYPASS: float = 0.10

    # ── tunable per-classifier ───────────────────────────────
    THRESHOLD = 0.50
    KW_WEIGHT = 0.30
    ENC_WEIGHT = 0.70
    OBFUSCATION_BOOST = 0.10

    KW_FLOOR_MULT = 0.60
    ENC_FLOOR_MULT = 0.80

    AGREEMENT_BOOST = 0.06
    AGREEMENT_KW_MIN = 0.10
    AGREEMENT_ENC_MIN = 0.15

    # ── early-exit control ───────────────────────────────────
    SKIP_ENCODER_ON_CLEAN = True
    OBF_ENCODER_THRESHOLD = 0.15
    MIN_KW_FOR_ENCODER = 0.05

    # ── shared helpers ───────────────────────────────────────

    def _should_run_encoder(self, kw_score: float, obf: float) -> bool:
        if not self.SKIP_ENCODER_ON_CLEAN:
            return True
        if kw_score >= self.MIN_KW_FOR_ENCODER:
            return True
        if obf > self.OBF_ENCODER_THRESHOLD:
            return True
        return False

    # ═════════════════════════════════════════════════════════
    #  Phase methods — used by ClassifierRegistry for batching
    # ═════════════════════════════════════════════════════════

    def keyword_phase(
        self, original: str, normalized: str,
    ) -> tuple[float, list[str]]:
        return self.keyword_score_dual(
            original, normalized, self.HIGH, self.MED, self.LOW,
        )

    def finalize(
        self,
        kw_score: float,
        matched: list[str],
        enc_scores: dict[str, float],
        obf: float,
        enc_skipped: bool = False,
    ) -> dict:
        enc_score = max(enc_scores.values()) if enc_scores else 0.0
        final = self._combine(kw_score, enc_score, obf)

        details = (
            f"kw={kw_score:.2f} enc={enc_score:.2f} "
            f"obf={obf:.2f} final={final:.2f}"
        )
        if enc_skipped:
            details += " [enc-skip]"

        return {
            "label": self.name,
            "flag": 1 if final >= self.THRESHOLD else 0,
            "confidence": round(final, 4),
            "matched": matched[:5],
            "details": details,
            "encoder_scores": {k: round(v, 4) for k, v in enc_scores.items()},
        }

    # ── static helpers ───────────────────────────────────────

    @staticmethod
    def normalize(text: str) -> str:
        return _normalize(text)

    @staticmethod
    def get_obfuscation_score(original: str, normalized: str) -> float:
        return _obfuscation_score(original, normalized)

    @staticmethod
    def keyword_score(
        text: str,
        high: list[str],
        medium: list[str],
        low: list[str],
        high_w: float = 0.40,
        med_w: float = 0.15,
        low_w: float = 0.04,
    ) -> tuple[float, list[str]]:
        t = text.lower()
        score = 0.0
        matched: list[str] = []
        for kw in high:
            if _kw_pattern(kw).search(t):
                score += high_w
                matched.append(kw)
        for kw in medium:
            if _kw_pattern(kw).search(t):
                score += med_w
                matched.append(kw)
        for kw in low:
            if _kw_pattern(kw).search(t):
                score += low_w
                matched.append(kw)
        return min(score, 1.0), matched

    @staticmethod
    def keyword_score_dual(
        original: str,
        normalized: str,
        high: list[str],
        medium: list[str],
        low: list[str],
        **kw_args,
    ) -> tuple[float, list[str]]:
        score_n, matched_n = BaseClassifier.keyword_score(
            normalized, high, medium, low, **kw_args
        )
        score_o, matched_o = BaseClassifier.keyword_score(
            original, high, medium, low, **kw_args
        )
        if score_n >= score_o:
            return score_n, matched_n
        return score_o, matched_o

    def _combine(
        self,
        kw_score: float,
        enc_score: float,
        obf: float = 0.0,
    ) -> float:
        if enc_score > 0:
            combined = (self.KW_WEIGHT * kw_score) + (self.ENC_WEIGHT * enc_score)
        else:
            combined = kw_score

        kw_floor = kw_score * self.KW_FLOOR_MULT
        enc_floor = enc_score * self.ENC_FLOOR_MULT
        combined = max(combined, kw_floor, enc_floor)

        if (kw_score >= self.AGREEMENT_KW_MIN
                and enc_score >= self.AGREEMENT_ENC_MIN):
            combined += self.AGREEMENT_BOOST

        if obf > 0.15 and (kw_score > 0 or enc_score > 0.3):
            combined += self.OBFUSCATION_BOOST * obf

        return min(combined, 1.0)