from classifiers.base import BaseClassifier


class FraudClassifier(BaseClassifier):
    name = "fraud"
    version = "2.4.0"

    # ── Tier 1 — keywords ────────────────────────────────────
    # NOTE: compound phrases split so intervening words don't break match.
    # e.g. "wire transfer" matches "wire transfer $500 now".
    HIGH = [
        "send me your bank", "bank details",
        "wire transfer", "nigerian prince", "advance fee",
        "won the lottery", "send bitcoin to",
        "money laundering", "phishing",
        "steal identity", "credit card number",
        "update payment info", "update payment details",
        "subscription will be cancelled",
        "account has been compromised",
        "confirm your payment immediately",
        "routing number", "send me your ssn",
        "enter your social security", "give me your password",
        "send your login", "share your credentials",
        # v2.4.0
        "claim your prize", "claim your reward",
        "you've been selected", "you have been selected",
    ]
    MED = [
        "verify your account", "click this link urgently",
        "investment guaranteed return", "double your money",
        "act now or lose", "reset your password here",
        "inheritance fund", "unclaimed funds", "western union",
        "cryptocurrency opportunity",
        "tech support", "remote access", "security alert",
        "verify your identity", "suspended your account",
        "unauthorized transaction", "call this number",
        "confirm your details", "your account will be closed",
        "i need access", "fix a critical",
        "from tech support", "customer service representative",
        "update your payment", "will be cancelled unless",
        "at this link", "payment information",
        "billing information", "account will be suspended",
        "renew your subscription", "payment method on file",
        "unless you verify", "unless you update",
        "unless you confirm",
        "been selected", "rewards program", "verify now",
        "verify immediately", "tax refund", "refund pending",
        "enter your bank", "processing fee",
        "pay a small fee",
        "transfer to this account", "within 24 hours",
        "within 48 hours", "account locked",
        "won a gift card", "redeem your",
        "confirm your identity by",
        # v2.4.0
        "click here to claim", "click this link",
        "your prize", "your reward",
        "congratulations you", "you are eligible",
        "selected for an exclusive", "exclusive offer for you",
    ]
    LOW = [
        "bank account", "transfer money", "payment",
        "urgent", "limited time", "deal", "profit guaranteed",
        "risk free", "earn from home",
        "credentials", "login details", "password",
        "social security", "ssn", "vulnerability",
        "refund", "expiring soon", "immediate action",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text attempts to deceive, scam, or phish the reader "
        "into giving up money or personal information."
    )
    SCREEN_THRESHOLD = 0.15
    DETAIL_KW_BYPASS = 0.10

    # ── Tier 2 — NLI hypotheses ──────────────────────────────
    HYPOTHESES = [
        "This text is attempting to trick someone into sending money or financial assets.",
        "This text is a phishing attempt to steal personal information, passwords, or credentials.",
        "This text impersonates a bank, company, or authority to deceive the recipient.",
        "This text pressures someone to act urgently on a fraudulent financial request.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.30
    ENC_WEIGHT = 0.70
    OBFUSCATION_BOOST = 0.10
    THRESHOLD = 0.50

    KW_FLOOR_MULT = 0.88
    ENC_FLOOR_MULT = 0.80

    # Fraud is keyword-heavy — skip encoder when no keywords fire.
    SKIP_ENCODER_ON_CLEAN = True

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