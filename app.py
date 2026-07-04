"""
app.py
-------
Streamlit UI for the text-to-SQL agent.

Run with:
    export GEMINI_API_KEY="your-key-here"
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
from agent import ask, SQLAgentError, DB_PATH
import sqlite3

st.set_page_config(page_title="E-Commerce Data Assistant", page_icon="🛒", layout="wide")

st.title("🛒 E-Commerce Data Assistant")
st.caption("Ask questions about the sales data in plain English — the agent writes and runs the SQL for you.")

with st.sidebar:
    st.header("About this project")
    st.write(
        "This is a text-to-SQL agent built on top of an e-commerce transactions "
        "database. It converts your question into a SQL query using Google's Gemini "
        "model, runs it, and explains the result in plain English."
    )
    st.subheader("Database tables")
    st.code("customers\norders\norder_items", language="text")

    st.subheader("Try asking:")
    example_questions = [
        "What is the total revenue by product category?",
        "Which city has the most customers?",
        "What is the average order value for customers who used a discount?",
        "How many customers signed up through Paid Ads?",
        "What is the monthly revenue trend for 2025?",
        "Which payment method is used most often?",
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True):
            st.session_state["question_input"] = q

if "history" not in st.session_state:
    st.session_state["history"] = []

question = st.text_input(
    "Ask a question about the sales data:",
    key="question_input",
    placeholder="e.g. What was the top-selling category last quarter?",
)

col1, col2 = st.columns([1, 5])
with col1:
    submit = st.button("Ask", type="primary")

if submit and question.strip():
    with st.spinner("Thinking through the query..."):
        try:
            result = ask(question)
            st.session_state["history"].insert(0, result)
        except SQLAgentError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Something went wrong: {e}")

for item in st.session_state["history"]:
    with st.container(border=True):
        st.markdown(f"**Q: {item['question']}**")
        st.markdown(item["answer"])
        with st.expander("Show generated SQL and raw result"):
            st.code(item["sql"], language="sql")
            st.dataframe(item["result"], use_container_width=True)
