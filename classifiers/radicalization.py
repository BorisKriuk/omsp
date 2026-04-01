from classifiers.base import BaseClassifier


class RadicalizationClassifier(BaseClassifier):
    name = "radicalization"
    version = "2.4.0"

    # ── Tier 1 — keywords ────────────────────────────────────
    HIGH = [
        "join the cause", "die for the cause",
        "enemies of our people", "ethnic cleansing",
        "race war", "white power", "final solution",
        "purge the unbelievers", "great replacement",
        "day of the rope", "accelerationism",
        "blood and soil", "rahowa", "siege culture",
        "race traitor", "white genocide", "holy crusade",
        "systematically replaced",
    ]
    MED = [
        "wake up sheeple", "they control everything",
        "zionist conspiracy", "us versus them",
        "pure blood", "traitors among us", "globalist agenda",
        "new world order", "deep state", "false flag",
        "cultural marxism", "based and redpilled",
        "fourteen words", "you will not replace us",
        "degenerate society", "cleanse the nation",
        "being replaced", "replace us", "our people",
        "we won't exist", "won't exist anymore",
        "protest time is over", "time for action",
        "subhuman", "vermin", "untermenschen",
        "demographic replacement", "mud people",
        # v2.4.0
        "fight back before", "take matters into",
        "our survival depends", "no political solution",
        "rise up against", "the enemy within",
    ]
    LOW = [
        "propaganda", "brainwashed", "red pill",
        "truth they hide", "mainstream lies", "movement",
        "patriot", "sovereign citizen", "identitarian",
        "echo chamber", "recruitment video",
        "open your eyes", "wake up and see",
        "parasites", "infestation", "mongrel",
        # v2.4.0
        "our kind", "our blood", "purity",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text contains extremist, supremacist, or radicalizing "
        "rhetoric that dehumanises or targets a group of people."
    )
    SCREEN_THRESHOLD = 0.03   # safety-critical
    DETAIL_KW_BYPASS = 0.02

    # ── Tier 2 — NLI hypotheses ──────────────────────────────
    HYPOTHESES = [
        "This text promotes an extremist ideology that dehumanises a racial, ethnic, or religious group.",
        "This text attempts to radicalise someone toward violent extremism or hateful ideology.",
        "This text contains white supremacist, neo-Nazi, or ethno-nationalist rhetoric.",
        "This text frames a specific group as an existential enemy that must be violently opposed.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.30
    ENC_WEIGHT = 0.70
    OBFUSCATION_BOOST = 0.10
    THRESHOLD = 0.57          # raised from 0.55 to reduce FP

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