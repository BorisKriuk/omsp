from classifiers.base import BaseClassifier


class SelfHarmClassifier(BaseClassifier):
    name = "self_harm"
    version = "2.4.0"

    # ── Tier 1 — keywords ────────────────────────────────────
    HIGH = [
        "kill myself", "end my life", "suicide plan",
        "want to die", "no reason to live", "cut myself",
        "overdose", "hang myself", "jump off",
        "goodbye letter", "final note",
        "wish I wasn't born", "wish I was never born",
        "i give up on life", "going to end it",
    ]
    MED = [
        "self harm", "hurting myself", "don't want to exist",
        "better off dead", "can't go on", "nobody would miss me",
        "planning to end it", "pills to sleep forever",
        "everything is pointless", "nothing matters anymore",
        "want to disappear", "don't want to wake up",
        "want it all to end", "can't keep going",
        "nobody would care", "the pain to stop",
        "better without me", "world without me",
        "i'm a burden", "burden to everyone",
        "not worth saving", "tired of fighting",
        "don't want to be here", "want to stop existing",
        # method-related
        "painkillers", "how many pills",
        "pills it would take", "slit my wrist",
        "razor blade", "tie the rope",
        "jump from the", "bridge railing",
        "lethal dose", "enough pills to",
        "carbon monoxide", "exit bag",
        # v2.4.0 — additional method inquiry patterns
        "how many painkillers", "painkillers it would take",
        "looked up how many", "how to cut deep",
    ]
    LOW = [
        "depressed", "hopeless", "worthless", "empty inside",
        "can't take it", "tired of living", "numb",
        "alone", "broken", "suffering",
        "tired of pretending", "why am I still here",
        "no point anymore", "what's the use",
        "pills", "blade", "rope",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text expresses distress, hopelessness, suicidal thoughts, "
        "or intentions of self-harm."
    )
    # v2.4.0: raised from 0.03 to 0.05 — was generating 6 FP
    SCREEN_THRESHOLD = 0.05
    DETAIL_KW_BYPASS = 0.02

    # ── Tier 2 — NLI hypotheses ──────────────────────────────
    HYPOTHESES = [
        "This person is expressing a plan or intent to commit suicide.",
        "This person is in severe emotional crisis and may be an immediate danger to themselves.",
        "This person is expressing a wish to disappear, not exist, or not wake up, indicating passive suicidal ideation.",
        "This text is a suicide note or final goodbye message.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.30
    ENC_WEIGHT = 0.70
    OBFUSCATION_BOOST = 0.10
    THRESHOLD = 0.48

    KW_FLOOR_MULT = 0.72
    ENC_FLOOR_MULT = 0.80

    SKIP_ENCODER_ON_CLEAN = False

    def __init__(self):
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from encoder.backend import EncoderBackend
            self._encoder = EncoderBackend()
        return self._encoder

    def classify(self, text: str, context: dict | None = None) -> dict:
        normalized = self.normalize(text)
        obf = self.get_obfuscation_score(text, normalized)

        kw_score, matched = self.keyword_score(
            normalized, self.HIGH, self.MED, self.LOW
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