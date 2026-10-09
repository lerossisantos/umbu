# Guardrail panel eval: 3 seeded cases x 1 runs

Seeded, synthetic answer key written from Northwind's context files (not a held-out set).

| Metric | Result | Target | Met |
|---|---|---|---|
| Block recall (violations caught) | — | ≥ 95% | — |
| False blocks on clean copy | 0% | ≤ 10% | yes |
| Verdict accuracy (pass / warn / block) | 33% | ≥ 80% | no |
| Cited the right rule | — | ≥ 90% | — |
| Same verdict across runs | — | ≥ 90% | — |
| Clean copy auto-passed (no findings at all) | 33% | tracked | — |

Recall by rule family: {}

Missed blocks: none · False blocks: none · Inconsistent cases: none · Checker failures (SYS-01): 0
