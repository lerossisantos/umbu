"""The guardrail panel: code checks + model checkers + routing.
Used by run_checks.py (batch) and app.py (re-checking a reviewer's edits)."""
import json

from umbu.jsonutil import parse_json
from umbu.brief_checks import check_asset_brief
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


def checker_failed(checker, error):
    """Fail toward a person: a checker that errors, times out or returns
    something unreadable produces a blocking finding, so the asset can never
    pass by default."""
    return {"checker": checker, "rule_id": "SYS-01", "field": f"{checker} checker",
            "issue": f"The {checker.replace('_', ' ')} checker did not return a result "
                     f"({type(error).__name__}). Sent to a person; edit or re-check to retry.",
            "severity": "block", "confidence": "high"}


def run_panel(project, asset, run_dir):
    findings = [{**f, "confidence": "certain"} for f in check_asset(asset, run_dir)]
    findings += check_asset_brief(asset)  # brief mandatories that code can check exactly
    for checker, agent in MODEL_CHECKERS.items():
        try:
            results = ask_checker(project, agent, asset)
            if not isinstance(results, list):
                raise ValueError("findings is not a list")
        except Exception as error:  # any failure goes to a person, never auto-pass
            findings.append(checker_failed(checker, error))
            continue
        for f in results:
            f["checker"] = checker
            f.setdefault("confidence", "medium")
            findings.append(f)
    return findings


def route(findings):
    """Routing policy: anything flagged goes to a person. Blocks must be fixed first."""
    if not findings:
        return "auto_pass", None
    if any(f["severity"] == "block" for f in findings):
        return "review_queue", "must_fix"
    return "review_queue", "review"
