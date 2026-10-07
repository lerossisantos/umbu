"""Step 3 of the pipeline: the guardrail panel.
Runs 3 checkers on every asset, then routes each asset to auto-pass or the review queue.

  python run_checks.py                      check the latest run as the agents wrote it
  python run_checks.py --scenario vp_edits  copy the latest run, apply the VP's edits, check that copy
"""
import argparse
import json
import shutil

from umbu.context import ROOT
from umbu.foundry import get_project
from umbu.jsonutil import parse_json
from umbu.record import latest_run_dir, load_record, save_record
from umbu.spec_checks import check_asset

MODEL_CHECKERS = {
    "claims": "umbu-claims-checker",
    "brand_voice": "umbu-brand-voice-checker",
}


def apply_scenario(run_dir, scenario_name):
    scenario = json.loads((ROOT / "scenarios" / f"{scenario_name}.json").read_text(encoding="utf-8"))
    new_dir = run_dir.parent / f"{run_dir.name.split('-' + scenario_name)[0]}-{scenario_name}"
    if new_dir.exists():
        shutil.rmtree(new_dir)
    shutil.copytree(run_dir, new_dir)
    record = load_record(new_dir)
    record["scenario"] = {"name": scenario["name"], "story": scenario["story"]}
    for asset in record["assets"]:
        edits = scenario["edits"].get(asset["asset_id"])
        if edits:
            asset["copy"].update(edits)
            asset["edited_by"] = scenario["edited_by"]
            asset["edited_fields"] = list(edits)
    save_record(new_dir, record)
    print(f"Scenario: {scenario['name']}\n{scenario['story']}\n")
    return new_dir


def ask_checker(project, agent_name, asset):
    payload = {"asset_id": asset["asset_id"], "channel": asset["channel"], "copy": asset["copy"],
               "claims_used": asset.get("claims_used", []),
               "alt_text": asset.get("image", {}).get("alt_text")}
    client = project.get_openai_client(agent_name=agent_name)
    conversation = client.conversations.create()
    response = client.responses.create(conversation=conversation.id, input=json.dumps(payload, indent=2))
    return parse_json(response.output_text).get("findings", [])


def route(findings):
    """Routing policy: anything flagged goes to a person. Blocks must be fixed first."""
    if not findings:
        return "auto_pass", None
    if any(f["severity"] == "block" for f in findings):
        return "review_queue", "must_fix"
    return "review_queue", "review"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="name of a file in scenarios/ to apply before checking")
    args = parser.parse_args()

    run_dir = latest_run_dir() if not args.scenario else None
    if args.scenario:
        base = sorted(p for p in (ROOT / "runs").iterdir() if p.is_dir() and "-" + args.scenario not in p.name)[-1]
        run_dir = apply_scenario(base, args.scenario)

    record = load_record(run_dir)
    project = get_project()
    record["checks"] = []

    for asset in record["assets"]:
        aid = asset["asset_id"]
        print(f"[{aid}] checking...")
        findings = check_asset(asset, run_dir)
        for checker, agent in MODEL_CHECKERS.items():
            for f in ask_checker(project, agent, asset):
                f["checker"] = checker
                findings.append(f)
        decision, priority = route(findings)
        record["checks"].append({"asset_id": aid, "findings": findings, "route": decision, "priority": priority})
        save_record(run_dir, record)

    print("\n=== Guardrail panel results ===")
    for c in record["checks"]:
        label = "AUTO-PASS" if c["route"] == "auto_pass" else f"REVIEW QUEUE ({c['priority']})"
        print(f"\n{c['asset_id']}: {label}")
        for f in c["findings"]:
            print(f"  [{f['severity'].upper():5}] {f['checker']:12} {f['rule_id']:9} {f['field']}: {f['issue']}")
    print(f"\nSaved to {run_dir / 'record.json'}")


if __name__ == "__main__":
    main()
