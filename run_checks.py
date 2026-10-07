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
from umbu.panel import route, run_panel
from umbu.record import latest_run_dir, load_record, save_record



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
        findings = run_panel(project, asset, run_dir)
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
