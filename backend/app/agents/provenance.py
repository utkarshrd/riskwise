"""
Number provenance guard for copilot replies.

Rule: a number in a reply is allowed only if it can be traced to
  1. a tool output or tool argument from this turn (including numbers inside its text fields, such as dates),
  2. a retrieved citation, or
  3. the user's own message.
Nothing else gets a pass for being a percentage, an amount or "small". The only exemptions are a short, explicit
list of methodology constants and section references (see METHODOLOGY_CONSTANTS).

A line containing an unsourced number is removed from the reply and reported, so the copilot never shows a figure
that no deterministic service produced.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

# Constants that appear in the copilot's fixed wording and are definitions, not computed results.
METHODOLOGY_CONSTANTS: frozenset[float] = frozenset({252.0, 95.0, 99.0, 100.0})

_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SECTION_REF = re.compile(r"§\s*\d+(?:\.\d+)*")
# A numeric token, not glued to a word (so "3MINDIA" or "p2" are not numbers), with optional sign.
_NUMBER = re.compile(r"(?<![\w.^=])([-+−]?)(\d[\d,]*(?:\.\d+)?)(?![A-Za-z_])")
_LEADING_MARKER = re.compile(r"^\s*(?:[-*•>]|\d+[.)])\s+")


class ProvenanceFlag(BaseModel):
    token: str
    context: str
    action: str  # "removed"
    reason: str


class GuardResult(BaseModel):
    answer: str
    flags: list[ProvenanceFlag]
    checked: int  # numeric tokens examined


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def numbers_in(text: str) -> list[tuple[str, float, int]]:
    """(token, value, decimals) for each number in text, ignoring ISO dates and section references."""
    scrubbed = _SECTION_REF.sub(" ", _ISO_DATE.sub(" ", text))
    found: list[tuple[str, float, int]] = []
    for m in _NUMBER.finditer(scrubbed):
        value = _to_float(m.group(2))
        if value is None:
            continue
        decimals = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
        found.append((m.group(2), value, decimals))
    return found


_KEY_DIGITS = re.compile(r"\d+(?:\.\d+)?")


def _collect(obj: Any, values: list[float], texts: list[str], key_numbers: list[float]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        values.append(abs(float(obj)))
    elif isinstance(obj, str):
        texts.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            # keys label the numbers (historical_var_95), and digits glued to words are read here, not by numbers_in
            key_numbers.extend(float(d) for d in _KEY_DIGITS.findall(str(k)))
            _collect(v, values, texts, key_numbers)
    elif isinstance(obj, Iterable):
        for v in obj:
            _collect(v, values, texts, key_numbers)


class SourcePool:
    """Everything a number in the reply may legitimately come from."""

    def __init__(self, sources: list[Any], user_message: str = ""):
        values: list[float] = []
        key_numbers: list[float] = []
        texts: list[str] = [user_message]
        for s in sources:
            _collect(s, values, texts, key_numbers)

        scaled: list[float] = []
        for v in values:
            scaled.append(v)
            scaled.append(v * 100.0)  # a fraction shown as a percentage
            scaled.append(v / 12.0)  # months shown as years
        self.values = scaled

        self.text_numbers: list[float] = list(key_numbers)
        self.dates: set[str] = set()
        for t in texts:
            self.dates.update(_ISO_DATE.findall(t))
            self.text_numbers.extend(v for _, v, _ in numbers_in(t))

    def has(self, value: float, decimals: int) -> bool:
        # A displayed number is a rounding of the real one, so allow half a unit in its last shown digit
        tol = 0.5 * 10 ** (-decimals) * (1 + 1e-9) + 1e-12
        for pool in (self.text_numbers, self.values):
            if any(abs(value - p) <= tol for p in pool):
                return True
        return value in METHODOLOGY_CONSTANTS


def check_answer(answer: str, sources: list[Any], user_message: str = "") -> GuardResult:
    """Remove every line whose numbers cannot be traced to a source, and report what was removed."""
    pool = SourcePool(sources, user_message)
    kept: list[str] = []
    flags: list[ProvenanceFlag] = []
    checked = 0

    for line in answer.split("\n"):
        problems: list[str] = []
        for date in _ISO_DATE.findall(line):
            checked += 1
            if date not in pool.dates:
                problems.append(date)
        for token, value, decimals in numbers_in(line):
            checked += 1
            if not pool.has(value, decimals):
                problems.append(token)

        if not problems:
            kept.append(line)
            continue

        stripped = _LEADING_MARKER.sub("", line).strip()
        for token in problems:
            flags.append(
                ProvenanceFlag(
                    token=token,
                    context=stripped[:120],
                    action="removed",
                    reason="No tool output, citation or user message contains this figure, so it was removed.",
                )
            )
        marker = _LEADING_MARKER.match(line)
        kept.append(f"{marker.group(0) if marker else ''}[removed: a figure here had no computed source]")

    return GuardResult(answer="\n".join(kept), flags=flags, checked=checked)
