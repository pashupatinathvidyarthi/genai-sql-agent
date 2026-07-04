# GenAI Text-to-SQL Agent for E-Commerce Data

A natural-language interface over an e-commerce database — ask a business question in plain English, get a data-backed answer, with the SQL shown for transparency.

This project directly targets the JD's callout: *"Exposure to GenAI concepts and agent-based systems, along with an interest in applying them to real-world problems."* Most fresher candidates won't have anything like this — it's a genuine differentiator, and it's also more relevant to an Analyst role than a generic RAG-over-PDFs demo, since it works over structured business data.

## Why text-to-SQL instead of classic RAG?

Classic RAG (retrieval-augmented generation) is built for unstructured documents — PDFs, wikis, articles. This dataset is tabular (customers, orders, order items), so the right approach is **text-to-SQL**: the LLM writes a query against the actual schema, the query runs against real data, and the answer is grounded in exact numbers rather than approximate retrieval. This is also the pattern real BI/analytics teams are adopting (e.g., "chat with your data" features in Tableau, Power BI Copilot, etc.) — so it's a more credible, job-relevant demo.

## Architecture

```
User question (plain English)
        |
        v
  [Gemini] generates SQL query from schema + question
        |
        v
  Safety check (blocks any non-SELECT / write operations)
        |
        v
  SQLite database executes the query
        |
        v
  [Gemini] converts raw result -> plain-English answer
        |
        v
  Answer + SQL shown to user (Streamlit UI)
```

## Project Structure

```
genai_sql_agent/
├── ecommerce.db      # SQLite database (built from the same e-commerce dataset as Project 1)
├── agent.py           # Core logic: generate_sql -> validate_sql -> run_sql -> explain_result
├── app.py             # Streamlit UI wrapper
└── README.md
```

## Setup & Run

```bash
pip install -r requirements.txt

# Get a free API key (no credit card required) at https://aistudio.google.com
export GEMINI_API_KEY="your-key-here"        # Mac/Linux
# $env:GEMINI_API_KEY="your-key-here"        # Windows PowerShell

streamlit run app.py
```

This opens a browser UI where you can type questions like:
- "What is the total revenue by product category?"
- "Which city has the most customers?"
- "What is the average order value for customers who used a discount?"
- "What is the monthly revenue trend for 2025?"

You can also test the agent directly from the command line without the UI:

```bash
python agent.py "Which payment method is used most often?"
```

## Safety Design (worth mentioning in interviews)

The agent only ever executes `SELECT` statements. Before running any generated SQL, `validate_sql()` checks for and rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `ATTACH`, and `REPLACE` keywords — so even if the model were prompted adversarially to generate a destructive query, it would be blocked before touching the database. This is a basic but important guardrail for any agent that's allowed to interact with real data.

## Database Schema

| Table | Key columns |
|---|---|
| `customers` | customer_id, signup_date, city, age, gender, acquisition_channel |
| `orders` | order_id, customer_id, order_date, order_value, discount_applied, payment_method |
| `order_items` | order_item_id, order_id, category, quantity, item_price |

(Same schema as the dataset used in the ML case study project — the two projects are designed to be presented together as "I analyzed this data with traditional ML, then built a GenAI interface on top of it.")

