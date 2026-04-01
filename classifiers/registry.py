from __future__ import annotations
import logging
from classifiers.base import BaseClassifier

logger = logging.getLogger(__name__)


class ClassifierRegistry:
    """Thread-safe registry with two-phase batched encoder inference."""

    RELATED_GROUPS: list[frozenset[str]] = [
        frozenset({"terrorist", "radicalization"}),
        frozenset({"fraud", "spam"}),
    ]

    def __init__(self) -> None:
        self._classifiers: dict[str, BaseClassifier] = {}
        self._encoder = None

    def register(self, clf: BaseClassifier) -> None:
        self._classifiers[clf.name] = clf

    def unregister(self, name: str) -> None:
        self._classifiers.pop(name, None)

    def get(self, name: str) -> BaseClassifier | None:
        return self._classifiers.get(name)

    def classify_all(self, text: str, context: dict | None = None) -> dict:
        # Phase 0 — normalise once
        normalized = BaseClassifier.normalize(text)
        obf = BaseClassifier.get_obfuscation_score(text, normalized)

        # Phase 1 — keyword scoring for ALL classifiers (< 1 ms)
        kw_data: dict[str, tuple[float, list[str]]] = {}
        encoder_needed: dict[str, list[str]] = {}

        for name, clf in self._classifiers.items():
            kw_score, matched = clf.keyword_phase(text, normalized)
            kw_data[name] = (kw_score, matched)
            if clf._should_run_encoder(kw_score, obf):
                encoder_needed[name] = clf.HYPOTHESES

        # Phase 2 — TWO-PHASE batched encoder
        all_enc_scores: dict[str, dict[str, float]] = {}
        screen_only_names: set[str] = set()
        if encoder_needed:
            all_enc_scores, screen_only_names = self._batched_encoder_two_phase(
                normalized, encoder_needed, kw_data,
            )

        # Phase 3 — finalize each classifier
        results: dict[str, dict] = {}
        for name, clf in self._classifiers.items():
            kw_score, matched = kw_data[name]
            enc_scores = all_enc_scores.get(name, {})
            enc_skipped = name not in encoder_needed
            results[name] = clf.finalize(
                kw_score, matched, enc_scores, obf, enc_skipped,
            )
            if name in screen_only_names:
                results[name]["details"] += " [screen]"

        # Phase 4 — cross-classifier suppression
        self._suppress_related(results)
        return results

    # ── encoder helpers ──────────────────────────────────────
    def _get_encoder(self):
        if self._encoder is None:
            try:
                from encoder.backend import EncoderBackend
                self._encoder = EncoderBackend()
            except Exception:
                logger.exception("Cannot get encoder")
        return self._encoder

    def _batched_encoder_two_phase(
        self,
        normalized: str,
        encoder_needed: dict[str, list[str]],
        kw_data: dict[str, tuple[float, list[str]]],
    ) -> tuple[dict[str, dict[str, float]], set[str]]:
        """Two-phase encoder: screen broad hypotheses first, detail only
        where needed.

        Phase A — Screen:
            Run one broad hypothesis per classifier that needs screening.
            Classifiers with keyword signal bypass this via per-classifier
            DETAIL_KW_BYPASS.

        Phase B — Detail:
            Run full hypotheses for classifiers that passed screening
            or bypassed it.

        Returns:
            (classifier_name → {hypothesis: score}, set of screen-only names)
        """
        encoder = self._get_encoder()
        if encoder is None or not encoder.is_ready:
            return {}, set()

        # ── split: keyword-signal classifiers go straight to detail ──
        direct_detail: dict[str, list[str]] = {}
        needs_screen: dict[str, list[str]] = {}

        for name, hyps in encoder_needed.items():
            clf = self._classifiers[name]
            kw_score = kw_data.get(name, (0.0, []))[0]
            bypass = getattr(clf, "DETAIL_KW_BYPASS", 0.10)
            if kw_score >= bypass:
                direct_detail[name] = hyps
            else:
                needs_screen[name] = hyps

        # ── Phase A: screen ──
        name_to_screen_hyp: dict[str, str] = {}
        screen_hyp_list: list[str] = []
        screen_seen: set[str] = set()

        for name in list(needs_screen):
            clf = self._classifiers[name]
            sh = getattr(clf, "SCREEN_HYPOTHESIS", "")
            if sh:
                name_to_screen_hyp[name] = sh
                if sh not in screen_seen:
                    screen_hyp_list.append(sh)
                    screen_seen.add(sh)
            else:
                # No screen hypothesis → direct to detail
                direct_detail[name] = needs_screen.pop(name)

        screen_scores: dict[str, float] = {}
        if screen_hyp_list:
            screen_scores = encoder.classify_zero_shot(
                normalized, screen_hyp_list, multi_label=True,
            ) or {}

        # Decide who passed screening
        screen_only_names: set[str] = set()
        for name in needs_screen:
            clf = self._classifiers[name]
            sh = name_to_screen_hyp.get(name, "")
            s_score = screen_scores.get(sh, 0.0)
            threshold = getattr(clf, "SCREEN_THRESHOLD", 0.20)

            if s_score >= threshold:
                direct_detail[name] = encoder_needed[name]
            else:
                screen_only_names.add(name)

        # ── Phase B: detail ──
        detail_results: dict[str, dict[str, float]] = {}
        if direct_detail:
            all_hyps: list[str] = []
            detail_seen: set[str] = set()
            for hyps in direct_detail.values():
                for h in hyps:
                    if h not in detail_seen:
                        all_hyps.append(h)
                        detail_seen.add(h)

            if all_hyps:
                scores = encoder.classify_zero_shot(
                    normalized, all_hyps, multi_label=True,
                ) or {}
                for name, hyps in direct_detail.items():
                    detail_results[name] = {
                        h: scores.get(h, 0.0) for h in hyps
                    }

        # ── Merge: screen-only classifiers get just their screen score ──
        result: dict[str, dict[str, float]] = {}
        for name in screen_only_names:
            sh = name_to_screen_hyp.get(name, "")
            if sh:
                result[name] = {sh: screen_scores.get(sh, 0.0)}
            else:
                result[name] = {}
        result.update(detail_results)

        return result, screen_only_names

    # ── suppression ──────────────────────────────────────────
    def _suppress_related(self, results: dict) -> None:
        for group in self.RELATED_GROUPS:
            flagged = [
                (name, results[name])
                for name in group
                if name in results and results[name].get("flag") == 1
            ]
            if len(flagged) <= 1:
                continue
            best_name = max(flagged, key=lambda x: x[1]["confidence"])[0]
            for name, result in flagged:
                if name != best_name:
                    result["flag"] = 0
                    result["details"] += (
                        f" [suppressed: deferred to {best_name}]"
                    )

    def list_classifiers(self) -> list[dict]:
        return [
            {"name": c.name, "version": c.version}
            for c in self._classifiers.values()
        ]