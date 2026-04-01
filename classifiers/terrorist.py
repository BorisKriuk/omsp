from classifiers.base import BaseClassifier


class TerroristClassifier(BaseClassifier):
    name = "terrorist"
    version = "2.5.0"

    # ── Tier 1 — keyword lists ───────────────────────────────
    HIGH = [
        "bomb", "detonate", "explosive", "suicide attack", "jihad",
        "martyrdom operation", "kill infidels", "caliphate army",
        "weapons cache", "chemical weapon", "biological weapon",
        "dirty bomb", "ied", "mass casualty", "sleeper cell",
        "pledge allegiance to", "behead", "car bomb", "vest bomb",
        "shahid", "mujahideen", "takfir", "lone wolf attack",
        "coordinated strike", "pressure cooker bomb",
        "ammonium nitrate", "detonate the", "arm the device",
        "weapons stockpile",
    ]
    MED = [
        "radicalize", "extremist", "terror cell", "insurgent",
        "militant", "recruit fighters", "holy war", "armed uprising",
        "overthrow government", "guerrilla", "armed resistance",
        "violent struggle", "infidel", "kuffar", "crusader enemy",
        "operational security", "soft target",
        "the brothers", "remembered for generations",
        "won't stand", "pieces are in place",
        "strike the target", "awaiting the signal",
        "assets in position", "the operation begins",
        "ready to move on", "scope the location",
        "activate the cell", "ready to strike",
        # coded operational language
        "eyes on the", "the signal comes",
        "moving into position", "package is ready",
        "green light", "target is set",
        "await further instructions", "go dark",
        "we have eyes on", "final preparation",
        # v2.5.0 — phase/station language for coordinated attacks
        "phase two begins", "at their stations",
        "everyone is in position", "commence the operation",
    ]
    LOW = [
        "weapon", "attack plan", "target location", "operation",
        "recruit", "propaganda", "ideology", "resistance",
        "training camp", "safehouse", "secure channel",
        "blueprint", "manifesto",
        "high value target", "surveillance",
        "reconnaissance", "extraction point",
        # v2.5.0 — kept targeted terms, removed overly generic ones
        # Removed: "signal", "compound", "checkpoint", "perimeter"
        "embassy", "consulate", "operative", "handler",
        "intercept", "rendezvous",
    ]

    # ── Screen hypothesis ────────────────────────────────────
    SCREEN_HYPOTHESIS = (
        "This text involves or alludes to terrorism, violent attacks, "
        "weapons, surveillance, or covert operational planning."
    )
    # v2.5.0: raised from 0.03 to 0.08 — 0.03 was letting nearly
    # everything through, causing 24 FP.  Still well below the old
    # 0.20 that killed subtle recall.
    SCREEN_THRESHOLD = 0.08
    DETAIL_KW_BYPASS = 0.04   # v2.5.0: raised from 0.02 to need at least one LOW kw

    # ── Tier 2 — NLI hypotheses (detail phase) ───────────────
    HYPOTHESES = [
        "This text discusses planning or coordinating a violent attack on people.",
        "This text mentions acquiring or using weapons, explosives, or tools intended for mass harm.",
        "This text expresses allegiance to or support for a terrorist organization.",
        "This text uses coded, indirect, or operational language to coordinate surveillance, logistics, or timing of an attack.",
    ]

    # ── score combination ────────────────────────────────────
    KW_WEIGHT = 0.30
    ENC_WEIGHT = 0.70
    OBFUSCATION_BOOST = 0.10
    THRESHOLD = 0.52          # v2.5.0: raised from 0.50 to tighten FP

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