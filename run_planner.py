"""Step 1 of the pipeline: send the campaign brief to the Planner agent
and start a new campaign record in runs/<timestamp>/record.json.

  python run_planner.py                                  plan the campaign brief in context/
  python run_planner.py --brief scenarios/brief_conflict.md   try another brief

If the brief conflicts with itself or with brand policy, the Planner asks
instead of guessing: the questions are saved and the pipeline stops."""
import argparse
import datetime
import json
import sys
from pathlib import Path

from umbu.context import CONTEXT_DIR, RUNS_DIR
from umbu.foundry import get_project
from umbu.jsonutil import parse_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", help="path to a brief file (default: context/campaign_brief.md)")
    args = parser.parse_args()
    brief_path = Path(args.brief) if args.brief else CONTEXT_DIR / "campaign_brief.md"
    brief = brief_path.read_text(encoding="utf-8")

    project = get_project()
    client = project.get_openai_client(agent_name="umbu-planner")
    conversation = client.conversations.create()

    print("Planner is working (gpt-5 can take a minute)...")
    response = client.responses.create(conversation=conversation.id, input=brief)

    run_dir = RUNS_DIR / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    (run_dir / "planner_raw.txt").write_text(response.output_text, encoding="utf-8")

    plan = parse_json(response.output_text)

    if plan.get("status") == "needs_input":
        record = {"campaign_id": run_dir.name, "brief": brief, "status": "needs_input",
                  "questions": plan.get("questions", [])}
        (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print("\nThe Planner stopped: the brief needs a decision before anything is created.\n")
        for i, q in enumerate(record["questions"], 1):
            print(f"{i}. {q.get('conflict')}")
            quote = str(q.get("quote", "")).strip().strip('"\u201c\u201d')
            print(f"   Brief says: \"{quote}\"   (conflicts with {q.get('rule')})")
            print(f"   Question: {q.get('question')}\n")
        print(f"Saved to {run_dir / 'record.json'}. Fix the brief and run again.")
        sys.exit(2)  # non-zero, so run_all.py stops here

    # The campaign record: one shared file every later step reads and adds to.
    record = {
        "campaign_id": run_dir.name,
        "brief": brief,
        "plan": plan,
        "assets": [],
        "checks": [],
        "decisions": [],
    }
    (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(f"\nCampaign: {plan['campaign_name']}")
    print(f"Key message: {plan['key_message']}\n")
    for asset in plan["assets"]:
        print(f"- {asset['asset_id']} ({asset['channel']}): {asset['angle']}")
        print(f"  proof points: {', '.join(asset['proof_points'])}")
    print(f"\nSaved to {run_dir / 'record.json'}")


if __name__ == "__main__":
    main()
