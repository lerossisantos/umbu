"""Eval step 1: run the guardrail panel over the seeded dataset, several times.

Question: does Umbu catch the violations it should, without blocking clean content?
Each case goes through the same panel the product uses (code checks + the claims and
brand-voice agents in Foundry). Running it 3 times puts a number on the run-to-run
variation of the model checkers.

  python run_eval.py --runs 1 --limit 3     quick smoke test (3 cases, ~1 min)
  python run_eval.py                        full eval: 35 cases x 3 runs (~10-15 min)

Writes eval/results/<timestamp>/: outputs.jsonl (every case and run), summary.json,
results.md (the table for the deck).
"""
import argparse
import datetime
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from umbu.foundry import get_project
from umbu.panel import run_panel
from eval.scoring import results_table, rule_ids, rule_match, score, verdict_of

ROOT = Path(__file__).parent
EVAL = ROOT / "eval"
FIXTURES = EVAL / "fixtures"  # the two images the display ad and email cases point to

_local = threading.local()


def project():
    if not hasattr(_local, "project"):
        _local.project = get_project()
    return _local.project


def run_case(case, run):
    started = time.time()
    findings = run_panel(project(), case["asset"], FIXTURES)
    actual_rules = rule_ids(findings)
    return {
        "case_id": case["case_id"], "run": run, "kind": case["kind"], "rule_family": case["rule_family"],
        "placement": case["placement"], "note": case["note"],
        "expected_verdict": case["expected_verdict"], "expected_rules": case["expected_rules"],
        "actual_verdict": verdict_of(findings), "actual_rules": actual_rules,
        "rule_match": rule_match(case["expected_rules"], actual_rules),
        "seconds": round(time.time() - started, 1),
        "copy": case["asset"]["copy"], "alt_text": case["asset"].get("image", {}).get("alt_text"),
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--limit", type=int, help="only the first N cases (smoke test)")
    parser.add_argument("--workers", type=int, default=6, help="cases checked in parallel")
    args = parser.parse_args()

    cases = [json.loads(line) for line in (EVAL / "dataset.jsonl").read_text(encoding="utf-8").splitlines() if line]
    cases = cases[: args.limit] if args.limit else cases
    out_dir = EVAL / "results" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    print(f"{len(cases)} cases x {args.runs} runs = {len(cases) * args.runs} panel checks. Results: {out_dir}\n")

    rows = []
    jobs = [(c, r) for r in range(1, args.runs + 1) for c in cases]
    with ThreadPoolExecutor(max_workers=args.workers) as pool, (out_dir / "outputs.jsonl").open("w", encoding="utf-8") as fh:
        futures = {pool.submit(run_case, c, r): (c, r) for c, r in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            ok = "ok  " if row["actual_verdict"] == row["expected_verdict"] else "MISS"
            print(f"[{i:>3}/{len(jobs)}] {ok} run {row['run']} {row['case_id']:<4} expected {row['expected_verdict']:<5} "
                  f"got {row['actual_verdict']:<5} {', '.join(row['actual_rules'])[:70]}")

    metrics = score(rows)
    (out_dir / "summary.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    table = results_table(metrics)
    (out_dir / "results.md").write_text(
        f"# Guardrail panel eval: {metrics['cases']} seeded cases x {metrics['runs']} runs\n\n"
        "Seeded, synthetic answer key written from Northwind's context files (not a held-out set).\n\n"
        f"{table}\n\nRecall by rule family: {metrics['recall_by_family']}\n\n"
        f"Missed blocks: {metrics['missed_blocks'] or 'none'} · False blocks: {metrics['false_blocks'] or 'none'} · "
        f"Inconsistent cases: {metrics['inconsistent_cases'] or 'none'} · Checker failures (SYS-01): "
        f"{metrics['checker_failures']}\n", encoding="utf-8")
    print("\n" + table)
    print(f"\nMissed blocks: {metrics['missed_blocks'] or 'none'}")
    print(f"False blocks on clean copy: {metrics['false_blocks'] or 'none'}")
    print(f"Cases whose verdict changed between runs: {metrics['inconsistent_cases'] or 'none'}")
    print(f"Checker failures (SYS-01, sent to a person): {metrics['checker_failures']}")
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
