"""Eval step 2: put the eval results in the Umbu Foundry project (Evaluations view).

Uses Foundry's evaluation API (OpenAI-compatible evals, through azure-ai-projects 2.x).
The panel's outputs from run_eval.py are the data; Foundry's string-check graders
re-grade every row against the answer key, so the pass rate in the portal is the metric:

  1. Umbu guardrails · verdict accuracy     all rows: actual verdict == expected verdict
  2. Umbu guardrails · block recall          rows that should block: did they block, right rule?
  3. Umbu guardrails · clean copy            clean rows: not blocked

Optional (--safety): Foundry's built-in violence evaluator on the clean copy, to show the
platform's own evaluators running next to ours.

  python log_eval_to_foundry.py                     uses the latest folder in eval/results/
  python log_eval_to_foundry.py --safety            also runs the built-in safety evaluator
"""
import argparse
import json
import os
import time
from pathlib import Path

from umbu.foundry import get_project

RESULTS = Path(__file__).parent / "eval" / "results"
FIELDS = ["case_id", "run", "placement", "note", "expected_verdict", "actual_verdict",
          "expected_rules", "actual_rules", "rule_match", "copy"]


def item(row):
    """Foundry graders read strings, so every field is flattened to text."""
    return {"case_id": row["case_id"], "run": str(row["run"]), "placement": row["placement"], "note": row["note"],
            "expected_verdict": row["expected_verdict"], "actual_verdict": row["actual_verdict"],
            "expected_rules": ", ".join(row["expected_rules"]) or "none",
            "actual_rules": ", ".join(row["actual_rules"]) or "none",
            "rule_match": row["rule_match"], "copy": json.dumps(row["copy"], ensure_ascii=False)}


def string_check(name, field, reference, operation="eq"):
    return {"type": "string_check", "name": name, "input": "{{item." + field + "}}",
            "reference": reference, "operation": operation}


def run_eval(client, name, rows, criteria, fields=FIELDS, make_item=item):
    eval_obj = client.evals.create(
        name=name,
        data_source_config={"type": "custom", "include_sample_schema": False,
                            "item_schema": {"type": "object", "properties": {f: {"type": "string"} for f in fields},
                                            "required": fields}},
        testing_criteria=criteria,
    )
    run = client.evals.runs.create(
        eval_id=eval_obj.id, name=name,
        data_source={"type": "jsonl", "source": {"type": "file_content",
                                                 "content": [{"item": make_item(r)} for r in rows]}},
    )
    print(f"  started: {name} ({len(rows)} rows)")
    while run.status not in ("completed", "failed", "canceled"):
        time.sleep(5)
        run = client.evals.runs.retrieve(run_id=run.id, eval_id=eval_obj.id)
    counts = getattr(run, "result_counts", None)
    print(f"  {run.status}: {name} · {counts}")
    print(f"  view in Foundry: {getattr(run, 'report_url', None)}\n")
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", help="a folder in eval/results/ (default: the latest)")
    parser.add_argument("--safety", action="store_true", help="also run Foundry's built-in violence evaluator")
    args = parser.parse_args()

    folder = Path(args.results) if args.results else sorted(p for p in RESULTS.iterdir() if p.is_dir())[-1]
    rows = [json.loads(line) for line in (folder / "outputs.jsonl").read_text(encoding="utf-8").splitlines() if line]
    print(f"Logging {len(rows)} rows from {folder} to Foundry\n")
    client = get_project().get_openai_client()

    run_eval(client, "Umbu guardrails · verdict accuracy", rows,
             [string_check("verdict_matches_answer_key", "actual_verdict", "{{item.expected_verdict}}")])
    run_eval(client, "Umbu guardrails · block recall", [r for r in rows if r["expected_verdict"] == "block"],
             [string_check("blocked", "actual_verdict", "block"),
              string_check("cited_expected_rule", "rule_match", "yes")])
    run_eval(client, "Umbu guardrails · clean copy not blocked", [r for r in rows if r["kind"] == "clean"],
             [string_check("not_blocked", "actual_verdict", "block", operation="ne")])

    if args.safety:
        try:
            clean = [r for r in rows if r["kind"] == "clean" and r["run"] == 1]
            run_eval(client, "Umbu copy · built-in violence check", clean,
                     [{"type": "azure_ai_evaluator", "name": "violence", "evaluator_name": "builtin.violence",
                       "data_mapping": {"query": "{{item.query}}", "response": "{{item.response}}"},
                       "initialization_parameters": {"deployment_name": os.environ.get("TEXT_DEPLOYMENT", "gpt-5-mini")}}],
                     fields=["query", "response"],
                     make_item=lambda r: {"query": f"Write {r['placement']} copy for the Cascade Shell launch",
                                          "response": json.dumps(r["copy"], ensure_ascii=False)})
        except Exception as error:  # optional extra; never blocks the main eval
            print(f"  built-in safety evaluator skipped: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
