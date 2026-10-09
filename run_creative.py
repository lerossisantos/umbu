"""Step 2 of the pipeline: for each asset in the latest plan, the Copywriter writes
the copy and the Art Director writes an image prompt; then we generate the image.
Results are added to the same campaign record."""
import json

from umbu.foundry import get_project
from umbu.images import generate_image, get_image_client
from umbu.jsonutil import parse_json
from umbu.record import latest_run_dir, load_record, save_record


def ask_agent(project, agent_name: str, payload: dict) -> dict:
    client = project.get_openai_client(agent_name=agent_name)
    conversation = client.conversations.create()
    response = client.responses.create(conversation=conversation.id, input=json.dumps(payload, indent=2))
    return parse_json(response.output_text)


def main():
    run_dir = latest_run_dir()
    record = load_record(run_dir)
    plan = record["plan"]
    project = get_project()
    image_client = get_image_client()

    record["assets"] = []
    for brief in plan["assets"]:
        asset_id = brief["asset_id"]
        print(f"\n[{asset_id}] Copywriter is writing...")
        copy = ask_agent(project, "umbu-copywriter", {
            "key_message": plan["key_message"],
            "messages": [m for m in plan.get("messages", []) if m.get("message_id") in brief.get("message_ids", [])],
            "asset_brief": {k: v for k, v in brief.items() if k != "image_brief"},
        })
        asset = {"asset_id": asset_id, "channel": brief["channel"], "copy": copy["copy"],
                 "claims_used": copy.get("claims_used", []), "copy_notes": copy.get("notes", ""),
                 "refused": copy.get("refused", []), "message_ids": brief.get("message_ids", [])}
        for r in asset["refused"]:
            print(f"[{asset_id}] Copywriter refused: {r}")

        if brief.get("image_brief"):
            print(f"[{asset_id}] Art Director is writing the image prompt...")
            art = ask_agent(project, "umbu-art-director", {"asset_id": asset_id, "image_brief": brief["image_brief"]})
            image_file = f"{asset_id}.png"
            print(f"[{asset_id}] Generating image (this can take ~30 seconds)...")
            generate_image(image_client, art["image_prompt"], brief["image_brief"]["size"], run_dir / image_file)
            asset["image"] = {"file": image_file, "size": brief["image_brief"]["size"],
                              "prompt": art["image_prompt"], "alt_text": art["alt_text"],
                              "ai_disclosure": art.get("ai_disclosure"), "art_notes": art.get("notes", "")}

        record["assets"].append(asset)
        save_record(run_dir, record)  # save after each asset so a failure doesn't lose earlier work
        print(f"[{asset_id}] done")

    print(f"\nAll assets written. Open {run_dir} to see the copy (record.json) and images (.png).")


if __name__ == "__main__":
    main()
