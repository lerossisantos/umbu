# Guardrail panel eval: 35 seeded cases x 3 runs

Seeded, synthetic answer key written from Northwind's context files (not a held-out set).

| Metric | Result | Target | Met |
|---|---|---|---|
| Block recall (violations caught) | 99% | ≥ 95% | yes |
| False blocks on clean copy | 4% | ≤ 10% | yes |
| Verdict accuracy (pass / warn / block) | 90% | ≥ 80% | yes |
| Cited the right rule | 99% | ≥ 90% | yes |
| Same verdict across runs | 77% | ≥ 90% | no |
| Clean copy auto-passed (no findings at all) | 63% | tracked | — |

Recall by rule family: {'ACC': '6/6', 'AM': '3/3', 'BR': '3/3', 'BV': '11/12', 'CH': '6/6', 'CL': '30/30', 'REG': '6/6', 'VP': '6/6'}

Missed blocks: ['V15'] · False blocks: ['C02'] · Inconsistent cases: ['C01', 'C02', 'C05', 'C06', 'C07', 'C08', 'C09', 'V15'] · Checker failures (SYS-01): 1
