from __future__ import annotations

import os

import streamlit as st

from mf_facts.service import build_service
from mf_facts.settings import Settings

st.set_page_config(page_title="MF Facts Bot", page_icon="📘", layout="centered")


def _bridge_secrets() -> None:
    """On Streamlit Community Cloud, secrets live in st.secrets, not env vars."""
    try:
        secrets = st.secrets
        for key in ("GROQ_API_KEY", "GROQ_MODEL"):
            if key not in os.environ and key in secrets:
                os.environ[key] = str(secrets[key])
    except Exception:
        # local runs have no secrets.toml; .env / exported vars are used instead
        return


_bridge_secrets()

EXAMPLES = [
    "What is the expense ratio of HDFC Flexi Cap Fund?",
    "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
    "How do I download my consolidated account statement?",
]


@st.cache_resource(show_spinner="Loading index and models…")
def get_service():
    return build_service(Settings.load())


def render(answer) -> None:
    if answer.kind == "answer":
        st.markdown(answer.text)
    else:
        st.info(answer.text)
    if answer.citation_url:
        st.markdown(f"**Source:** [{answer.citation_url}]({answer.citation_url})")
    if answer.updated_at:
        st.caption(f"Last updated from sources: {answer.updated_at.isoformat()}")


service = get_service()

st.title("Mutual fund facts, with sources")
st.write("Ask a factual question about a mutual fund scheme. "
         "I answer from official public pages only.")
st.caption("**Facts-only. No investment advice.**")

st.write("**Try:**")
columns = st.columns(3)
clicked = None
for column, example in zip(columns, EXAMPLES):
    if column.button(example, use_container_width=True):
        clicked = example

typed = st.chat_input("Ask about expense ratio, exit load, minimum SIP, lock-in…")
query = clicked or typed

if query:
    st.chat_message("user").write(query)
    with st.chat_message("assistant"):
        with st.spinner("Checking sources…"):
            render(service.ask(query))

with st.expander("Disclaimer"):
    st.write(
        "**Facts-only. No investment advice.** This assistant reports publicly available "
        "scheme facts and links to the official source. It does not recommend, rank, or "
        "predict returns. Always verify on the AMC/SEBI/AMFI page before acting."
    )
