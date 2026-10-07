"""Guardrail owner inbox: where rule owners act on warning overrides.
Overrides are grouped by rule, because a rule that keeps getting overridden
is the signal that the rule (or the brand canon) needs to change."""
import datetime
import html

import streamlit as st

from umbu.governance import (CHANGE_REQUESTED, KEPT_LIVE, KEPT_TAKEDOWN, OPEN, STATUS_LABEL,
                             all_owners, load_overrides, save_overrides)

st.set_page_config(page_title="Guardrail owner inbox", page_icon="🌳", layout="wide")

st.sidebar.title("🌳 Umbu")
owner = st.sidebar.selectbox("Viewing as guardrail owner", all_owners(), index=all_owners().index("Brand team"))
st.sidebar.caption("Proof of concept. In production, these items would land in the owner's existing "
                   "tools (e.g. a Jira or Workfront queue), not a separate app.")

st.title("Guardrail owner inbox")
st.caption("When a reviewer approves content over a warning, the override is routed here, to the owner of "
           "that rule. Step 1: change the guardrail or keep it. Step 2 (if kept): can the content stay live?")

items = load_overrides()
mine = [i for i in items if i["owner"] == owner]
open_items = [i for i in mine if i["status"] == OPEN]

c = st.columns(3)
c[0].metric("Open overrides", len(open_items))
c[1].metric("Rules affected", len({i["rule_id"] for i in open_items}))
c[2].metric("Resolved", len(mine) - len(open_items))

if not open_items:
    st.success(f"No open overrides for {owner}.")

rules = {}
for i in open_items:
    rules.setdefault(i["rule_id"], []).append(i)

for rule_id, group in sorted(rules.items(), key=lambda kv: -len(kv[1])):
    all_for_rule = [i for i in items if i["rule_id"] == rule_id]
    with st.container(border=True):
        st.markdown(f"### `{rule_id}` · {len(group)} open override(s) "
                    f"<span style='color:#888;font-size:0.7em'>· {len(all_for_rule)} all-time</span>",
                    unsafe_allow_html=True)
        st.caption(f"Rule lives in: {group[0]['rule_file']}")

        for i in group:
            st.markdown(
                f"<div style='border-left:4px solid #b54708;padding:4px 10px;margin:8px 0'>"
                f"<b>{i['asset_id']}</b> · {i['channel']} · {html.escape(i['field'])} "
                f"<span style='color:#888'>· run {i['run_id']}</span><br>"
                f"Checker said: {html.escape(i['issue'])}<br>"
                f"<i>“{html.escape(i['quote'])}”</i><br>"
                f"<b>Reviewer ({html.escape(i['reviewer'])}) approved anyway:</b> {html.escape(i['reviewer_note'])}"
                f"</div>", unsafe_allow_html=True)

            key = i["id"]
            step1 = st.radio("Step 1 · The guardrail", ["Keep the guardrail as is", "Change the guardrail"],
                             key=f"s1-{key}", horizontal=True)
            step2 = None
            if step1 == "Keep the guardrail as is":
                step2 = st.radio("Step 2 · The live content",
                                 ["Content can stay live", "Ask content owner to take it down"],
                                 key=f"s2-{key}", horizontal=True)
            else:
                st.info(f"Edit {i['rule_file']}, then run `python setup_agents.py`. "
                        "Foundry creates a new agent version, so the change is traceable.")
            owner_note = st.text_input("Owner note", key=f"n-{key}")
            if st.button("Save owner decision", key=f"b-{key}"):
                if step1 == "Change the guardrail":
                    i["status"] = CHANGE_REQUESTED
                elif step2 == "Content can stay live":
                    i["status"] = KEPT_LIVE
                else:
                    i["status"] = KEPT_TAKEDOWN
                i["owner_decision"] = {"by": owner, "note": owner_note,
                                       "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}
                save_overrides(items)
                st.rerun()
            st.markdown("---")

st.subheader("History")
resolved = [i for i in mine if i["status"] != OPEN]
if resolved:
    st.dataframe([{"rule": i["rule_id"], "asset": i["asset_id"], "run": i["run_id"],
                   "outcome": STATUS_LABEL[i["status"]], "reviewer note": i["reviewer_note"],
                   "owner note": i["owner_decision"]["note"], "decided": i["owner_decision"]["timestamp"]}
                  for i in resolved], width="stretch", hide_index=True)
else:
    st.write("Nothing resolved yet.")
