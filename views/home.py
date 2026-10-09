"""Home: one entry point per persona, with live status from the latest campaign runs."""
import datetime

import streamlit as st

from umbu.governance import OPEN, load_overrides
from umbu.review_logic import list_runs, run_summary
from umbu.ui import SLATE, TEAL, chip, esc, html

runs = list_runs()
latest_own = next((r for r in runs if "-" not in r.name.split("-", 1)[1]), runs[0] if runs else None) if runs else None
latest_any = runs[0] if runs else None
summary = run_summary(latest_any) if latest_any else None
open_overrides = [i for i in load_overrides() if i["status"] == OPEN]

hour = datetime.datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"

top = st.columns([3, 1])
with top[0]:
    html(f"<h1 style='margin:0;font-size:40px;line-height:1.15;letter-spacing:-0.02em'>{greeting}, Leticia</h1>"
         f"<p style='margin:10px 0 0;font-size:17px;color:{SLATE};max-width:640px'>Every asset is checked against "
         "Northwind's brand canon, approved claims, channel specs and regulations before anyone sees it.</p>")
with top[1]:
    st.selectbox("Brand workspace", ["Northwind", "Northwind Kids", "Northwind EU"])

st.write("")

ICON = {  # simple line icons in the brand teal
    "create": '<path d="M11 2v4M11 16v4M2 11h4M16 11h4M4.6 4.6l2.8 2.8M14.6 14.6l2.8 2.8M4.6 17.4l2.8-2.8M14.6 7.4l2.8-2.8"/>',
    "vet": '<path d="M11 14V3M6.5 7.5 11 3l4.5 4.5"/><path d="M3 14v4h16v-4"/>',
    "review": '<path d="M11 2 3 5v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V5z"/><path d="m7.5 11 2.5 2.5 4.5-5"/>',
    "inbox": '<path d="M3 12h4l2 3h4l2-3h4"/><path d="M5 5h12l2 7v6H3v-6z"/>',
}


def card(icon, who, title, body, footer, href=None, highlight=False):
    border = f"2px solid {TEAL}" if highlight else "1px solid #DDE3E0"
    badge = chip("Needs you", "teal") if highlight else ""
    inner = (f"<div style='display:flex;flex-direction:column;gap:14px;background:#FFFFFF;border:{border};"
             f"border-radius:14px;padding:26px;min-height:250px;box-sizing:border-box'>"
             f"<div style='display:flex;align-items:center;gap:12px'>"
             f"<div style='width:44px;height:44px;border-radius:10px;background:#E3EFEE;display:flex;align-items:center;justify-content:center'>"
             f"<svg width='22' height='22' viewBox='0 0 22 22' fill='none' stroke='{TEAL}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>{ICON[icon]}</svg></div>"
             f"<span style='font-size:13px;font-weight:600;color:{SLATE}'>{who}</span><span style='margin-left:auto'>{badge}</span></div>"
             f"<div style='font-size:22px;font-weight:700'>{title}</div>"
             f"<div style='font-size:15px;line-height:1.5;color:#3D4843'>{body}</div>"
             f"<div style='margin-top:auto;padding-top:14px;border-top:1px solid #EDF1EF;font-size:14px;color:#3D4843'>{footer}</div></div>")
    html(f"<a class='ucard' href='{href}' target='_self'>{inner}</a>" if href else
         f"<a class='ucard' href='#'>{inner}</a>")


if summary:
    rec = summary["record"]
    last = (f"Last run: {esc(rec['plan']['campaign_name'])} · {len(rec['assets'])} assets")
    review_footer = (f"<span style='color:#A3201A;font-weight:600'>{summary['must_fix']} must fix</span> &nbsp; "
                     f"<span style='color:#8A4B00;font-weight:600'>{summary['review']} to review</span> &nbsp; "
                     f"<span style='color:#0B6B3A;font-weight:600'>{summary['auto_pass']} auto-passed</span>")
else:
    last, review_footer = "No runs yet", "Nothing to review"
if open_overrides:
    rules = sorted({i["rule_id"] for i in open_overrides})
    owners = sorted({i["owner"] for i in open_overrides})
    inbox_footer = (f"<b>{len(open_overrides)} open override{'s' if len(open_overrides) != 1 else ''}</b> for "
                    f"{', '.join(owners)} · <span class='rc'>{', '.join(rules)}</span>")
else:
    inbox_footer = "No open overrides"

row1 = st.columns(2, gap="medium")
with row1[0]:
    card("create", "For campaign owners", "Create content from a brief",
         "Submit a campaign brief. Agents plan the messages, write the copy and generate images, then the guardrails check everything.",
         last)
with row1[1]:
    card("vet", "For content made outside Umbu", "Vet pre-created content",
         "Upload copy and images made outside Umbu, by your team, an agency or another AI tool. The same guardrails check it before it goes live.",
         "Made anywhere, by anyone · Same rules, same audit trail")
st.write("")
row2 = st.columns(2, gap="medium")
with row2[0]:
    card("review", "For reviewers", "Review guardrail feedback",
         "Approve, edit or reject each piece of content. Blocked content can't be approved until it's fixed and re-checked.",
         review_footer, href="review", highlight=bool(summary and (summary["must_fix"] or summary["review"])))
with row2[1]:
    card("inbox", "For brand, legal and channel owners", "Guardrail owner inbox",
         "See where reviewers overrode a rule, grouped by rule. Decide whether the rule changes and whether the content has to be adjusted.",
         inbox_footer, href="owner-inbox")

# ---------- recent runs ----------
st.write("")
html("<h2 style='font-size:18px;margin:18px 0 12px'>Recent campaign runs</h2>")
rows = []
for r in runs[:6]:
    s = run_summary(r)
    rec = s["record"]
    source = "AI-generated, human-edited" if rec.get("scenario") else "AI-generated"
    name = rec["plan"]["campaign_name"] + (f" · {rec['scenario']['name']}" if rec.get("scenario") else "")
    if s["must_fix"]:
        status = f"<span style='color:#A3201A;font-weight:600'>{s['must_fix']} must fix</span>"
    elif s["review"]:
        status = f"<span style='color:#8A4B00;font-weight:600'>{s['review']} to review</span>"
    else:
        status = "<span style='color:#0B6B3A;font-weight:600'>All clear</span>"
    when = datetime.datetime.strptime(r.name[:15], "%Y%m%d-%H%M%S").strftime("%b %d, %-I:%M %p")
    rows.append(f"<tr><td><a href='review?run={r.name}' target='_self' style='color:{TEAL};font-weight:600'>{esc(name)}</a></td>"
                f"<td>{source}</td><td>{len(rec['assets'])}</td><td>{status}</td><td style='color:{SLATE}'>{when}</td></tr>")
html("<div style='border:1px solid #DDE3E0;border-radius:12px;overflow:hidden'><table class='ut'>"
     "<tr><th>Run</th><th>Source</th><th>Assets</th><th>Status</th><th>Updated</th></tr>"
     + "".join(rows) + "</table></div>")
html(f"<p style='margin-top:18px;font-size:13px;color:{SLATE}'>Proof of concept. In production, Umbu's findings and "
     "decisions would appear inside the workflow tools your teams already use.</p>")
