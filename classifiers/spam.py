from classifiers.base import BaseClassifier


class SpamClassifier(BaseClassifier):
    name = "spam"
    version = "2.6.0"

    # ── Tier 1 — keywords ────────────────────────────────────
    HIGH = [
        "buy now", "free trial", "click here to claim",
        "congratulations you won", "act immediately",
        "million dollars", "100% free", "no obligation",
        "click the link", "claim your prize",
        "you have been selected", "act now",
        "limited time offer", "risk free",
        "order now", "call now", "won a prize",
        "you are a winner",
        "you won", "you have won",
        "act today", "act fast",
        "not a scam", "this is not spam",
        "this isn't spam", "totally legit",
    ]
    MED = [
        "limited offer", "exclusive deal", "sign up today",
        "discount code", "unsubscribe", "promotional",
        "earn money fast", "work from home opportunity",
        "dm me for details", "message me privately",
        "before they patch", "get it for free",
        "double your income", "no experience needed",
        "be your own boss", "make money online",
        "casino bonus", "forex signal", "crypto opportunity",
        "dm me", "secret method", "they don't want you to know",
        "loophole", "hack to get",
        "crazy deal", "insane deal", "amazing deal",
        "unreal savings", "save big", "massive discount",
        "if you act today",
        "just pay shipping", "pay shipping only",
        "free samples", "giving away free",
        "made money from home", "income from home",
        "paid survey", "make money while you sleep",
        "passive income secret", "financial freedom",
        "i promise you", "trust me on this",
        "link in bio", "swipe up",
        "click here", "tap here", "sign up now",
    ]
    LOW = [
        "cheap", "winner", "prize",
        "subscribe", "giveaway", "coupon",
        "bonus", "cashback", "discount",
        "free gift", "exclusive access", "vip",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text is spam or unsolicited commercial advertising."
    )
    SCREEN_THRESHOLD = 0.25
    DETAIL_KW_BYPASS = 0.10

    # ── Tier 2 — NLI hypotheses ──────────────────────────────
    HYPOTHESES = [
        "This text is unsolicited commercial spam or advertising.",
        "This text uses urgency or fake scarcity to push a commercial offer.",
        "This text offers something free or too-good-to-be-true through unofficial or private channels.",
        "This text uses personal income claims to lure people into a money-making scheme.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.55
    ENC_WEIGHT = 0.45
    OBFUSCATION_BOOST = 0.08
    THRESHOLD = 0.52          # v2.6: backed down from 0.55 — was overcorrecting

    KW_FLOOR_MULT = 0.85
    ENC_FLOOR_MULT = 0.70

    # ── encoder gating ───────────────────────────────────────
    # v2.6: keep SKIP_ENCODER_ON_CLEAN but lower the kw trigger
    # so a single LOW keyword (score=0.04) still gets encoder support.
    SKIP_ENCODER_ON_CLEAN = True
    MIN_KW_FOR_ENCODER = 0.03   # was 0.05 — missed subtle spam with 1 LOW kw

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

        kw_score, matched = self.keyword_score_dual(
            text, normalized, self.HIGH, self.MED, self.LOW,
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