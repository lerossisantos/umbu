"""Umbu's visual identity for the Streamlit proof of concept ("Rooted": deep teal,
quiet neutrals, status colors only for status). Mirrors the mockup and the visual
identity guide. Screens use these helpers so they all look like one product."""
import html as _html

import streamlit as st

TEAL = "#0E4D52"
INK = "#16201C"
SLATE = "#55615B"
STATUS = {  # text, background
    "block": ("#A3201A", "#FCE9E7"),
    "warn": ("#8A4B00", "#FDF1DE"),
    "pass": ("#0B6B3A", "#E6F4EC"),
    "ai": ("#4B2E83", "#EEE9F7"),
    "neutral": ("#3D4843", "#EEF1F0"),
    "teal": ("#0E4D52", "#E3EFEE"),
}

# Reviewer-facing names for each checker (never model names).
CHECKER_LABEL = {
    "channel_spec": "Channel specs",
    "claims": "Claims & regulatory",
    "brand_voice": "Brand voice",
    "brief": "Brief compliance",
}
AI_JUDGMENT = {"claims", "brand_voice"}


def esc(text) -> str:
    return _html.escape(str(text))


def chip(text: str, kind: str) -> str:
    fg, bg = STATUS[kind]
    return (f"<span style='background:{bg};color:{fg};font-weight:700;font-size:13px;vertical-align:middle;"
            f"border-radius:999px;padding:3px 10px;white-space:nowrap'>{esc(text)}</span>")


def rule_code(rule_id: str, rule_text: str = "") -> str:
    """Rule IDs in IBM Plex Mono; hover shows the rule text (like the mockup)."""
    tip = f" title='{esc(rule_id)}: {esc(rule_text)}'" if rule_text else ""
    under = "text-decoration:underline dotted;text-underline-offset:3px;cursor:help;" if rule_text else ""
    return f"<span class='rc'{tip} style='{under}'>{esc(rule_id)}</span>"


def html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def page_header(crumb: str, title: str, subtitle: str = ""):
    sub = f"<p style='margin:4px 0 0;font-size:16px;color:{SLATE}'>{subtitle}</p>" if subtitle else ""
    html(f"<div style='margin-bottom:18px'><div style='font-size:13px;color:{SLATE}'>{crumb}</div>"
         f"<h1 style='margin:6px 0 0;font-size:32px;line-height:1.2'>{esc(title)}</h1>{sub}</div>")


def apply_brand():
    st.logo("assets/umbu-logo.png", size="large")
    st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
html, body, p, li, label, input, textarea, button, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { font-family: 'Public Sans', system-ui, sans-serif; }
h1, h2, h3, h4 { font-family: 'Public Sans', system-ui, sans-serif !important; font-weight: 700 !important; color: #16201C; letter-spacing: -0.01em; padding: 0 !important; }
header[data-testid="stHeader"] { background: #FFFFFF; border-bottom: 1px solid #DDE3E0; }
.block-container { max-width: 1320px; padding-top: 4.5rem !important; }
code, .rc { font-family: 'IBM Plex Mono', monospace !important; color: #0E4D52 !important; background: #E3EFEE !important; border-radius: 6px; padding: 1px 6px; font-size: 0.9em; }
mark { background: #FCE9E7; color: #16201C; border-radius: 3px; padding: 0 3px; }
/* white cards: any container with a key that starts with "card" */
[class*="st-key-card"] { background: #FFFFFF; border: 1px solid #DDE3E0; border-radius: 14px; padding: 20px 22px; }
[class*="st-key-cardblock"] { background: #FFFAF9; border-color: #E8B9B4; }
[class*="st-key-cardsel"] { border: 2px solid #0E4D52; }
/* buttons: primary = teal, secondary = white with border */
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"] { background: #0E4D52; border-color: #0E4D52; font-weight: 700; }
.stButton button[kind="secondary"] { background: #FFFFFF; border-color: #C9D4D0; color: #16201C; font-weight: 600; }
.stButton button:disabled { background: #EEF1F0 !important; border: 1px dashed #C9D4D0 !important; color: #8C9692 !important; }
/* queue buttons look like list rows */
[class*="st-key-q-"] button, [class*="st-key-qsel-"] button { justify-content: flex-start !important; text-align: left; border: 0 !important; border-radius: 8px !important; min-height: 44px; padding-left: 12px; }
[class*="st-key-q-"] button { background: transparent !important; }
[class*="st-key-qsel-"] button { background: #E3EFEE !important; border-left: 3px solid #0E4D52 !important; font-weight: 700; }
[class*="st-key-q-"] button > div, [class*="st-key-qsel-"] button > div, [class*="st-key-q-"] button [data-testid="stMarkdownContainer"], [class*="st-key-qsel-"] button [data-testid="stMarkdownContainer"] { width: 100%; text-align: left; justify-content: flex-start; }
[class*="st-key-q-"] button p, [class*="st-key-qsel-"] button p { text-align: left; }
a.ucard { display: block; text-decoration: none !important; color: #16201C !important; }
a.ucard:hover > div { border-color: #0E4D52 !important; }
table.ut { width: 100%; border-collapse: collapse; font-size: 14px; background: #FFFFFF; }
table.ut th { text-align: left; color: #55615B; font-weight: 600; padding: 12px 16px; border-bottom: 1px solid #DDE3E0; }
table.ut td { padding: 12px 16px; border-bottom: 1px solid #EDF1EF; }
</style>""")
