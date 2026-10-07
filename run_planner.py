"""Step 1 of the pipeline: send the campaign brief to the Planner agent
and start a new campaign record in runs/<timestamp>/record.json."""
import datetime
import json

from umbu.context import CONTEXT_DIR, RUNS_DIR
from umbu.foundry import get_project
from umbu.jsonutil import parse_json


def main():
    brief = (CONTEXT_DIR / "campaign_brief.md").read_text(encoding="utf-8")

    project = get_project()
    client = project.get_openai_client(agent_name="umbu-planner")
    conversation = client.conversations.create()

    print("Planner is working (gpt-5 can take a minute)...")
    response = client.responses.create(conversation=conversation.id, input=brief)

    run_dir = RUNS_DIR / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True)
    (run_dir / "planner_raw.txt").write_text(response.output_text, encoding="utf-8")

    plan = parse_json(response.output_text)

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
