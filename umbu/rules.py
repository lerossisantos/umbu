"""Looks up a rule's text by its ID from the content standards (the markdown tables in
context/), so screens can show the rule behind a code without hard-coding it."""
import functools
import json
import re

from umbu.context import CONTEXT_DIR

FILES = ["brand_voice.md", "approved_claims.md", "regulations.md", "channel_specs.md"]
_ROW = re.compile(r"^\|\s*([A-Z]{2,3}(?:-[A-Z]+)?-?\d{0,2}[A-Z0-9-]*)\s*\|\s*(.+?)\s*\|")


@functools.lru_cache(maxsize=1)
def _index() -> dict:
    out = {}
    for name in FILES:
        path = CONTEXT_DIR / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = _ROW.match(line)
            if m and m.group(1) not in ("ID",):
                out.setdefault(m.group(1), (m.group(2).strip(), name))
    briefs = CONTEXT_DIR / "brief_mandatories.json"
    if briefs.exists():
        for mnd in json.loads(briefs.read_text(encoding="utf-8")).get("mandatories", []):
            out[mnd["id"]] = (mnd["text"], "campaign_brief.md")
    out.setdefault("SYS-01", ("A checker failed to return a result; a person must review", "umbu/panel.py"))
    out.setdefault("CH-MIN", ("Minimum copy length so long placements aren't left half empty", "channel_specs.md"))
    return out


def rule_text(rule_id: str) -> str:
    return _index().get(rule_id, ("", ""))[0].strip('"')


def rule_file(rule_id: str) -> str:
    return _index().get(rule_id, ("", ""))[1]
