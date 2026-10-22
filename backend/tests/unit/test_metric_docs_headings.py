"""Every metric tooltip in the frontend links to a heading in docs/MARKET_RISK_METHODS.md.

If a heading is renamed or removed the link silently lands at the top of the page, so fail here instead.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
METHODS_MD = REPO / "docs" / "MARKET_RISK_METHODS.md"
GLOSSARY_TS = REPO / "frontend" / "lib" / "metric-docs.ts"


def _doc_headings() -> set[str]:
    return {
        re.sub(r"^#+\s*", "", line).strip()
        for line in METHODS_MD.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    }


def _glossary_headings() -> list[str]:
    return re.findall(r'heading:\s*"([^"]+)"', GLOSSARY_TS.read_text(encoding="utf-8"))


def test_glossary_has_entries():
    assert len(_glossary_headings()) >= 20


def test_every_glossary_heading_exists_in_methods_doc():
    doc = _doc_headings()
    missing = [h for h in _glossary_headings() if h not in doc]
    assert not missing, f"metric-docs.ts points at headings missing from MARKET_RISK_METHODS.md: {missing}"
