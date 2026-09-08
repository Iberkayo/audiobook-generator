from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class NormalizationEvent:
    source: str
    spoken: str
    kind: str
    start: int
    end: int


@dataclass
class NormalizationResult:
    source_text: str
    spoken_text: str
    events: List[NormalizationEvent] = field(default_factory=list)


ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
MONTHS = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}

COMMON_ABBREVIATIONS = {
    "Dr.": "Doktor",
    "Prof.": "Profesör",
    "Doç.": "Doçent",
    "vb.": "ve benzeri",
    "vs.": "vesaire",
    "örn.": "örneğin",
    "bkz.": "bakınız",
    "T.C.": "Türkiye Cumhuriyeti",
}


def _under_thousand(n: int) -> str:
    if n == 0:
        return ""
    parts: List[str] = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        if hundreds > 1:
            parts.append(ONES[hundreds])
        parts.append("yüz")
    tens, ones = divmod(rest, 10)
    if tens:
        parts.append(TENS[tens])
    if ones:
        parts.append(ONES[ones])
    return " ".join(parts)


def number_to_turkish(n: int) -> str:
    if n == 0:
        return "sıfır"
    if n < 0:
        return "eksi " + number_to_turkish(-n)

    scales = [
        (1_000_000_000, "milyar"),
        (1_000_000, "milyon"),
        (1_000, "bin"),
    ]
    parts: List[str] = []
    remaining = n
    for value, name in scales:
        q, remaining = divmod(remaining, value)
        if q:
            if value == 1_000 and q == 1:
                parts.append("bin")
            else:
                parts.append(number_to_turkish(q))
                parts.append(name)
    if remaining:
        parts.append(_under_thousand(remaining))
    return " ".join(p for p in parts if p)


class TurkishTextNormalizer:
    """Deterministic, auditable Turkish text normalization for audiobook speech.

    The normalizer deliberately handles only high-confidence transformations.
    Ambiguous items should remain untouched and can later be handled by a
    pronunciation lexicon or contextual resolver.
    """

    DATE_RE = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[./](0?[1-9]|1[0-2])[./](\d{4})\b")
    PERCENT_RE = re.compile(r"%(\d{1,3}(?:[.,]\d+)?)")
    TL_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:TL|₺)\b", re.I)
    INTEGER_RE = re.compile(r"(?<![\w%])\d{1,12}(?![\w])")

    def normalize(self, text: str) -> NormalizationResult:
        source = text
        events: List[NormalizationEvent] = []

        # We replace from right to left for every pass so source offsets remain
        # meaningful within that pass. Events retain the original matched text.
        text = self._replace_abbreviations(text, events)
        text = self._replace_regex(text, self.DATE_RE, self._date_spoken, "date", events)
        text = self._replace_regex(text, self.PERCENT_RE, self._percent_spoken, "percentage", events)
        text = self._replace_regex(text, self.TL_RE, self._currency_spoken, "currency_try", events)
        text = self._replace_regex(text, self.INTEGER_RE, self._integer_spoken, "integer", events)

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return NormalizationResult(source_text=source, spoken_text=text, events=events)

    def _replace_abbreviations(self, text: str, events: List[NormalizationEvent]) -> str:
        for source, spoken in COMMON_ABBREVIATIONS.items():
            pattern = re.compile(re.escape(source), re.I)
            text = self._replace_regex(text, pattern, lambda _: spoken, "abbreviation", events)
        return text

    def _replace_regex(self, text, pattern, formatter, kind, events):
        matches = list(pattern.finditer(text))
        for match in reversed(matches):
            spoken = formatter(match)
            events.append(
                NormalizationEvent(
                    source=match.group(0),
                    spoken=spoken,
                    kind=kind,
                    start=match.start(),
                    end=match.end(),
                )
            )
            text = text[: match.start()] + spoken + text[match.end() :]
        return text

    @staticmethod
    def _date_spoken(match: re.Match) -> str:
        day, month, year = map(int, match.groups())
        return f"{number_to_turkish(day)} {MONTHS[month]} {number_to_turkish(year)}"

    @staticmethod
    def _percent_spoken(match: re.Match) -> str:
        raw = match.group(1).replace(",", ".")
        if "." in raw:
            whole, frac = raw.split(".", 1)
            frac_words = " ".join(number_to_turkish(int(ch)) for ch in frac)
            return f"yüzde {number_to_turkish(int(whole))} virgül {frac_words}"
        return f"yüzde {number_to_turkish(int(raw))}"

    @staticmethod
    def _currency_spoken(match: re.Match) -> str:
        raw = match.group(1).replace(".", "").replace(",", ".")
        amount = float(raw)
        whole = int(amount)
        frac = int(round((amount - whole) * 100))
        if frac:
            return f"{number_to_turkish(whole)} Türk lirası {number_to_turkish(frac)} kuruş"
        return f"{number_to_turkish(whole)} Türk lirası"

    @staticmethod
    def _integer_spoken(match: re.Match) -> str:
        return number_to_turkish(int(match.group(0)))
