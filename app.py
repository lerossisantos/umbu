"""Umbu app. Start it with:  streamlit run app.py

PROOF OF CONCEPT: this standalone UI proves the review interaction. In production,
Umbu's findings and approve/reject actions would live inside the workflow tools
reviewers already use (e.g. Workfront, Jira, their DAM), not in a separate app."""
import streamlit as st

from umbu.ui import apply_brand

st.set_page_config(page_title="Umbu", page_icon="assets/umbu-icon.png", layout="wide")
apply_brand()

page = st.navigation([
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/review.py", title="Review", url_path="review"),
    st.Page("views/owner_inbox.py", title="Owner inbox", url_path="owner-inbox"),
], position="top")
page.run()
