"""Analytics Copilot — console over the FastAPI backend.

Not a generic chatbot: you ask a business question in natural language, the
LangGraph workflow turns it into a *validated, read-only* SELECT over the dbt
AI marts, and this UI shows three things side by side — the answer, what the
pipeline did to get there (the generated SQL + self-healing trace), and the
governed Superset dashboard the same marts power.

The UI is a pure HTTP client; all logic lives in the API.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Analytics Copilot",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_URL = os.getenv("CORE_API_URL", "http://localhost:8090")
SUPERSET_URL = os.getenv("SUPERSET_URL", "http://localhost:8088")
# Dashboard id/slug to embed — defaults to the committed demo dashboard.
SUPERSET_DASHBOARD_ID = os.getenv("SUPERSET_DASHBOARD_ID", "brazil_ecommerce").strip()
REQUEST_TIMEOUT = 300

EXAMPLE_QUESTIONS = [
    "Which product categories have the highest revenue?",
    "Show the top 10 customers by number of orders.",
    "What is the monthly revenue trend this year?",
    "List sellers with the most late deliveries.",
]


# --- Styling ---------------------------------------------------------------
st.markdown(
    """
    <style>
      html, body, [class*="css"], button, input, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
          Roboto, Helvetica, Arial, sans-serif;
      }
      #MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; }
      .block-container {
        padding-top: 2rem; padding-bottom: 3rem;
        padding-left: 3rem; padding-right: 3rem; max-width: 100%;
      }
      h1, h2, h3, h4 { color: #2b3a55; font-weight: 700; letter-spacing: -0.015em; }
      .brand { font-size: 1.45rem; font-weight: 800; color: #2b3a55;
        letter-spacing: -0.02em; }
      .brand span { color: #2f7d6b; }
      .subtle { color: #7a828e; font-size: 0.88rem; }
      .eyebrow { color: #2f7d6b; font-weight: 700; font-size: 0.78rem;
        text-transform: uppercase; letter-spacing: 0.08em; }
      .stButton > button { border-radius: 10px; font-weight: 600; }
      .step { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
      .dot { width: 10px; height: 10px; border-radius: 50%; flex: 0 0 auto; }
      .dot.ok { background: #2f7d6b; }
      .dot.warn { background: #d99a2b; }
      .dot.err { background: #c0483b; }
      .dot.idle { background: #d7dbe0; }
      .step-label { color: #2b3a55; font-weight: 600; font-size: 0.92rem; }
      .step-note { color: #7a828e; font-size: 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Session state ---------------------------------------------------------
def init_state() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("question", "")
    st.session_state.setdefault("pending_question", None)


init_state()


def api_error(resp: requests.Response) -> str:
    """Pull a human-readable message out of an error response."""
    try:
        body = resp.json()
        return body.get("detail") or body.get("error", {}).get("message") or resp.text
    except Exception:
        return resp.text


def _node_line(node: str | None, data: dict[str, Any]) -> str | None:
    """One human-readable status line for a workflow node event."""
    if node == "sql_generator":
        return f"Generating SQL — attempt {data.get('attempt', 1)}…"
    if node == "sql_validator":
        if data.get("status") == "valid":
            return "SQL validated ✓ (read-only, marts only)"
        return f"↩ Rejected: {data.get('validation_error', 'invalid')} — retrying"
    if node == "sql_executor":
        if data.get("error"):
            return f"Execution failed: {data['error']}"
        return f"Executed ✓ — {data.get('row_count', 0)} row(s)"
    if node == "result_formatter":
        return "Summarizing the result…"
    if node == "error_handler":
        return "Handling error…"
    return None


def run_query_stream(question: str) -> dict[str, Any] | None:
    """Stream /query/stream, show the pipeline live, return the final payload.

    The API emits one SSE event per workflow node (see TraceEvent), so the user
    watches the SQL get generated, validated, self-corrected and executed in
    real time — then a terminal ``final`` event carries the answer + rows.
    """
    try:
        resp = requests.post(
            f"{API_URL}/query/stream",
            json={"question": question},
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )
    except Exception as exc:  # network / connection error
        st.error(f"Cannot reach API at {API_URL}: {exc}")
        return None
    if resp.status_code != 200:
        st.error(f"Error {resp.status_code}: {api_error(resp)}")
        return None

    status = st.status("Working…", expanded=True)
    final: dict[str, Any] | None = None
    rationale: str | None = None

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode() if isinstance(raw, bytes) else raw
        if not line.startswith("data:"):
            continue
        event = json.loads(line[5:].strip())
        etype = event.get("type")
        data = event.get("data", {})

        if etype == "node":
            line_text = _node_line(event.get("node"), data)
            if line_text:
                status.write(line_text)
            if data.get("rationale"):
                rationale = data["rationale"]
        elif etype == "final":
            status.update(label="Done", state="complete", expanded=False)
            final = data
            # Carry the generator's rationale through — the /query/stream final
            # event doesn't repeat it, but the panel wants "why this SQL".
            final["rationale"] = rationale
        elif etype == "error":
            status.update(label="Error", state="error", expanded=True)
            st.error(data.get("message", "Workflow failed."))

    return final


# --- Pipeline summary (persistent view of the streamed run) ----------------
def _step(state: str, label: str, note: str = "") -> None:
    note_html = f"<span class='step-note'>· {note}</span>" if note else ""
    st.markdown(
        f"<div class='step'><span class='dot {state}'></span>"
        f"<span class='step-label'>{label}</span>{note_html}</div>",
        unsafe_allow_html=True,
    )


def render_pipeline(result: dict[str, Any]) -> None:
    """Persistent structural summary of the run, from the final payload.

    The live blow-by-blow shows in the st.status during streaming; this stays
    behind afterwards so the SQL, self-correction count and row count remain
    visible once the stream has closed.
    """
    sql = result.get("sql")
    error = result.get("error")
    retries = int(result.get("retry_count", 0))
    row_count = int(result.get("row_count", 0))

    gen = "ok" if sql else "err"
    _step(gen, "Generate SQL", "LLM → single SELECT over AI marts")

    if not sql:
        _step("err", "Validate SQL", "generation failed")
        _step("idle", "Execute")
        _step("idle", "Summarize")
        return

    val_note = f"self-corrected ×{retries}" if retries else "3-layer AST check passed"
    _step("warn" if retries else "ok", "Validate SQL", val_note)

    if error:
        _step("err", "Execute", "query failed")
        _step("idle", "Summarize")
        return

    _step("ok", "Execute", f"{row_count} row(s), read-only")
    _step("ok", "Summarize", "grounded natural-language answer")


# --- Results (table + auto chart) ------------------------------------------
def render_results(result: dict[str, Any]) -> None:
    rows = result.get("rows") or []
    if not rows:
        st.caption("No rows returned.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    numeric = df.select_dtypes(include="number").columns.tolist()
    non_numeric = [c for c in df.columns if c not in numeric]
    # Offer a chart only when there's a clear label + measure shape.
    if numeric and non_numeric and len(df) <= 100:
        with st.expander("Chart", expanded=True):
            c1, c2, c3 = st.columns(3)
            label_col = c1.selectbox("Category", non_numeric, key="chart_label")
            value_col = c2.selectbox("Measure", numeric, key="chart_value")
            kind = c3.selectbox("Type", ["Bar", "Line"], key="chart_kind")
            chart_df = df[[label_col, value_col]].set_index(label_col)
            if kind == "Bar":
                st.bar_chart(chart_df)
            else:
                st.line_chart(chart_df)


# ===========================================================================
# HEADER
# ===========================================================================
brand_col, _ = st.columns([4, 2])
with brand_col:
    st.markdown("<div class='brand'>Analytics <span>Copilot</span></div>", True)
    st.markdown(
        "<div class='subtle'>Natural-language analytics over dbt marts — "
        "validated, read-only SQL.</div>",
        True,
    )

st.divider()
copilot_tab, dashboard_tab = st.tabs(["Copilot", "Dashboard"])


# ===========================================================================
# COPILOT TAB
# ===========================================================================
with copilot_tab:
    ask_col, trace_col = st.columns([1.4, 1], gap="large")

    with ask_col:
        st.markdown("<div class='eyebrow'>Ask</div>", True)
        with st.form("ask_form", clear_on_submit=False):
            question = st.text_area(
                "Question",
                value=st.session_state.question,
                height=90,
                placeholder="Which product categories have the highest revenue?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Ask", type="primary")

        st.markdown("<div class='subtle'>Try one of these:</div>", True)
        chip_cols = st.columns(2)
        for i, example in enumerate(EXAMPLE_QUESTIONS):
            if chip_cols[i % 2].button(example, key=f"ex_{i}"):
                st.session_state.pending_question = example
                st.rerun()

        # Resolve which question to run this pass.
        to_run: str | None = None
        if submitted and question.strip():
            to_run = question.strip()
        elif st.session_state.pending_question:
            to_run = st.session_state.pending_question
            st.session_state.question = to_run
        st.session_state.pending_question = None

        if to_run:
            st.session_state.result = run_query_stream(to_run)

        result = st.session_state.result
        if result:
            st.write("")
            with st.container(border=True):
                st.markdown(result.get("answer") or "_(empty answer)_")
            render_results(result)

    with trace_col:
        st.markdown("<div class='eyebrow'>Behind the scenes</div>", True)
        result = st.session_state.result
        if not result:
            st.caption("Ask a question to see the pipeline and the SQL it ran.")
        else:
            render_pipeline(result)
            st.write("")
            if result.get("sql"):
                st.markdown("<div class='subtle'>Generated SQL</div>", True)
                st.code(result["sql"], language="sql")
            if result.get("rationale"):
                st.markdown("<div class='subtle'>Why this SQL</div>", True)
                st.caption(result["rationale"])
            if result.get("error"):
                st.error(result["error"])


# ===========================================================================
# DASHBOARD TAB — embedded Superset
# ===========================================================================
with dashboard_tab:
    st.markdown("<div class='eyebrow'>Governed dashboard</div>", True)
    st.markdown(
        "<div class='subtle'>The same dbt marts, pre-aggregated for BI. "
        "Powered by Apache Superset.</div>",
        True,
    )
    st.write("")
    if SUPERSET_DASHBOARD_ID:
        embed_url = (
            f"{SUPERSET_URL}/superset/dashboard/{SUPERSET_DASHBOARD_ID}/"
            "?standalone=1&show_filters=0"
        )
        st.components.v1.iframe(embed_url, height=900, scrolling=True)
    else:
        st.info(
            "Set `SUPERSET_DASHBOARD_ID` (and start Superset with "
            "`make up-dashboard`) to embed the dashboard here. Open Superset at "
            f"{SUPERSET_URL} to find a dashboard's id in its URL."
        )
