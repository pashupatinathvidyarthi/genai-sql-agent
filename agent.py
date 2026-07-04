"""
agent.py
---------
Core text-to-SQL agent logic — powered by Google's Gemini API (free tier).

Flow:
  1. Take a natural-language question from the user.
  2. Send it to Gemini along with the database schema, asking for a SQL query.
  3. Run basic safety checks on the generated SQL (block writes/deletes).
  4. Execute the query against the SQLite database.
  5. Send the result back to Gemini and ask for a plain-English answer.

Requires: GEMINI_API_KEY environment variable to be set.
    Get a free key (no credit card required) at: https://aistudio.google.com
    export GEMINI_API_KEY="AIza..."
"""

import os
import re
import sqlite3
import pandas as pd
from google import genai

DB_PATH = os.path.join(os.path.dirname(__file__), "ecommerce.db")
MODEL = "gemini-2.5-flash"  # fast, high free-tier quota — good fit for this use case

SCHEMA_DESCRIPTION = """
Table: customers
  - customer_id (INTEGER, primary key)
  - signup_date (TEXT, format YYYY-MM-DD)
  - city (TEXT)
  - age (INTEGER)
  - gender (TEXT: 'M' or 'F')
  - acquisition_channel (TEXT: 'Organic', 'Paid Ads', 'Referral', 'Email', 'Social Media')

Table: orders
  - order_id (INTEGER, primary key)
  - customer_id (INTEGER, foreign key -> customers.customer_id)
  - order_date (TEXT, format YYYY-MM-DD)
  - order_value (REAL, total order value in Rs.)
  - discount_applied (INTEGER, 0 or 1)
  - payment_method (TEXT: 'Card', 'UPI', 'COD', 'Wallet')

Table: order_items
  - order_item_id (INTEGER, primary key)
  - order_id (INTEGER, foreign key -> orders.order_id)
  - category (TEXT: 'Electronics', 'Fashion', 'Home & Kitchen', 'Beauty', 'Sports', 'Books', 'Grocery', 'Toys')
  - quantity (INTEGER)
  - item_price (REAL)
"""

# Basic safety net: only allow read-only queries
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|ATTACH|REPLACE)\b",
    re.IGNORECASE,
)


class SQLAgentError(Exception):
    pass


def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SQLAgentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free key at https://aistudio.google.com, then run:\n"
            "  export GEMINI_API_KEY='your-key-here'   (Mac/Linux)\n"
            "  $env:GEMINI_API_KEY='your-key-here'      (Windows PowerShell)"
        )
    return genai.Client(api_key=api_key)


def generate_sql(question: str) -> str:
    """Ask Gemini to translate a natural language question into a SQL query."""
    client = get_client()
    prompt = f"""You are a SQL expert. Given this SQLite database schema:

{SCHEMA_DESCRIPTION}

Write a single SQLite query that answers this question:
"{question}"

Rules:
- Return ONLY the raw SQL query, no explanation, no markdown code fences, no backticks.
- Only use SELECT statements — never write/modify data.
- Use proper JOINs across tables where needed.
- Use SQLite-compatible date functions (e.g., strftime, date()) if date logic is needed.
- If the question is ambiguous, make a reasonable assumption and write the query anyway.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    sql = response.text.strip()
    # strip accidental markdown fences just in case
    sql = re.sub(r"^```(sql)?|```$", "", sql, flags=re.MULTILINE).strip()
    return sql


def validate_sql(sql: str) -> None:
    """Reject anything that isn't a read-only SELECT query."""
    if FORBIDDEN_KEYWORDS.search(sql):
        raise SQLAgentError(f"Generated query contains a forbidden write operation. Query was:\n{sql}")
    if not sql.strip().upper().startswith("SELECT"):
        raise SQLAgentError(f"Generated query is not a SELECT statement:\n{sql}")


def run_sql(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


def explain_result(question: str, sql: str, result_df: pd.DataFrame) -> str:
    """Ask Gemini to turn the raw query result into a plain-English answer."""
    client = get_client()
    preview = result_df.head(20).to_markdown(index=False) if not result_df.empty else "(no rows returned)"
    prompt = f"""The user asked: "{question}"

We ran this SQL query:
{sql}

It returned this result (showing up to 20 rows):
{preview}

Write a short, plain-English answer (2-4 sentences) for a business user.
Include the key number(s) directly. Do not mention SQL or the query itself.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def ask(question: str) -> dict:
    """Full pipeline: question -> SQL -> validated -> executed -> explained."""
    sql = generate_sql(question)
    validate_sql(sql)
    result_df = run_sql(sql)
    answer = explain_result(question, sql, result_df)
    return {"question": question, "sql": sql, "result": result_df, "answer": answer}


if __name__ == "__main__":
    # Quick CLI test
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "What is the total revenue from the Electronics category?"
    out = ask(q)
    print("Question:", out["question"])
    print("\nGenerated SQL:\n", out["sql"])
    print("\nResult:\n", out["result"])
    print("\nAnswer:\n", out["answer"])
