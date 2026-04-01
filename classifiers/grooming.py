from classifiers.base import BaseClassifier


class GroomingClassifier(BaseClassifier):
    name = "grooming"
    version = "2.4.0"

    # ── Tier 1 — keywords ────────────────────────────────────
    HIGH = [
        "send me a picture of yourself", "don't tell your parents",
        "our little secret", "you're mature for your age",
        "send nudes", "turn on your camera", "i won't show anyone",
        "meet me alone", "age is just a number",
        "won't tell your parents", "are your parents home",
        "don't tell your mom", "don't tell your dad",
        "don't tell your mother", "don't tell your father",
    ]
    MED = [
        "how old are you", "do you have a boyfriend",
        "you're so pretty", "special friend", "trust me",
        "delete our chat", "private conversation",
        "don't tell anyone", "just between us",
        "just us", "away from everyone", "come alone",
        "no one has to know", "won't tell anyone",
        "somewhere private", "keep this between",
        "our secret place", "place where we",
        "where we could meet", "where we can meet",
        "don't tell your", "only one who understands",
        "you can trust me", "nobody needs to know",
        "more mature than", "not like other kids",
        "our special", "you're different from",
        "i understand you", "no one gets you like",
        # v2.4.0 — subtle grooming patterns
        "just the two of us", "only one who gets me",
        "only one who gets", "you and me alone",
        "hang out alone", "meet up privately",
        "when are you alone", "when are you home alone",
        "are you by yourself", "is anyone else home",
        "you're not like the others", "old soul",
        "more grown up than", "wise beyond your",
        "won't judge you", "safe with me",
        "between you and me", "our little",
    ]
    LOW = [
        "where do you live", "what school", "are you alone",
        "your parents home", "secret", "meet up",
        "special to me", "mature", "grown up",
        "home alone", "you're different", "old are you",
        # v2.4.0
        "pictures of you", "photo of you", "video of you",
        "webcam", "camera on",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text shows patterns of an adult manipulating, "
        "isolating, or building inappropriate trust with a young person."
    )
    SCREEN_THRESHOLD = 0.03   # safety-critical
    DETAIL_KW_BYPASS = 0.02

    # ── Tier 2 — NLI hypotheses ──────────────────────────────
    HYPOTHESES = [
        "This text is an adult attempting to build inappropriate emotional trust with a minor.",
        "This text tries to isolate a child from their parents or guardians.",
        "This text attempts to arrange a secret or private meeting with a minor.",
        "This text normalises sexual or romantic contact between an adult and a child.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.45
    ENC_WEIGHT = 0.55
    OBFUSCATION_BOOST = 0.10
    THRESHOLD = 0.48

    KW_FLOOR_MULT = 0.85
    ENC_FLOOR_MULT = 0.78

    SKIP_ENCODER_ON_CLEAN = False

    def __init__(self):
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from encoder.backend import EncoderBackend
            self._encoder = EncoderBackend()
        return self._encoder

    def keyword_phase(
        self, original: str, normalized: str,
    ) -> tuple[float, list[str]]:
        return self.keyword_score_dual(
            original, normalized, self.HIGH, self.MED, self.LOW,
            med_w=0.20, low_w=0.05,
        )

    def classify(self, text: str, context: dict | None = None) -> dict:
        normalized = self.normalize(text)
        obf = self.get_obfuscation_score(text, normalized)

        kw_score, matched = self.keyword_score_dual(
            text, normalized, self.HIGH, self.MED, self.LOW,
            med_w=0.20, low_w=0.05,
        )

        encoder = self._get_encoder()
        enc_score = 0.0
        enc_details: dict[str, float] = {}
        enc_skipped = False

        if encoder.is_ready and self._should_run_encoder(kw_score, obf):
            scores = encoder.classify_zero_shot(
                normalized, self.HYPOTHESES, multi_label=True
            )
            if scores:
                enc_score = max(scores.values())
                enc_details = {k: round(v, 4) for k, v in scores.items()}
        elif encoder.is_ready:
            enc_skipped = True

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
            "encoder_scores": enc_details,
        }