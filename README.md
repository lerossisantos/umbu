# Umbu

**Content rooted in your context.** Umbu is a context and governance layer for generative marketing. Agents plan a campaign, write the copy and generate the images. Then every output, whether an AI or a person wrote it, is checked against the brand's voice, approved claims, channel specs and regulations before anyone approves it.

Built as the capstone for Maven's AI PM certification by Leticia Rossi. It is a working proof of concept, not a product.

> **Demo brand:** Northwind is a fictional outdoor-gear company. All product facts and test results are invented for the demo.

## What it does

```
campaign brief
   → Planner agent              messages, placements, brief mandatories (asks when the brief is unclear)
   → Copywriter + Art Director  copy per placement, image prompt, generated image, alt text
   → Guardrail panel            code checks: channel specs, accessibility, CAN-SPAM footer, AI disclosure, brief price
                                AI checks: claims & regulatory, brand voice (each cites a rule ID)
   → Routing                    block = must fix · warning = person reviews · clean = auto-pass
   → Review                     accept AI fixes or edit (every edit is re-checked), approve, reject
   → Owner inbox                warning overrides go to the rule's owner, who labels what happened
```

- **Blocks can't be approved.** Fix it, and the fix is re-checked.
- **Approving over a warning needs a written reason.** That reason goes to the rule's owner.
- **If a checker fails, the content goes to a person** (SYS-01), never auto-pass.
- **Provenance** (AI-generated / human-edited, and by whom) is kept for copy and images.
- **The review UI is a proof of concept.** In production these actions would live in the tools teams already use (Workfront, Jira, DAM approval flows).

## Repository map

| Path | What it is |
|---|---|
| `context/` | The brand's "roots": brand voice (BV), approved claims (CL, AM), prohibited claims (CL-P), regulations (REG), channel specs (CH, ACC), brief mandatories (BR), rule owners |
| `prompts/` | Instructions for the six Foundry agents (Planner, Copywriter, Art Director, claims, brand voice and brief checkers) |
| `setup_agents.py` | Registers the agents in Microsoft Foundry (a new version only when instructions change) |
| `run_planner.py` → `run_creative.py` → `run_checks.py` | The pipeline, one step each. `run_all.py` runs them in order |
| `scenarios/vp_edits.json` | Demo scenario: the VP of Sales edits the copy after the agents finish |
| `umbu/` | Shared code: Foundry client, guardrail panel, code checks, brief checks, governance, UI helpers |
| `app.py`, `views/` | Streamlit app: Home, Review, Owner inbox |
| `eval/`, `run_eval.py`, `log_eval_to_foundry.py` | The guardrail-panel evaluation (see below) |
| `runs/` | Pipeline outputs (not committed) |

## How to run

**You need:** Python 3.11+, the Azure CLI, and a Microsoft Foundry project with these model deployments: a reasoning model (Planner, claims checker), a smaller text model (Copywriter, Art Director, brand-voice and brief checkers) and an image model. The demo used `gpt-5`, `gpt-5-mini` and `gpt-image-2`.

```bash
git clone https://github.com/lerossisantos/umbu.git
cd umbu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
az login
```

Create a `.env` file in the project folder:

```
FOUNDRY_PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
PLANNER_DEPLOYMENT=gpt-5
TEXT_DEPLOYMENT=gpt-5-mini
IMAGE_DEPLOYMENT=gpt-image-2
```

Then:

```bash
python setup_agents.py                      # once, and again after you change a file in prompts/ or context/
python run_all.py --scenario vp_edits       # brief → plan → copy + images → checks, plus the VP-edits copy
streamlit run app.py                        # open the app at http://localhost:8501
```

## Evaluation

**Question:** does the guardrail panel catch the violations it should, without blocking clean content?

- **Dataset:** `eval/dataset.jsonl`, 35 seeded cases built from the context files: 9 clean, 22 single violations (at least one per rule family: CL, AM, BR, BV, REG, CH, ACC), the 2 VP-edits assets and 2 that should only warn. It is a **seeded, synthetic answer key** written by the same person who wrote the rules. It is not a held-out set.
- **Evaluators** (`eval/scoring.py`, code-based): verdict accuracy, block recall, false-block rate on clean copy, rule-ID match, and consistency across 3 runs.
- **Platform:** results are logged to the Foundry project's Evaluations view with Foundry's evaluation API. Its string-check graders re-grade every row against the answer key.

```bash
python run_eval.py --runs 1 --limit 3       # smoke test
python run_eval.py                          # 35 cases x 3 runs → eval/results/<time>/results.md
python log_eval_to_foundry.py --safety      # log to Foundry (+ optional built-in safety evaluator)
```

**Results (Oct 9, 2026 · 35 cases x 3 runs · `eval/results/20261009-145405/`):**

| Metric | Result | Target |
|---|---|---|
| Block recall (violations caught) | 99% (71/72) | ≥ 95% |
| False blocks on clean copy | 4% (1/27) | ≤ 10% |
| Verdict accuracy (pass / warn / block) | 90% (94/105) | ≥ 80% |
| Cited the expected rule | 99% (77/78) | ≥ 90% |
| Code-checked rules (specs, accessibility, CAN-SPAM, AI disclosure, price) | 100% (21/21) | 100% |
| Same block / no-block decision across 3 runs | 94% (33/35 cases) | ≥ 95% |
| Same exact verdict across 3 runs | 77% (27/35 cases) | ≥ 90% |

The one missed block ("Built for weekend warriors") and the one false block (a display ad flagged once for the breathability qualifier) were both model-judgment calls that changed between runs. One checker call failed and was sent to a person (SYS-01), as designed. Most verdict changes are clean copy moving between *pass* and a mild brand-voice *warning*, which is why warnings go to a person instead of auto-passing.

**Next:** a held-out set written by someone other than the rule author, a larger set (40+ briefs), and per-metric thresholds as the quality gate before each new stage opens.

## Data sources

The rules are simplified from real, citable sources: GOV.UK style guide (OGL v3), USWDS and 18F (CC0), Google Ads specs, Can I Email (MIT), WCAG 2.2, FTC Endorsement and Green Guides, CAN-SPAM and EU AI Act Art. 50. **Not legal advice.**

## License

See `LICENSE`.
