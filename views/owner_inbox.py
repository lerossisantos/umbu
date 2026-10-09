"""Guardrail owner inbox (mockup screen 5): where rule owners act on warning overrides.
Overrides are grouped by rule, because a rule that keeps getting overridden is the
signal that the rule (or the content standards) may need to change. Each decision
carries one learning label, so human decisions stay usable as a learning signal."""
import datetime

import streamlit as st

from umbu.governance import (CHANGE_REQUESTED, KEPT_LIVE, KEPT_TAKEDOWN, OPEN, OUTCOMES, STANDARDS_UPDATE,
                             STATUS_LABEL, all_owners, load_overrides, save_overrides)
from umbu.review_logic import CHANNEL_LABEL
from umbu.rules import rule_text
from umbu.ui import SLATE, chip, esc, html, page_header, rule_code
from umbu.ui import CHECKER_LABEL, AI_JUDGMENT

items = load_overrides()
owners = all_owners()

head_l, head_r = st.columns([3, 1.3])
with head_r:
    owner = st.selectbox("Viewing as", owners, index=owners.index("Brand team") if "Brand team" in owners else 0)
with head_l:
    page_header("Home / Owner inbox", "Guardrail owner inbox")

mine = [i for i in items if i["owner"] == owner]
open_items = [i for i in mine if i["status"] == OPEN]
owned_rules = {"Brand team": "BV-01 to BV-10, AM-01, AM-02", "Legal & Compliance": "CL-01 to CL-10, CL-P01 to CL-P08, REG-01 to REG-09",
               "Channel Ops": "CH-RSA, CH-RDA, CH-EM, CH-MIN", "Accessibility lead": "ACC-01 to ACC-04",
               "Campaign owner": "BR-01, BR-02"}.get(owner, "")


def tile(label, value, sub=""):
    sub = f"<div style='font-size:13px;color:{SLATE}'>{esc(sub)}</div>" if sub else ""
    return (f"<div style='background:#FFFFFF;border:1px solid #DDE3E0;border-radius:12px;padding:18px 20px'>"
            f"<div style='font-size:14px;color:{SLATE}'>{esc(label)}</div>"
            f"<div style='font-size:30px;font-weight:700;margin-top:4px'>{value}</div>{sub}</div>")


html("<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:24px'>"
     + tile("Open overrides", len(open_items)) + tile("Rules affected", len({i['rule_id'] for i in open_items}))
     + tile("Resolved", len(mine) - len(open_items), owned_rules and f"Rules you own: {owned_rules}") + "</div>")

if not open_items:
    html(f"<div style='background:#E6F4EC;border-radius:10px;padding:14px 16px;color:#0B6B3A;font-weight:600'>"
         f"No open overrides for {esc(owner)}.</div>")

rules = {}
for i in open_items:
    rules.setdefault(i["rule_id"], []).append(i)

for rule_id, group in sorted(rules.items(), key=lambda kv: -len(kv[1])):
    all_for_rule = [i for i in items if i["rule_id"] == rule_id]
    text = rule_text(rule_id)
    checker = " + ".join(CHECKER_LABEL.get(c, c) for c in group[0].get("checkers", []))
    method = "AI judgment" if any(c in AI_JUDGMENT for c in group[0].get("checkers", [])) else "rule-based"
    with st.container(key=f"card-rule-{rule_id}"):
        html(f"<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap'>"
             f"{rule_code(rule_id)}<h2 style='margin:0;font-size:20px'>{esc(text.split('.')[0] or rule_id)}</h2>"
             f"{chip(f'{len(group)} open override' + ('s' if len(group) != 1 else ''), 'warn')}"
             f"<span style='margin-left:auto;font-size:14px;color:{SLATE}'>All-time overrides: {len(all_for_rule)}</span></div>"
             f"<p style='margin:8px 0 14px;font-size:15px;color:#3D4843'>Rule: “{esc(text)}” · Lives in "
             f"<span class='rc'>{esc(group[0]['rule_file'])}</span> · Checked by {esc(checker)} ({method})</p>")

        for i in group:
            key = i["id"]
            when = i["approved_at"].replace("T", " ")[:16]
            html(f"<div style='background:#F5F7F6;border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px'>"
                 f"<div style='font-size:13px;color:{SLATE}'>{esc(CHANNEL_LABEL.get(i['channel'], i['channel']))} "
                 f"<span class='rc'>{esc(i['asset_id'])}</span> · {esc(i['field'])} · run {esc(i['run_id'])} · approved {esc(when)}</div>"
                 f"<div style='font-size:15px'><b>Checker said:</b> “{esc(i['quote'])}” {esc(i['issue'])}</div>"
                 f"<div style='font-size:15px'><b>{esc(i['reviewer'])} approved anyway:</b> “{esc(i['reviewer_note'])}”</div></div>")

            html("<div style='font-size:15px;font-weight:700;margin:16px 0 6px'>Step 1 · What happened with the guardrail?</div>")
            names = [o["name"] for o in OUTCOMES]
            pick = st.radio("Step 1", names, key=f"s1-{key}", label_visibility="collapsed",
                            captions=[f"{o['desc']}  \n:violet[Learning label: {o['label']}]" for o in OUTCOMES])
            outcome = next(o for o in OUTCOMES if o["name"] == pick)
            if outcome["key"] == "rule_change":
                html(f"<div style='background:#EEE9F7;border-radius:10px;padding:12px 14px;font-size:14px;color:#2E1B55'>"
                     f"<b>Rule change:</b> opens a draft of {rule_code(rule_id, text)} v2 in "
                     f"<span class='rc'>{esc(i['rule_file'])}</span>. Publishing re-registers the agents, creating "
                     f"new versions. Past findings stay correct under v1; only examples judged under v2 are used for learning.</div>")

            step2 = None
            if outcome["step2"]:
                html("<div style='font-size:15px;font-weight:700;margin:14px 0 6px'>Step 2 · The content</div>")
                step2 = st.radio("Step 2", ["Content can stay as is",
                                            "Ask the content owner to adjust it (or take it down if live)"],
                                 key=f"s2-{key}", label_visibility="collapsed", horizontal=True)

            owner_note = st.text_input("Note to the reviewer", key=f"n-{key}")
            if st.button("Save decision", key=f"b-{key}", type="primary"):
                if outcome["key"] == "rule_change":
                    i["status"] = CHANGE_REQUESTED
                elif step2 and step2.startswith("Ask"):
                    i["status"] = KEPT_TAKEDOWN
                elif outcome["key"] == "outdated_standards":
                    i["status"] = STANDARDS_UPDATE
                else:
                    i["status"] = KEPT_LIVE
                i["owner_decision"] = {"by": owner, "note": owner_note, "outcome": outcome["key"],
                                       "learning_label": outcome["label"].split(" · ")[0],
                                       "content": step2,
                                       "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}
                save_overrides(items)
                st.rerun()

html("<h2 style='font-size:18px;margin:28px 0 10px'>History</h2>")
resolved = [i for i in mine if i["status"] != OPEN]
if resolved:
    st.dataframe([{"rule": i["rule_id"], "asset": i["asset_id"], "run": i["run_id"],
                   "outcome": STATUS_LABEL.get(i["status"], i["status"]),
                   "learning label": (i.get("owner_decision") or {}).get("learning_label", "—"),
                   "reviewer note": i["reviewer_note"], "owner note": (i.get("owner_decision") or {}).get("note", ""),
                   "decided": (i.get("owner_decision") or {}).get("timestamp", "")}
                  for i in resolved], width="stretch", hide_index=True)
else:
    html(f"<div style='background:#FFFFFF;border:1px dashed #C9D4D0;border-radius:12px;padding:20px;color:{SLATE}'>"
         "Resolved overrides appear here with the owner's decision, so reviewers can see what happened to their feedback.</div>")
html(f"<p style='margin-top:18px;font-size:13px;color:{SLATE}'>Proof of concept. In production these items would land "
     "in the owner's existing tools (e.g. a Jira or Workfront queue).</p>")
