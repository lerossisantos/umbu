"""Umbu review queue: the human step of the pipeline.
Start it with:  streamlit run app.py

PROOF OF CONCEPT: this standalone UI proves the review interaction. In production,
Umbu's findings and approve/reject actions would live inside the workflow tools
reviewers already use (e.g. Workfront, Jira, their DAM), not in a separate app.

Reviewers see each asset with its image, copy and checker findings, then approve,
request changes or reject. Every decision is saved in the campaign record:
human decisions are Umbu's learning signal."""
import datetime
import html
import json

import streamlit as st

from umbu.context import RUNS_DIR
from umbu.brief_checks import check_package, load_mandatories
from umbu.foundry import get_project
from umbu.governance import STATUS_LABEL, load_overrides, log_warning_overrides, takedowns_for_run
from umbu.panel import route, run_panel
from umbu.record import load_record, save_record

st.set_page_config(page_title="Umbu review queue", page_icon="🌳", layout="wide")

DECISIONS = ["Approve", "Request changes", "Reject"]


# ---------- helpers ----------
def list_runs():
    runs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "record.json").exists()
            and json.loads((p / "record.json").read_text(encoding="utf-8")).get("status") != "needs_input"]
    return sorted(runs, key=lambda p: p.name, reverse=True)


def run_label(path):
    record = load_record(path)
    scenario = record.get("scenario", {}).get("name")
    return f"{path.name}  ·  {scenario}" if scenario else f"{path.name}  ·  agents' own copy"


def merge_findings(findings):
    """Code and model checkers can flag the same thing. Show it once, credit both."""
    merged = {}
    for f in findings:
        key = (f["rule_id"], f.get("field", ""))
        if key in merged:
            m = merged[key]
            if f["checker"] not in m["checkers"]:
                m["checkers"].append(f["checker"])
            if f["severity"] == "block":
                m["severity"] = "block"
        else:
            merged[key] = {**f, "checkers": [f["checker"]]}
    return sorted(merged.values(), key=lambda m: m["severity"] != "block")


def effective_route(check, warn_policy):
    findings = check["findings"]
    if any(f["severity"] == "block" for f in findings):
        return "must_fix"
    if findings and warn_policy == "Send to review":
        return "review"
    return "auto_pass"


ROUTE_BADGE = {
    "must_fix": ("⛔ Must fix", "#b42318"),
    "review": ("🟡 Review", "#b54708"),
    "auto_pass": ("✅ Auto-pass", "#067647"),
}


def highlight(text, quotes):
    out = html.escape(str(text))
    for q in quotes:
        if q and html.escape(q) in out:
            out = out.replace(html.escape(q), f"<mark>{html.escape(q)}</mark>")
    return out


def render_copy(copy, quotes):
    for field, value in copy.items():
        values = value if isinstance(value, list) else [value]
        st.markdown(f"**{field}**")
        for v in values:
            st.markdown(
                f"{highlight(v, quotes)} "
                f"<span style='color:#888;font-size:0.8em'>({len(str(v))} chars)</span>",
                unsafe_allow_html=True,
            )


def render_finding(f):
    color = "#b42318" if f["severity"] == "block" else "#b54708"
    checkers = " + ".join(f["checkers"])
    quote = f"<br><i>“{html.escape(f['quote'])}”</i>" if f.get("quote") else ""
    fix = (f"<br><span style='color:#067647'>Suggested: {html.escape(f['suggested_fix'])}</span>"
           if f.get("suggested_fix") else "")
    st.markdown(
        f"<div style='border-left:4px solid {color};padding:4px 10px;margin:6px 0'>"
        f"<b style='color:{color}'>{f['severity'].upper()}</b> · <code>{f['rule_id']}</code> · "
        f"{html.escape(f.get('field', ''))} · <span style='color:#888'>{checkers}</span>"
        f"{' · confidence: ' + f['confidence'] if f.get('confidence') else ''}<br>"
        f"{html.escape(f['issue'])}{quote}{fix}</div>",
        unsafe_allow_html=True,
    )


# ---------- sidebar ----------
st.sidebar.title("🌳 Umbu")
st.sidebar.caption("Content rooted in your context")
runs = list_runs() if RUNS_DIR.exists() else []
if not runs:
    st.warning("No runs yet. Run `python run_all.py` first.")
    st.stop()
run_dir = st.sidebar.selectbox("Campaign run", runs, format_func=run_label)
reviewer = st.sidebar.text_input("Reviewer", "Leticia (Brand owner)")
warn_policy = st.sidebar.radio(
    "Routing policy for warnings",
    ["Send to review", "Auto-pass with notes"],
    help="Blocks always go to a person. This decides what happens to assets that only have warnings.",
)
st.sidebar.divider()
st.sidebar.markdown(
    "**Pipeline**  \nBrief → Planner → Copywriter + Art Director → "
    "Guardrail panel (code + claims + brand voice) → **this review queue**"
)
st.sidebar.caption(
    "Proof of concept. In production, these findings and decisions would appear "
    "inside the workflow tools reviewers already use."
)

record = load_record(run_dir)
checks = {c["asset_id"]: c for c in record.get("checks", [])}
decisions = {d["asset_id"]: d for d in record.get("decisions", [])}

# ---------- header ----------
st.title(record["plan"]["campaign_name"])
st.caption(f"Key message: {record['plan']['key_message']}")
if record.get("scenario"):
    st.info(f"**Scenario: {record['scenario']['name']}.** {record['scenario']['story']}")
if not checks:
    st.warning("This run hasn't been through the guardrail panel yet. Run `python run_checks.py`.")
    st.stop()

routes = {aid: effective_route(c, warn_policy) for aid, c in checks.items()}
takedowns = takedowns_for_run(run_dir.name)
cols = st.columns(4)
cols[0].metric("Assets", len(record["assets"]))
cols[1].metric("Auto-pass", sum(r == "auto_pass" for r in routes.values()))
cols[2].metric("Needs review", sum(r == "review" for r in routes.values()))
cols[3].metric("Must fix", sum(r == "must_fix" for r in routes.values()))

# ---------- assets ----------
for asset in record["assets"]:
    aid = asset["asset_id"]
    check = checks.get(aid, {"findings": []})
    findings = merge_findings(check["findings"])
    label, color = ROUTE_BADGE[routes.get(aid, "review")]
    done = decisions.get(aid)

    with st.container(border=True):
        head = f"### {aid} · {asset['channel']} &nbsp; <span style='color:{color}'>{label}</span>"
        if done:
            head += f" &nbsp; <span style='color:#888'>· decided: {done['decision']}</span>"
        st.markdown(head, unsafe_allow_html=True)
        for t in takedowns.get(aid, []):
            st.error(f"Takedown requested by {t['owner_decision']['by']} (rule {t['rule_id']}): "
                     f"{t['owner_decision']['note'] or 'no note'}")
        if asset.get("edited_by"):
            st.caption(f"✏️ Edited by {asset['edited_by']}: {', '.join(asset.get('edited_fields', []))}")

        left, right = st.columns([3, 2])
        with left:
            render_copy(asset["copy"], [f.get("quote") for f in findings])
        with right:
            if asset.get("image"):
                img = asset["image"]
                st.image(str(run_dir / img["file"]), width="stretch")
                st.caption(f"{img.get('ai_disclosure', '')} · Alt text: {img['alt_text']}")

        st.markdown(f"**Guardrail findings ({len(findings)})**")
        if findings:
            for f in findings:
                render_finding(f)
        else:
            st.markdown("No issues found by any checker.")

        msg = st.session_state.pop(f"msg-{aid}", None)
        if msg:
            getattr(st, msg[0])(msg[1])

        with st.form(f"decide-{run_dir.name}-{aid}"):
            choice = st.radio("Decision", DECISIONS, horizontal=True,
                              index=DECISIONS.index(done["decision"]) if done else 0)
            note = st.text_input("Why? (saved to the record)", value=done.get("note", "") if done else "")
            edits = {}
            with st.expander("Edit copy before deciding"):
                for field, value in asset["copy"].items():
                    if isinstance(value, list):
                        new = st.text_area(field, "\n".join(value), key=f"{aid}-{field}")
                        lines = [line for line in new.split("\n") if line.strip()]
                        if lines != value:
                            edits[field] = lines
                    else:
                        new = st.text_input(field, value, key=f"{aid}-{field}")
                        if new != value:
                            edits[field] = new
            if st.form_submit_button("Save decision"):
                now = datetime.datetime.now().isoformat(timespec="seconds")
                if edits:
                    # Rule 1: a reviewer's edits go back through the full guardrail panel.
                    candidate = {**asset, "copy": {**asset["copy"], **edits}}
                    with st.spinner("Re-checking your edits with the guardrail panel..."):
                        new_findings = run_panel(get_project(), candidate, run_dir)
                    asset["copy"].update(edits)
                    asset["edited_by"] = reviewer
                    asset["edited_fields"] = list(edits)
                    new_route, new_priority = route(new_findings)
                    record["checks"] = [c for c in record["checks"] if c["asset_id"] != aid] + [{
                        "asset_id": aid, "findings": new_findings, "route": new_route,
                        "priority": new_priority, "rechecked_after_edit_by": reviewer, "rechecked_at": now}]
                    findings = merge_findings(new_findings)
                    route_now = effective_route({"findings": new_findings}, warn_policy)
                else:
                    route_now = routes.get(aid)

                blocks = [f for f in findings if f["severity"] == "block"]
                warns = [f for f in findings if f["severity"] == "warn"]
                if choice == "Approve" and blocks:
                    # Rule 2: blocks can never be approved. Log the attempt.
                    record.setdefault("audit", []).append({
                        "event": "approval_refused", "asset_id": aid, "reviewer": reviewer, "timestamp": now,
                        "blocking_rules": [f["rule_id"] for f in blocks], "after_edit": bool(edits)})
                    save_record(run_dir, record)
                    st.session_state[f"msg-{aid}"] = ("error",
                        "Approval refused: " + ", ".join(f["rule_id"] for f in blocks) +
                        " still block this asset. Fix the copy, or choose Request changes / Reject.")
                    st.rerun()
                elif choice == "Approve" and warns and not note.strip():
                    # Rule 3: overriding warnings needs a written reason.
                    st.session_state[f"msg-{aid}"] = ("warning",
                        "This asset has warnings. Add a note explaining why it's OK to approve.")
                    if edits:
                        save_record(run_dir, record)
                    st.rerun()
                else:
                    decision = {
                        "asset_id": aid, "decision": choice, "note": note, "reviewer": reviewer,
                        "timestamp": now, "route_at_review": route_now,
                        "findings": [{"rule_id": f["rule_id"], "severity": f["severity"],
                                      "checkers": f["checkers"]} for f in findings],
                        "edited_fields": list(edits),
                    }
                    if choice == "Approve":
                        decision["approved_copy"] = json.loads(json.dumps(asset["copy"]))  # exact snapshot
                        if warns:
                            # Route each overridden warning to the owner of that rule.
                            log_warning_overrides(run_dir.name, asset, warns, reviewer, note, now)
                    record["decisions"] = [d for d in record.get("decisions", []) if d["asset_id"] != aid] + [decision]
                    save_record(run_dir, record)
                    st.session_state[f"msg-{aid}"] = ("success", f"Saved: {choice}.")
                    st.rerun()

# ---------- brief check (package level) ----------
st.divider()
st.subheader("Brief check")
spec = load_mandatories()
st.caption(f"Against campaign brief {spec.get('brief_version', 'v1')} · owner: Campaign owner. "
           "Runs on the approved version of each asset where there is one, because edits made "
           "during review can break the brief after creation.")
for m in spec["mandatories"]:
    st.markdown(f"`{m['id']}` {m['text']} <span style='color:#888'>· "
                f"{'rule-based' if m['method'] == 'code' else 'AI judgment'}</span>", unsafe_allow_html=True)
bc = record.get("brief_check")
if st.button("Re-run brief check on approved content"):
    with st.spinner("Checking the campaign against its brief..."):
        record["brief_check"] = check_package(get_project(), record)
    save_record(run_dir, record)
    st.rerun()
if not bc:
    st.write("Not run yet for this campaign.")
elif not bc["findings"]:
    st.success(f"All brief mandatories met (checked {bc['checked_at']}).")
else:
    st.caption(f"Checked {bc['checked_at']} · versions: " +
               ", ".join(f"{k} {v}" for k, v in bc["checked_versions"].items()))
    for f in bc["findings"]:
        render_finding({**f, "checkers": ["brief"], "field": f"{f['asset_id']} · {f['field']}"})
    st.info("Two ways to resolve a brief finding: **fix the content** (edit the asset above; the edit is "
            "re-checked against the brief too), or **amend the brief** if the brief itself changed. "
            "Brief amendments with campaign-owner approval are designed, not built yet.")

# ---------- learning signal ----------
st.divider()
st.subheader("Decision log: the learning signal")
st.caption("Each human decision is stored with the findings it was made against. "
           "Over time this shows which rules reviewers agree with and which ones they override, "
           "which is how checker thresholds get tuned.")
if record.get("decisions"):
    st.dataframe(
        [{"asset": d["asset_id"], "decision": d["decision"], "reviewer": d["reviewer"],
          "blocks": sum(f["severity"] == "block" for f in d["findings"]),
          "warnings": sum(f["severity"] == "warn" for f in d["findings"]),
          "edited": ", ".join(d["edited_fields"]) or "-", "note": d["note"], "time": d["timestamp"]}
         for d in record["decisions"]],
        width="stretch", hide_index=True,
    )
else:
    st.write("No decisions yet.")

st.subheader("Audit trail")
st.caption("Refused approval attempts. Repeated pushes against the same rule show where "
           "the brand canon or the rules may need a conversation.")
if record.get("audit"):
    st.dataframe([{"asset": a["asset_id"], "reviewer": a["reviewer"], "blocked by": ", ".join(a["blocking_rules"]),
                   "after edit": a["after_edit"], "time": a["timestamp"]} for a in record["audit"]],
                 width="stretch", hide_index=True)
else:
    st.write("No refused approvals.")

st.subheader("Warning overrides")
st.caption("Approvals made over a warning. Each one is routed to the rule's owner "
           "(see the Guardrail owner inbox page).")
run_overrides = [i for i in load_overrides() if i["run_id"] == run_dir.name]
if run_overrides:
    st.dataframe([{"asset": i["asset_id"], "rule": i["rule_id"], "owner": i["owner"],
                   "reviewer note": i["reviewer_note"], "status": STATUS_LABEL[i["status"]]}
                  for i in run_overrides], width="stretch", hide_index=True)
else:
    st.write("No warning overrides in this run.")
