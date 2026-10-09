"""Code-based evaluators for the guardrail-panel eval. They compare what the panel
returned with the seeded answer key in eval/dataset.jsonl. No model involved."""
from collections import Counter, defaultdict

# Targets we hold ourselves to before launch (proposed, not yet negotiated with
# Legal or Brand). Missed blocks are the worst failure, so recall has the highest bar.
TARGETS = {
    "block_recall": ("≥ 95%", 0.95, "higher"),
    "false_block_rate": ("≤ 10%", 0.10, "lower"),
    "verdict_accuracy": ("≥ 80%", 0.80, "higher"),
    "rule_id_match": ("≥ 90%", 0.90, "higher"),
    "consistency": ("≥ 90%", 0.90, "higher"),
}


def verdict_of(findings):
    """Same routing as the product: any block = block, any other finding = warn, none = pass."""
    if any(f.get("severity") == "block" for f in findings):
        return "block"
    return "warn" if findings else "pass"


def rule_ids(findings):
    return sorted({f.get("rule_id", "") for f in findings if f.get("rule_id")})


def rule_match(expected_rules, actual_rules):
    """'yes' if the panel cited at least one of the rules the answer key lists for this
    violation (several rules can legitimately cover the same problem, e.g. CL-P01 and REG-01)."""
    if not expected_rules:
        return "n/a"
    return "yes" if set(expected_rules) & set(actual_rules) else "no"


def score(rows):
    """rows: one per (case, run) with expected_verdict, actual_verdict, kind, expected_rules,
    actual_rules, case_id, run. Returns the metrics dict."""
    def share(hits, total):
        return (hits / total) if total else None

    blocks = [r for r in rows if r["expected_verdict"] == "block"]
    clean = [r for r in rows if r["kind"] == "clean"]
    with_rules = [r for r in rows if r["expected_rules"]]
    by_case = defaultdict(list)
    for r in rows:
        by_case[r["case_id"]].append(r["actual_verdict"])
    multi = {c: v for c, v in by_case.items() if len(v) > 1}

    by_family = defaultdict(lambda: [0, 0])
    for r in blocks:
        by_family[r["rule_family"]][1] += 1
        by_family[r["rule_family"]][0] += r["actual_verdict"] == "block"

    return {
        "cases": len(by_case),
        "runs": max((r["run"] for r in rows), default=0),
        "rows": len(rows),
        "verdict_accuracy": share(sum(r["actual_verdict"] == r["expected_verdict"] for r in rows), len(rows)),
        "block_recall": share(sum(r["actual_verdict"] == "block" for r in blocks), len(blocks)),
        "false_block_rate": share(sum(r["actual_verdict"] == "block" for r in clean), len(clean)),
        "clean_auto_pass_rate": share(sum(r["actual_verdict"] == "pass" for r in clean), len(clean)),
        "rule_id_match": share(sum(rule_match(r["expected_rules"], r["actual_rules"]) == "yes" for r in with_rules),
                               len(with_rules)),
        "consistency": share(sum(len(set(v)) == 1 for v in multi.values()), len(multi)),
        "checker_failures": sum("SYS-01" in r["actual_rules"] for r in rows),
        "recall_by_family": {k: f"{h}/{n}" for k, (h, n) in sorted(by_family.items())},
        "missed_blocks": sorted({r["case_id"] for r in blocks if r["actual_verdict"] != "block"}),
        "false_blocks": sorted({r["case_id"] for r in clean if r["actual_verdict"] == "block"}),
        "inconsistent_cases": sorted(c for c, v in multi.items() if len(set(v)) > 1),
        "confusion": dict(Counter(f"{r['expected_verdict']}→{r['actual_verdict']}" for r in rows)),
    }


def pct(x):
    return "—" if x is None else f"{x * 100:.0f}%"


def results_table(m):
    """Markdown table for the deck: metric, result, target, met?"""
    lines = ["| Metric | Result | Target | Met |", "|---|---|---|---|"]
    names = {"block_recall": "Block recall (violations caught)",
             "false_block_rate": "False blocks on clean copy",
             "verdict_accuracy": "Verdict accuracy (pass / warn / block)",
             "rule_id_match": "Cited the right rule",
             "consistency": "Same verdict across runs"}
    for key, label in names.items():
        val = m[key]
        text, bar, direction = TARGETS[key]
        met = "—" if val is None else ("yes" if (val >= bar if direction == "higher" else val <= bar) else "no")
        lines.append(f"| {label} | {pct(val)} | {text} | {met} |")
    lines.append(f"| Clean copy auto-passed (no findings at all) | {pct(m['clean_auto_pass_rate'])} | tracked | — |")
    return "\n".join(lines)
