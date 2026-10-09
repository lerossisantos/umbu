"""Review: the human step. Layout follows the mockup (screen 4a): a queue on the left,
riskiest first; the selected asset with its findings and actions on the right.
All rules (re-check of edits, blocks unapprovable, reasons for overrides, snapshots)
are enforced in umbu/review_logic.py."""
import streamlit as st

from umbu.brief_checks import check_package, load_mandatories
from umbu.governance import STATUS_LABEL, load_overrides, takedowns_for_run
from umbu.record import load_record, save_record
from umbu.review_logic import (CHANNEL_LABEL, ROUTE_BADGE, ROUTE_ORDER, apply_suggestions, decide,
                               effective_route, list_runs, merge_findings, recheck, run_label)
from umbu.rules import rule_text
from umbu.ui import AI_JUDGMENT, CHECKER_LABEL, SLATE, STATUS, chip, esc, html, page_header, rule_code


def project_or_none():
    """Foundry connection for re-checks. If it can't be reached, checkers fail toward a person (SYS-01)."""
    try:
        from umbu.foundry import get_project
        return get_project()
    except Exception:
        return None


def highlight(text, quotes):
    out = esc(text)
    for q in quotes:
        if q and esc(q) in out:
            out = out.replace(esc(q), f"<mark>{esc(q)}</mark>")
    return out


def render_copy(copy, quotes):
    parts = []
    for field, value in copy.items():
        values = value if isinstance(value, list) else [value]
        rows = "".join(
            f"<div style='font-size:15px;line-height:1.45;margin:3px 0'>{highlight(v, quotes)} "
            f"<span style='color:{SLATE};font-size:12px'>{len(str(v))} chars</span></div>" for v in values)
        parts.append(f"<div style='margin-bottom:12px'><div style='font-size:12px;font-weight:700;color:{SLATE};"
                     f"text-transform:none'>{esc(field.replace('_', ' '))}</div>{rows}</div>")
    html("".join(parts))


def render_finding(f):
    kind = "block" if f["severity"] == "block" else "warn"
    fg, bg = STATUS[kind]
    checkers = " + ".join(CHECKER_LABEL.get(c, c) for c in f["checkers"])
    method = ("AI judgment", "ai") if any(c in AI_JUDGMENT for c in f["checkers"]) else ("Rule-based", "neutral")
    conf = f" · confidence {esc(f['confidence'])}" if f.get("confidence") and f["confidence"] != "certain" else ""
    quote = (f"<span style='background:{bg};border-radius:4px;padding:1px 4px'>“{esc(f['quote'])}”</span> "
             if f.get("quote") else "")
    fix = (f"<div style='background:#E6F4EC;border-radius:8px;padding:8px 12px;margin-top:8px;font-size:14px'>"
           f"<b style='color:#0B6B3A'>Suggested fix</b> · {esc(f['suggested_fix'])}</div>" if f.get("suggested_fix") else "")
    border = "#F1D3CF" if kind == "block" else "#F0D9B5"
    html(f"<div style='background:#FFFFFF;border:1px solid {border};border-radius:10px;padding:12px 14px;margin:8px 0'>"
         f"<div style='display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13px'>"
         f"{chip('Blocked' if kind == 'block' else 'Warning', kind)} {rule_code(f['rule_id'], rule_text(f['rule_id']))}"
         f"<b style='color:#3D4843'>{esc(checkers)}</b>{chip(method[0], method[1])}"
         f"<span style='color:{SLATE}'>· {esc(f.get('field', ''))}{conf}</span></div>"
         f"<div style='font-size:15px;margin-top:6px;line-height:1.45'>{quote}{esc(f['issue'])}</div>{fix}</div>")


def provenance(asset):
    if asset.get("edited_by"):
        how = " (AI suggestion accepted)" if asset.get("edit_method") == "ai_suggestion" else ""
        return chip(f"AI-generated, human-edited · {asset['edited_by'].split(' (')[0]}{how}", "ai")
    return chip("AI-generated · Copywriter agent", "neutral")


def flash(key):
    msg = st.session_state.pop(key, None)
    if msg:
        getattr(st, msg[0])(msg[1])


# ---------- run selection ----------
runs = list_runs()
if not runs:
    st.warning("No runs yet. Run `python run_all.py` first.")
    st.stop()
names = [r.name for r in runs]
wanted = st.query_params.get("run")
default = names.index(wanted) if wanted in names else 0

head_l, head_r = st.columns([3, 1.3])
with head_r:
    run_dir = st.selectbox("Campaign run", runs, index=default, format_func=run_label)
    with st.popover("Review settings", width="stretch"):
        reviewer = st.text_input("Reviewer", st.session_state.get("reviewer", "Leticia Rossi"))
        st.session_state["reviewer"] = reviewer
        warn_policy = st.radio("Routing policy for warnings · set by your Umbu admin",
                               ["Send to review", "Auto-pass with notes"],
                               help="Blocks always go to a person. This decides what happens to assets with only warnings.")
reviewer = st.session_state.get("reviewer", "Leticia Rossi")

record = load_record(run_dir)
checks = {c["asset_id"]: c for c in record.get("checks", [])}
decisions = {d["asset_id"]: d for d in record.get("decisions", [])}
with head_l:
    page_header("Home / Review", record["plan"]["campaign_name"], f"Key message: {esc(record['plan']['key_message'])}")

if not checks:
    st.warning("This run hasn't been through the guardrails yet. Run `python run_checks.py`.")
    st.stop()

routes = {aid: effective_route(c["findings"], warn_policy) for aid, c in checks.items()}
n, done_n = len(record["assets"]), len(decisions)
pct = int(100 * done_n / n) if n else 0
scenario = (f"<div style='background:#EEE9F7;border-radius:10px;padding:12px 16px;font-size:14px;color:#2E1B55;margin-top:12px'>"
            f"<b>Scenario: {esc(record['scenario']['name'])}.</b> {esc(record['scenario']['story'])}</div>"
            if record.get("scenario") else "")
html(f"<div style='display:flex;align-items:center;gap:14px;flex-wrap:wrap'>"
     f"<span style='font-size:14px;font-weight:600'>{done_n} of {n} decided</span>"
     f"<div style='flex:1;min-width:200px;height:8px;border-radius:999px;background:#E6ECE9;overflow:hidden'>"
     f"<div style='width:{pct}%;height:100%;background:#0E4D52'></div></div>"
     f"<span style='font-size:13px;color:{SLATE}'>Warnings: {esc(warn_policy.lower())} · set by your Umbu admin</span></div>"
     f"{scenario}")
st.write("")

tab_review, tab_brief, tab_log = st.tabs([
    f"Content · {sum(r == 'must_fix' for r in routes.values())} must fix",
    "Brief check" + (" · issue" if record.get("brief_check", {}).get("findings") else ""),
    "Activity"])

# ---------- review ----------
with tab_review:
    order = sorted(record["assets"], key=lambda a: (ROUTE_ORDER[routes.get(a["asset_id"], "review")], a["asset_id"]))
    sel_key = f"sel-{run_dir.name}"
    if st.session_state.get(sel_key) not in [a["asset_id"] for a in order]:
        st.session_state[sel_key] = order[0]["asset_id"]
    takedowns = takedowns_for_run(run_dir.name)

    q_col, main = st.columns([1, 2.7], gap="medium")
    with q_col:
        with st.container(key="card-queue"):
            html(f"<div style='font-size:13px;color:{SLATE};margin-bottom:6px'>{n} assets · riskiest first</div>")
            for a in order:
                aid = a["asset_id"]
                label, kind = ROUTE_BADGE[routes.get(aid, "review")]
                d = decisions.get(aid)
                status = d["decision"] if d else label
                selected = st.session_state[sel_key] == aid
                if st.button(f"{CHANNEL_LABEL.get(a['channel'], a['channel'])}  ·  {status}",
                             key=f"{'qsel' if selected else 'q'}-{aid}", width="stretch"):
                    st.session_state[sel_key] = aid
                    st.rerun()
            html(f"<p style='font-size:12px;color:{SLATE};margin-top:10px'>Approved content is saved as an exact "
                 "snapshot and goes to the DAM.</p>")

    asset = next(a for a in record["assets"] if a["asset_id"] == st.session_state[sel_key])
    aid = asset["asset_id"]
    findings = merge_findings(checks.get(aid, {"findings": []})["findings"])
    route_now = routes.get(aid, "review")
    label, kind = ROUTE_BADGE[route_now]
    blocks = [f for f in findings if f["severity"] == "block"]
    warns = [f for f in findings if f["severity"] == "warn"]
    done = decisions.get(aid)

    with main:
        with st.container(key="cardblock-asset" if blocks else "card-asset"):
            decided = chip(f"Decided: {done['decision']}", "teal") if done else ""
            html(f"<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap'>"
                 f"<span class='rc'>{esc(aid)}</span>{provenance(asset)}<span style='margin-left:auto'>{chip(label, kind)} {decided}</span></div>"
                 f"<h2 style='margin:10px 0 2px;font-size:22px'>{esc(CHANNEL_LABEL.get(asset['channel'], asset['channel']))}</h2>")
            for t in takedowns.get(aid, []):
                st.error(f"Takedown requested by {t['owner_decision']['by']} (rule {t['rule_id']}): "
                         f"{t['owner_decision']['note'] or 'no note'}")
            if asset.get("edited_fields"):
                html(f"<p style='font-size:13px;color:{SLATE};margin:0 0 6px'>Edited: {esc(', '.join(asset['edited_fields']))}"
                     f" · every edit was re-checked by the guardrails</p>")

            c1, c2 = st.columns([3, 2], gap="medium")
            with c1:
                render_copy(asset["copy"], [f.get("quote") for f in findings])
            with c2:
                if asset.get("image"):
                    img = asset["image"]
                    st.image(str(run_dir / img["file"]), width="stretch")
                    html(f"{chip('AI-generated', 'ai')} <span style='font-size:13px;color:#3D4843'>"
                         f"Alt text: {esc(img['alt_text'])}</span>")

            html(f"<h3 style='font-size:16px;margin:16px 0 4px'>Guardrail findings ({len(findings)})</h3>")
            if findings:
                for f in findings:
                    render_finding(f)
            else:
                html(f"<div style='background:#E6F4EC;border-radius:10px;padding:12px 14px;color:#0B6B3A;font-weight:600'>"
                     "Passed all guardrails.</div>")

            flash(f"msg-{aid}")

            # ---- actions ----
            fixable = [f for f in findings if f.get("quote") and f.get("suggested_fix")]
            # natural-width buttons that wrap to a second line on narrow windows (no truncated labels)
            actions = st.container(horizontal=True, gap="small", vertical_alignment="center")
            b1 = b2 = b3 = b4 = actions
            with b1:
                if st.button(f"Accept AI suggestion{'s' if len(fixable) != 1 else ''}", type="primary",
                             disabled=not fixable, width="content", key=f"accept-{aid}",
                             help="Applies the suggested fixes, then re-checks the result with every guardrail"):
                    edits, applied, skipped = apply_suggestions(asset["copy"], fixable)
                    left = (f" Left for you: {', '.join(sorted(set(skipped)))} (the fix would repeat text "
                            "already in the field).") if skipped else ""
                    if not edits:
                        st.session_state[f"msg-{aid}"] = ("info", "None of the suggestions could be applied automatically. Edit manually.")
                    else:
                        with st.spinner("Applying the suggestions and re-checking with every guardrail..."):
                            new = recheck(project_or_none(), record, run_dir, asset, edits, reviewer, "ai_suggestion")
                        new_route = effective_route(new, warn_policy)
                        st.session_state[f"msg-{aid}"] = (
                            "success" if new_route != "must_fix" else "warning",
                            f"Applied fixes for {', '.join(sorted(set(applied)))}. Re-checked: "
                            f"{ROUTE_BADGE[new_route][0].lower()}.{left}")
                    st.rerun()
            with b2:
                editing = st.toggle("Edit manually", key=f"edit-{aid}")
            with b3:
                approve = st.button("Approve", disabled=bool(blocks), width="content", key=f"approve-{aid}",
                                    help="Fix the blocking findings first" if blocks else "Saves an exact snapshot")
            with b4:
                with st.popover("More", width="content"):
                    other = st.radio("Decision", ["Request changes", "Reject"], key=f"other-{aid}")
                    other_note = st.text_input("Note (saved to the record)", key=f"onote-{aid}")
                    if st.button("Save", key=f"osave-{aid}", type="primary"):
                        ok, k, m = decide(record, run_dir, asset, other, other_note, reviewer, findings, route_now)
                        st.session_state[f"msg-{aid}"] = (k, m)
                        st.rerun()

            note = ""
            if warns and not blocks:
                note = st.text_input("Approving over a warning? Say why. It goes to the rule's owner.",
                                     key=f"note-{aid}", placeholder="e.g. Short and long headlines never show together")
            if approve:
                ok, k, m = decide(record, run_dir, asset, "Approve", note, reviewer, findings, route_now)
                st.session_state[f"msg-{aid}"] = (k, m)
                st.rerun()

            if editing:
                with st.form(f"editform-{aid}"):
                    edits = {}
                    for field, value in asset["copy"].items():
                        if isinstance(value, list):
                            new = st.text_area(field.replace("_", " "), "\n".join(value), key=f"{aid}-{field}")
                            lines = [line for line in new.split("\n") if line.strip()]
                            if lines != value:
                                edits[field] = lines
                        else:
                            new = st.text_input(field.replace("_", " "), value, key=f"{aid}-{field}")
                            if new != value:
                                edits[field] = new
                    if st.form_submit_button("Save edits and re-check", type="primary"):
                        if not edits:
                            st.session_state[f"msg-{aid}"] = ("info", "No changes to save.")
                        else:
                            with st.spinner("Re-checking your edits with every guardrail..."):
                                new_f = recheck(project_or_none(), record, run_dir, asset, edits, reviewer, "manual")
                            st.session_state[f"msg-{aid}"] = (
                                "success", f"Edits saved and re-checked: {ROUTE_BADGE[effective_route(new_f, warn_policy)][0].lower()}.")
                        st.rerun()

# ---------- brief check ----------
with tab_brief:
    spec = load_mandatories()
    bc = record.get("brief_check")
    with st.container(key="card-brief"):
        state = chip("Brief mismatch", "warn") if bc and bc["findings"] else chip("All mandatories met", "pass") if bc else chip("Not run", "neutral")
        html(f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
             f"<h2 style='margin:0;font-size:20px'>Brief check</h2>"
             f"<span style='font-size:13px;color:{SLATE}'>Against campaign brief {esc(spec.get('brief_version', 'v1'))} · "
             f"owner: Campaign owner</span><span style='margin-left:auto'>{state}</span></div>"
             f"<p style='font-size:14px;color:#3D4843'>Runs on the approved version of each asset where there is one, "
             "because edits made during review can break the brief after creation.</p>")
        for m in spec["mandatories"]:
            html(f"<div style='font-size:14px;margin:4px 0'>{rule_code(m['id'], m['text'])} {esc(m['text'])} "
                 f"{chip('Rule-based' if m['method'] == 'code' else 'AI judgment', 'neutral' if m['method'] == 'code' else 'ai')}</div>")
        if bc and bc["findings"]:
            for f in bc["findings"]:
                render_finding({**f, "checkers": ["brief"], "field": f"{f['asset_id']} · {f['field']}"})
            html("<div style='display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px'>"
                 "<div style='border:1px solid #C9D4D0;border-radius:12px;padding:14px'><b>The content is wrong</b>"
                 "<div style='font-size:14px;color:#3D4843;margin-top:4px'>Fix it in the Content tab; the edit is re-checked against the brief too.</div>"
                 f"<div style='margin-top:6px'>{chip('Learning label: content error', 'ai')}</div></div>"
                 "<div style='border:1px solid #C9D4D0;border-radius:12px;padding:14px'><b>The brief changed</b>"
                 "<div style='font-size:14px;color:#3D4843;margin-top:4px'>Propose a brief amendment for the campaign owner to approve (next release).</div>"
                 f"<div style='margin-top:6px'>{chip('Learning label: context change', 'ai')}</div></div></div>")
        if bc:
            html(f"<p style='font-size:12px;color:{SLATE};margin-top:10px'>Checked {esc(bc['checked_at'])} · versions: "
                 + esc(", ".join(f"{k} {v}" for k, v in bc["checked_versions"].items())) + "</p>")
        if st.button("Re-run brief check on approved content", key="rerun-brief"):
            with st.spinner("Checking the campaign against its brief..."):
                record["brief_check"] = check_package(project_or_none(), record)
            save_record(run_dir, record)
            st.rerun()

# ---------- activity ----------
with tab_log:
    st.subheader("Decisions")
    st.caption("Every human decision is stored with the findings it was made against: Umbu's learning signal.")
    if record.get("decisions"):
        st.dataframe([{"asset": d["asset_id"], "decision": d["decision"], "reviewer": d["reviewer"],
                       "blocks": sum(f["severity"] == "block" for f in d["findings"]),
                       "warnings": sum(f["severity"] == "warn" for f in d["findings"]),
                       "edited": ", ".join(d["edited_fields"]) or "-", "note": d["note"], "time": d["timestamp"]}
                      for d in record["decisions"]], width="stretch", hide_index=True)
    else:
        st.write("No decisions yet.")
    st.subheader("Refused approvals")
    if record.get("audit"):
        st.dataframe([{"asset": a["asset_id"], "reviewer": a["reviewer"], "blocked by": ", ".join(a["blocking_rules"]),
                       "after edit": a["after_edit"], "time": a["timestamp"]} for a in record["audit"]],
                     width="stretch", hide_index=True)
    else:
        st.write("None.")
    st.subheader("Warning overrides sent to rule owners")
    run_overrides = [i for i in load_overrides() if i["run_id"] == run_dir.name]
    if run_overrides:
        st.dataframe([{"asset": i["asset_id"], "rule": i["rule_id"], "owner": i["owner"],
                       "reviewer note": i["reviewer_note"], "status": STATUS_LABEL.get(i["status"], i["status"])}
                      for i in run_overrides], width="stretch", hide_index=True)
    else:
        st.write("None.")
