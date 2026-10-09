"""Review rules, separate from the screens that show them.

The governance rules live here so every screen enforces them the same way:
  1. A reviewer's edits (manual or an accepted AI suggestion) go back through the
     full guardrail panel before anything is saved.
  2. Blocks can never be approved. Refused attempts are logged.
  3. Approving over a warning needs a written reason; the override goes to the rule's owner.
  4. Approved copy is stored as an exact snapshot."""
import datetime
import json

from umbu.context import RUNS_DIR
from umbu.governance import log_warning_overrides
from umbu.panel import route, run_panel
from umbu.record import load_record, save_record

CHANNEL_LABEL = {"google_rsa": "Google Search ad", "google_rda": "Google Display ad", "email": "Launch email"}
ROUTE_BADGE = {  # label, status kind
    "must_fix": ("Must fix", "block"),
    "review": ("Review", "warn"),
    "auto_pass": ("Auto-pass", "pass"),
}
ROUTE_ORDER = {"must_fix": 0, "review": 1, "auto_pass": 2}


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def list_runs():
    if not RUNS_DIR.exists():
        return []
    runs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "record.json").exists()
            and json.loads((p / "record.json").read_text(encoding="utf-8")).get("status") != "needs_input"]
    return sorted(runs, key=lambda p: p.name, reverse=True)


def run_label(path):
    """Time first, so runs of the same campaign can be told apart in a narrow dropdown."""
    import datetime
    record = load_record(path)
    scenario = record.get("scenario", {}).get("name") or "agents' copy"
    try:
        when = datetime.datetime.strptime(path.name[:15], "%Y%m%d-%H%M%S").strftime("%b %-d, %-I:%M %p")
    except ValueError:
        when = path.name
    return f"{when} · {scenario}"


def merge_findings(findings):
    """Code and model checkers can flag the same thing. Show it once, credit both."""
    merged = {}
    for f in findings:
        key = (f["rule_id"], f.get("field", ""))
        if key in merged:
            m = merged[key]
            if f["checker"] not in m["checkers"]:
                m["checkers"].append(f["checker"])
            if f["severity"] == "block":
                m["severity"] = "block"
        else:
            merged[key] = {**f, "checkers": [f["checker"]]}
    return sorted(merged.values(), key=lambda m: m["severity"] != "block")


def effective_route(findings, warn_policy="Send to review"):
    if any(f["severity"] == "block" for f in findings):
        return "must_fix"
    if findings and warn_policy == "Send to review":
        return "review"
    return "auto_pass"


def run_summary(run_dir, warn_policy="Send to review"):
    record = load_record(run_dir)
    checks = {c["asset_id"]: c for c in record.get("checks", [])}
    routes = {aid: effective_route(c["findings"], warn_policy) for aid, c in checks.items()}
    decided = {d["asset_id"] for d in record.get("decisions", [])}
    return {"record": record, "routes": routes, "decided": decided,
            "must_fix": sum(r == "must_fix" for r in routes.values()),
            "review": sum(r == "review" for r in routes.values()),
            "auto_pass": sum(r == "auto_pass" for r in routes.values())}


def apply_suggestions(copy, findings):
    """Replace each quoted phrase with the checker's suggested fix, field by field.
    Returns (edits, applied_rule_ids, skipped_rule_ids). Skips fixes whose quote is no
    longer present, and fixes that would repeat text already in the field (a model fix
    written for a longer span than its quote), so a person decides those."""
    def norm(t):
        return " ".join(t.lower().replace("!", "").replace(".", "").split())

    edits, applied, skipped = {}, [], []
    for f in findings:
        quote, fix, field = f.get("quote"), f.get("suggested_fix"), f.get("field", "")
        if not quote or not fix:
            continue
        for name, value in copy.items():
            if field and name not in field and not field.startswith(name):
                continue
            current = edits.get(name, value)
            texts = current if isinstance(current, list) else [current]
            target = next((t for t in texts if isinstance(t, str) and quote in t), None)
            if target is None:
                continue
            rest = target.replace(quote, " ")
            if norm(fix) and norm(fix) not in norm(quote) and norm(fix) in norm(rest):
                skipped.append(f["rule_id"])
                break
            if isinstance(current, list):
                new = [v.replace(quote, fix) if isinstance(v, str) else v for v in current]
            else:
                new = current.replace(quote, fix)
            edits[name] = new
            applied.append(f["rule_id"])
            break
    return edits, applied, skipped


def recheck(project, record, run_dir, asset, edits, editor, how):
    """Rule 1: edits go back through the full guardrail panel (incl. the brief price check)."""
    candidate = {**asset, "copy": {**asset["copy"], **edits}}
    new_findings = run_panel(project, candidate, run_dir)
    asset["copy"].update(edits)
    asset["edited_by"] = editor
    asset["edited_fields"] = sorted(set(asset.get("edited_fields", [])) | set(edits))
    asset["edit_method"] = how
    new_route, new_priority = route(new_findings)
    record["checks"] = [c for c in record["checks"] if c["asset_id"] != asset["asset_id"]] + [{
        "asset_id": asset["asset_id"], "findings": new_findings, "route": new_route,
        "priority": new_priority, "rechecked_after_edit_by": editor, "rechecked_at": now(), "edit_method": how}]
    save_record(run_dir, record)
    return new_findings


def decide(record, run_dir, asset, choice, note, reviewer, findings, route_now):
    """Rules 2-4. Returns (ok, message_kind, message)."""
    aid = asset["asset_id"]
    blocks = [f for f in findings if f["severity"] == "block"]
    warns = [f for f in findings if f["severity"] == "warn"]
    if choice == "Approve" and blocks:
        record.setdefault("audit", []).append({
            "event": "approval_refused", "asset_id": aid, "reviewer": reviewer, "timestamp": now(),
            "blocking_rules": [f["rule_id"] for f in blocks], "after_edit": bool(asset.get("edited_by"))})
        save_record(run_dir, record)
        return False, "error", ("Approval refused: " + ", ".join(f["rule_id"] for f in blocks) +
                                " still block this asset. Fix it first, or request changes / reject.")
    if choice == "Approve" and warns and not note.strip():
        return False, "warning", "This asset has warnings. Add a note explaining why it's OK to approve."
    decision = {
        "asset_id": aid, "decision": choice, "note": note, "reviewer": reviewer,
        "timestamp": now(), "route_at_review": route_now,
        "findings": [{"rule_id": f["rule_id"], "severity": f["severity"], "checkers": f["checkers"]}
                     for f in findings],
        "edited_fields": asset.get("edited_fields", []),
    }
    if choice == "Approve":
        decision["approved_copy"] = json.loads(json.dumps(asset["copy"]))  # exact snapshot
        if warns:
            log_warning_overrides(run_dir.name, asset, warns, reviewer, note, decision["timestamp"])
    record["decisions"] = [d for d in record.get("decisions", []) if d["asset_id"] != aid] + [decision]
    save_record(run_dir, record)
    msg = f"Saved: {choice}."
    if choice == "Approve" and warns:
        msg += " The warning override was sent to the rule's owner."
    return True, "success", msg
