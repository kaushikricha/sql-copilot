import os
import re
import streamlit as st
import pandas as pd
import pyodbc
from openai import OpenAI

WRITE_KEYWORDS = [
    "delete", "update", "insert", "drop", "alter", "truncate",
    "create", "merge", "grant", "revoke", "exec", "execute"
]

def contains_write_intent(text: str) -> bool:
    t = text.lower()
    return any(re.search(rf"\b{kw}\b", t) for kw in WRITE_KEYWORDS)

# ---------- Grok client (xAI OpenAI-compatible) ----------
xai_client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

def nl_to_sql(nl_request: str, db_name: str) -> str:
    system_prompt = (
        "You are an expert SQL Server assistant. "
        "Return ONLY a single SQL Server SELECT statement. "
        "No explanation. No markdown. No semicolon. "
        "Never use INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE."
    )

    context = (
        f"Database: {db_name}. "
        "Use the schema and table names exactly as provided by the user. "
        "If the user mentions Person.Person, use Person.Person. "
        "Return only a SQL Server SELECT statement."
    )

    response = xai_client.chat.completions.create(
        model="grok-4-latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\nUser request: {nl_request}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()

# ---------- Streamlit UI ----------
st.set_page_config(page_title="SQL Copilot", layout="wide")

# ✅ Initialize session state keys once
if "generated_sql" not in st.session_state:
    st.session_state["generated_sql"] = ""
if "sql_query" not in st.session_state:
    st.session_state["sql_query"] = ""

st.sidebar.header("SQL Server Settings")
host = st.sidebar.text_input("Server", "localhost")
database = st.sidebar.text_input("Database", "SqlCopilotDB")
st.sidebar.caption(f"Selected: SQL Server @ {host}")

def make_conn_str() -> str:
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={host};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

if st.sidebar.button("Test Connection"):
    try:
        with pyodbc.connect(make_conn_str()) as conn:
            pass
        st.sidebar.success("✅ Connection successful!")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {e}")

st.title("🧠 SQL Copilot")
st.markdown("Natural language → SQL (Grok) + safe SQL execution on SQL Server")

# --- NL -> SQL ---
st.subheader("Ask in English (Grok → SQL)")
nl_input = st.text_input("Example: show students older than 25")

if st.button("Generate SQL with Grok"):
    if not database.strip():
        st.warning("Please enter Database name in the sidebar first.")
    elif not nl_input.strip():
        st.warning("Please enter a request.")
    elif contains_write_intent(nl_input):
        st.error(
            "🚫 Unsafe request detected. This app is in Safe Mode (SELECT-only). "
            "Please ask a read-only question like: 'show', 'list', 'count'."
        )
        st.session_state["generated_sql"] = ""
        st.session_state["sql_query"] = ""   # ✅ clear the SQL box too
        st.stop()
    else:
        try:
            generated_sql = nl_to_sql(nl_input, database)

            if not generated_sql.strip().lower().startswith(("select", "with")):
                st.error("🚫 Generated SQL is not SELECT/WITH. Blocked for safety.")
                st.session_state["generated_sql"] = ""
                st.session_state["sql_query"] = ""
            else:
                # ✅ Store in BOTH places so the textbox updates
                st.session_state["generated_sql"] = generated_sql
                st.session_state["sql_query"] = generated_sql

                st.success("Generated SQL:")
                st.code(generated_sql, language="sql")

                # Optional: force UI refresh immediately
                st.rerun()

        except Exception as e:
            st.error(f"Grok error: {e}")

# --- Run SQL ---
st.subheader("Run SQL (Safe Mode: SELECT only)")

# ✅ No value= here (session_state controls it via key)
query = st.text_area(
    "SQL Query",
    height=160,
    key="sql_query",
)

if st.button("Run Query"):
    if not query.strip():
        st.warning("Please enter a SQL query.")
    elif not query.strip().lower().startswith(("select", "with")):
        st.error("Only SELECT queries are allowed.")
    else:
        try:
            with pyodbc.connect(make_conn_str()) as conn:
                df = pd.read_sql(query, conn)
                df.columns = [col if col else "Result" for col in df.columns]
            st.success("Query ran successfully!")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Query failed: {e}")