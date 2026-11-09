"""Normalise acupuncture point codes to WHO standard notation (e.g. LI4, TE5, LR3).

Sources write codes in many ways: "LI4", "LI 4", "LI-04", "Lu 07", "St20",
and use older meridian abbreviations ("TB", "TW", "SJ" for TE; "LV" for LR;
"Pe" for PC; "MP" for SP). `normalize_codes` rewrites them in text so point
codes can be matched reliably.
"""

import re

# Meridian abbreviations (upper-cased) to WHO codes.
MERIDIANS = {
    "LU": "LU",
    "LI": "LI",
    "ST": "ST",
    "SP": "SP",
    "MP": "SP",
    "HT": "HT",
    "SI": "SI",
    "BL": "BL",
    "UB": "BL",
    "KI": "KI",
    "KID": "KI",
    "PC": "PC",
    "PE": "PC",
    "P": "PC",
    "TE": "TE",
    "TB": "TE",
    "TW": "TE",
    "SJ": "TE",
    "GB": "GB",
    "LR": "LR",
    "LV": "LR",
    "LIV": "LR",
    "GV": "GV",
    "DU": "GV",
    "CV": "CV",
    "REN": "CV",
}

# Meridian abbreviation in any case, optional space or hyphen, then 1-2 digits.
# "P" alone is too ambiguous in prose, so it is only matched in `code_from_parts`.
_CODE = re.compile(
    r"(?<![\w-])("
    + "|".join(sorted((m for m in MERIDIANS if m != "P"), key=len, reverse=True))
    + r")[ -]?0?(\d{1,2})(?![\w-])",
    re.IGNORECASE,
)


def code_from_parts(meridian: str, number: str | int) -> str | None:
    """WHO code for a meridian abbreviation and point number, or None if unknown."""
    prefix = MERIDIANS.get(meridian.upper())
    return f"{prefix}{int(number)}" if prefix and int(number) > 0 else None


def normalize_codes(text: str) -> str:
    """Rewrite every recognised point code in `text` to WHO notation."""

    def replace(match: re.Match[str]) -> str:
        return code_from_parts(match.group(1), match.group(2)) or match.group(0)

    return _CODE.sub(replace, text)
