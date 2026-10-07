"""The guardrail panel: code checks + model checkers + routing.
Used by run_checks.py (batch) and app.py (re-checking a reviewer's edits)."""
import json

from umbu.jsonutil import parse_json
from umbu.spec_checks import check_asset

MODEL_CHECKERS = {
    "claims": "umbu-claims-checker",
    "brand_voice": "umbu-brand-voice-checker",
}


def ask_checker(project, agent_name, asset):
    payload = {"asset_id": asset["asset_id"], "channel": asset["channel"], "copy": asset["copy"],
               "claims_used": asset.get("claims_used", []),
               "alt_text": asset.get("image", {}).get("alt_text")}
    client = project.get_openai_client(agent_name=agent_name)
    conversation = client.conversations.create()
    response = client.responses.create(conversation=conversation.id, input=json.dumps(payload, indent=2))
    return parse_json(response.output_text).get("findings", [])


def run_panel(project, asset, run_dir):
    findings = check_asset(asset, run_dir)
    for checker, agent in MODEL_CHECKERS.items():
        for f in ask_checker(project, agent, asset):
            f["checker"] = checker
            findings.append(f)
    return findings


def route(findings):
    """Routing policy: anything flagged goes to a person. Blocks must be fixed first."""
    if not findings:
        return "auto_pass", None
    if any(f["severity"] == "block" for f in findings):
        return "review_queue", "must_fix"
    return "review_queue", "review"
