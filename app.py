from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# Streamlit Community Cloud installs requirements.txt but not the local package.
# Put src/ on the path so `mf_facts` imports work without `pip install -e .`.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mf_facts.service import build_service  # noqa: E402
from mf_facts.settings import Settings  # noqa: E402

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
    "What is a mutual fund?",
    "What is a flexi cap fund?",
    "Can you give me some example of flexi cap funds?",
]


@st.cache_resource(show_spinner="Loading index and models…")
def get_service():
    return build_service(Settings.load())


def to_record(answer) -> dict:
    """Serializable snapshot so history survives Streamlit reruns."""
    return {
        "kind": answer.kind,
        "text": answer.text,
        "citation_url": answer.citation_url,
        "updated_at": answer.updated_at.isoformat() if answer.updated_at else None,
    }


def render_answer(record: dict) -> None:
    if record["kind"] == "answer":
        st.markdown(record["text"])
    else:
        st.info(record["text"])
    if record.get("citation_url"):
        st.markdown(f"**Source:** [{record['citation_url']}]({record['citation_url']})")
    if record.get("updated_at"):
        st.caption(f"Last updated from sources: {record['updated_at']}")


service = get_service()

# Chat history lives in session state and is rendered oldest-first, like a
# normal messaging app. New turns are appended below the existing ones.
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Mutual fund facts, with sources")
st.write("Ask a factual question about a mutual fund scheme, or a basic mutual "
         "fund concept. I answer from official public pages only.")
st.caption("**Facts-only. No investment advice.**")

with st.sidebar:
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.write("**What I cover**")
    st.write(
        "Expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark and "
        "statement downloads for four HDFC schemes, plus basic concepts such as "
        "SIP, NAV, flexi cap and ELSS."
    )
    with st.expander("Disclaimer"):
        st.write(
            "Facts-only. No investment advice. This assistant reports publicly "
            "available scheme facts and links to the official source. It does not "
            "recommend, rank, or predict returns. Always verify on the AMC/SEBI/AMFI "
            "page before acting."
        )

with st.expander("Example questions", expanded=not st.session_state.messages):
    columns = st.columns(3)
    clicked = None
    for index, example in enumerate(EXAMPLES):
        if columns[index % 3].button(
            example, key=f"example-{index}", use_container_width=True
        ):
            clicked = example

# Render the full conversation before handling a new turn. The new turn is then
# appended and painted once, so old questions never disappear.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_answer(message["answer"])

typed = st.chat_input("Ask about a scheme fact or a mutual fund basic…")
query = clicked or typed

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Checking sources…"):
            answer = service.ask(query)
        record = to_record(answer)
        render_answer(record)

    st.session_state.messages.append({"role": "assistant", "answer": record})
