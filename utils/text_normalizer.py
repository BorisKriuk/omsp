"""
Obfuscation-resistant text normaliser.

Handles:
  • Homoglyphs  (Cyrillic/Greek → Latin, fullwidth → ASCII)
  • Invisible / zero-width characters
  • Bidi override characters
  • Leetspeak  (0→o  3→e  4→a  $→s  …)
  • Separator insertion  (b.o.m.b → bomb)
  • Repeated-character compression  (helllp → hellp)
"""

import re
import unicodedata

# ── homoglyph map ────────────────────────────────────────────
_HOMOGLYPHS: dict[str, str] = {
    # Cyrillic → Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "ԁ": "d", "ԛ": "q", "ԝ": "w",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M",
    "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    # Greek → Latin
    "α": "a", "β": "b", "ε": "e", "η": "n", "ι": "i",
    "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t",
    "υ": "u", "ω": "w",
    # Fullwidth ASCII (！through ～ → ! through ~)
    **{chr(0xFF01 + i): chr(0x21 + i) for i in range(94)},
}

# ── leetspeak (single-char) ─────────────────────────────────
_LEET: dict[str, str] = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g", "@": "a", "$": "s",
    "!": "i", "|": "l", "+": "t",
}

# ── leetspeak (multi-char, applied first) ────────────────────
_LEET_MULTI: list[tuple[str, str]] = [
    ("ph", "f"),
    ("vv", "w"),
]

# ── regex patterns ───────────────────────────────────────────
_INVISIBLE_RE = re.compile(
    "["
    "\u200b\u200c\u200d\u200e\u200f"   # zero-width space / joiners / marks
    "\u2060\u2061\u2062\u2063\u2064"    # word joiner, invisible operators
    "\ufeff"                             # BOM / ZWNBSP
    "\u00ad"                             # soft hyphen
    "\u034f"                             # combining grapheme joiner
    "\u061c"                             # Arabic letter mark
    "\u115f\u1160"                       # Hangul fillers
    "\u17b4\u17b5"                       # Khmer inherent vowels
    "\uffa0"                             # halfwidth Hangul filler
    "]"
)

_BIDI_RE = re.compile("[\u202a-\u202e\u2066-\u2069]")

_SEPARATOR_RE = re.compile(r"(?<=\w)[.\-_\s]{1,3}(?=\w)")

_REPEAT_RE = re.compile(r"(.)\1{2,}")


# ── public API ───────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Strip obfuscation and return a clean, lowercased string
    suitable for keyword matching and encoder input.
    """
    # 1  remove invisible / zero-width characters
    text = _INVISIBLE_RE.sub("", text)

    # 2  remove bidi overrides
    text = _BIDI_RE.sub("", text)

    # 3  NFKC (decomposes fullwidth, ligatures, compat forms)
    text = unicodedata.normalize("NFKC", text)

    # 4  homoglyph replacement
    text = "".join(_HOMOGLYPHS.get(ch, ch) for ch in text)

    # 5  lowercase
    text = text.lower()

    # 6  multi-char leetspeak
    for src, dst in _LEET_MULTI:
        text = text.replace(src, dst)

    # 7  single-char leetspeak
    text = "".join(_LEET.get(ch, ch) for ch in text)

    # 8  collapse separator insertion  (b.o.m.b → bomb)
    text = _SEPARATOR_RE.sub("", text)

    # 9  collapse 3+ repeated chars → 2  (helllp → hellp)
    text = _REPEAT_RE.sub(r"\1\1", text)

    # 10 normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def obfuscation_score(original: str, normalized: str) -> float:
    """
    0.0–1.0 score based on *specific* evasion indicators only:
      • invisible / bidi characters   (weight 0.50)
      • homoglyphs                    (weight 0.30)
      • leetspeak in alpha context    (weight 0.20)

    Normal capitalisation, punctuation, and Unicode (emoji, smart
    quotes, CJK) no longer inflate the score.
    """
    if not original:
        return 0.0

    total = max(len(original), 1)

    # 1 — invisible / bidi characters
    inv_count = len(_INVISIBLE_RE.findall(original)) + len(_BIDI_RE.findall(original))
    inv_ratio = min(inv_count / total * 5.0, 1.0)

    # 2 — homoglyphs
    hg_count = sum(1 for c in original if c in _HOMOGLYPHS)
    hg_ratio = min(hg_count / total * 3.0, 1.0)

    # 3 — leetspeak adjacent to letters (avoids "$5" or "24/7")
    leet_count = 0
    for i, ch in enumerate(original):
        if ch in _LEET:
            prev_alpha = i > 0 and original[i - 1].isalpha()
            next_alpha = i < len(original) - 1 and original[i + 1].isalpha()
            if prev_alpha or next_alpha:
                leet_count += 1
    leet_ratio = min(leet_count / total * 3.0, 1.0)

    score = 0.50 * inv_ratio + 0.30 * hg_ratio + 0.20 * leet_ratio
    return min(score, 1.0)