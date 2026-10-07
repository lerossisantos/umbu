# Northwind context store

These files are Umbu's "roots": what the agents read before they write, and what the guardrail checkers judge against.

Northwind is a **fictional** outdoor-gear brand created for this demo. Product facts and test results below are invented for the demo and are not claims about any real company or product.

Every rule has an ID (e.g. `BV-03`, `CL-05`). Checkers must cite the rule ID when they flag something, so every decision is traceable to a line in this folder.

| File | Used by | Check type |
|---|---|---|
| `brand_voice.md` | Copywriter, brand-voice checker | Model judgment |
| `approved_claims.md` | Copywriter, claims checker | Model judgment |
| `channel_specs.md` + `.json` | Planner, Art Director, channel-spec and accessibility checkers | Deterministic code |
| `regulations.md` | Claims checker, compliance checker | Model judgment |
| `campaign_brief.md` | Planner | Input |
