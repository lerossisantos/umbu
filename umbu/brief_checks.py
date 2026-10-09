"""Brief compliance, package level. The campaign brief is a rule source like the
content standards: its mandatories have IDs (BR-xx) and an owner (the campaign owner).

  - Exact items run as code, per asset, inside the guardrail panel (price must match).
    Because they're in the panel, a reviewer's edit is re-checked against the brief too.
  - Items that need judgment ("is the Repair Promise actually communicated?") run once
    over the whole campaign, after review, using the approved copy where it exists."""
import datetime
import json
import re

from umbu.context import CONTEXT_DIR
from umbu.jsonutil import parse_json

PRICE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")


def load_mandatories() -> dict:
    path = CONTEXT_DIR / "brief_mandatories.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"mandatories": []}


def _texts(copy: dict):
    for field, value in copy.items():
        for v in (value if isinstance(value, list) else [value]):
            if isinstance(v, str):
                yield field, v


def _finding(rule_id, field, issue, quote="", fix="", severity="block"):
    return {"checker": "brief", "rule_id": rule_id, "field": field, "quote": quote, "issue": issue,
            "severity": severity, "confidence": "certain", "suggested_fix": fix}


def check_asset_brief(asset: dict) -> list[dict]:
    """Code checks for exact mandatories (today: price). Runs per asset in the panel."""
    findings = []
    for m in load_mandatories()["mandatories"]:
        if m.get("method") != "code" or m.get("type") != "price":
            continue
        want = m["price"].replace(" ", "")
        found = False
        for field, text in _texts(asset["copy"]):
            for price in PRICE.findall(text):
                if price.replace(" ", "") == want:
                    found = True
                else:
                    findings.append(_finding(m["id"], field, f"Shows {price}; the brief says {want}.",
                                             quote=price, fix=want))
        if asset["channel"] in m.get("required_in", []) and not found:
            findings.append(_finding(m["id"], "all", f"The brief requires the price {want} here, and it's missing.",
                                     fix=f"Add {want}"))
    return findings


def check_package(project, record: dict) -> dict:
    """Judgment checks over the whole campaign, using approved snapshots where they exist."""
    spec = load_mandatories()
    approved = {d["asset_id"]: d["approved_copy"] for d in record.get("decisions", [])
                if d.get("decision") == "Approve" and d.get("approved_copy")}
    assets = [{"asset_id": a["asset_id"], "channel": a["channel"],
               "copy": approved.get(a["asset_id"], a["copy"]),
               "version": "approved" if a["asset_id"] in approved else "current"}
              for a in record["assets"]]

    findings = []
    for a in assets:  # exact items, on the version that would ship
        for f in check_asset_brief(a):
            findings.append({**f, "asset_id": a["asset_id"]})

    to_judge = [m for m in spec["mandatories"] if m.get("method") == "model"]
    if to_judge:
        try:
            client = project.get_openai_client(agent_name="umbu-brief-checker")
            conversation = client.conversations.create()
            response = client.responses.create(conversation=conversation.id, input=json.dumps(
                {"mandatories": [{"id": m["id"], "text": m["text"]} for m in to_judge], "assets": assets}, indent=2))
            results = parse_json(response.output_text).get("results", [])
        except Exception as error:  # fail toward a person
            results = [{"rule_id": m["id"], "met": False, "asset_id": "campaign", "quote": "",
                        "issue": f"The brief checker did not return a result ({type(error).__name__}). A person must confirm this mandatory.",
                        "severity": "block", "confidence": "high", "suggested_fix": ""} for m in to_judge]
        for r in results:
            if r.get("severity") in ("warn", "block") or not r.get("met", False):
                findings.append({"checker": "brief", "rule_id": r.get("rule_id", "BR-??"),
                                 "asset_id": r.get("asset_id", "campaign"), "field": "message",
                                 "quote": r.get("quote", ""), "issue": r.get("issue", ""),
                                 "severity": r.get("severity") if r.get("severity") in ("warn", "block") else "block",
                                 "confidence": r.get("confidence", "medium"),
                                 "suggested_fix": r.get("suggested_fix", "")})

    return {"checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "brief_version": spec.get("brief_version", "v1"),
            "checked_versions": {a["asset_id"]: a["version"] for a in assets},
            "findings": findings,
            "status": "met" if not findings else "issues"}
