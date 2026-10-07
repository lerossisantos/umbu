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
STATUS_LABEL = {
    OPEN: "Open",
    CHANGE_REQUESTED: "Guardrail change requested",
    KEPT_LIVE: "Kept guardrail · content stays live",
    KEPT_TAKEDOWN: "Kept guardrail · takedown requested",
}


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
