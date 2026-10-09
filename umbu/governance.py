"""Guardrail governance: when a reviewer approves content over a warning, the override
is logged and routed to the owner of that rule. The owner decides:
  1. change the guardrail, or keep it as is
  2. if kept: the content can stay live, or ask the content owner to take it down
Overrides live in runs/overrides.json because they span campaigns."""
import json

from umbu.context import CONTEXT_DIR, RUNS_DIR

OVERRIDES_FILE = RUNS_DIR / "overrides.json"
_OWNERS = json.loads((CONTEXT_DIR / "rule_owners.json").read_text(encoding="utf-8"))

OPEN = "open"
CHANGE_REQUESTED = "guardrail_change_requested"
KEPT_LIVE = "kept_content_stays_live"
KEPT_TAKEDOWN = "kept_takedown_requested"
STANDARDS_UPDATE = "standards_update_requested"
STATUS_LABEL = {
    OPEN: "Open",
    CHANGE_REQUESTED: "Rule change requested",
    KEPT_LIVE: "Rule stands · content stays as is",
    KEPT_TAKEDOWN: "Rule stands · content owner asked to adjust it",
    STANDARDS_UPDATE: "Standards update requested",
}

# What the owner decides happened, and how that decision is used for learning.
# Every resolved override carries exactly one label, so human decisions stay usable as a signal.
OUTCOMES = [
    {"key": "reviewer_error", "name": "Reviewer overrode a correct rule",
     "desc": "The rule and the checker were right; the approval was a mistake.",
     "label": "Reviewer error · reinforces the checker, override not used", "step2": True},
    {"key": "checker_error", "name": "Checker applied the rule wrongly",
     "desc": "The rule is right, but the checker misread the content.",
     "label": "Checker error · used to improve the checker", "step2": True},
    {"key": "rule_change", "name": "Change the rule",
     "desc": "The rule was applied as written, but our policy should change.",
     "label": "Rule change · used for learning under the new rule version", "step2": False},
    {"key": "outdated_standards", "name": "Rule is out of date with its source",
     "desc": "The source changed (e.g. a new regulation); update the standards and re-check affected content.",
     "label": "Outdated standards · past findings excluded from calibration", "step2": True},
]


def owner_for(rule_id: str) -> dict:
    matches = [p for p in _OWNERS["owners"] if rule_id.startswith(p)]
    return _OWNERS["owners"][max(matches, key=len)] if matches else _OWNERS["default"]


def all_owners() -> list[str]:
    return sorted({o["owner"] for o in _OWNERS["owners"].values()} | {_OWNERS["default"]["owner"]})


def load_overrides() -> list[dict]:
    if OVERRIDES_FILE.exists():
        return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return []


def save_overrides(items: list[dict]) -> None:
    RUNS_DIR.mkdir(exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def log_warning_overrides(run_id, asset, warnings, reviewer, note, timestamp):
    """Called when a reviewer approves an asset that still has warnings."""
    items = load_overrides()
    for f in warnings:
        oid = f"{run_id}:{asset['asset_id']}:{f['rule_id']}:{f.get('field', '')}"
        items = [i for i in items if i["id"] != oid]
        owner = owner_for(f["rule_id"])
        items.append({
            "id": oid, "run_id": run_id, "asset_id": asset["asset_id"], "channel": asset["channel"],
            "rule_id": f["rule_id"], "owner": owner["owner"], "rule_file": owner["file"],
            "field": f.get("field", ""), "quote": f.get("quote", ""), "issue": f.get("issue", ""),
            "suggested_fix": f.get("suggested_fix", ""), "checkers": f.get("checkers", []),
            "reviewer": reviewer, "reviewer_note": note, "approved_at": timestamp,
            "approved_copy": asset["copy"],
            "status": OPEN, "owner_decision": None,
        })
    save_overrides(items)


def takedowns_for_run(run_id) -> dict:
    """asset_id -> override items where the owner asked for the content to come down."""
    out = {}
    for i in load_overrides():
        if i["run_id"] == run_id and i["status"] == KEPT_TAKEDOWN:
            out.setdefault(i["asset_id"], []).append(i)
    return out
