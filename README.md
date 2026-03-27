# SQL Copilot 🚀

AI-powered application that converts natural language into SQL queries using LLMs.

## 🔹 Features
- Convert plain English questions into SQL queries
- Built with safety guardrails (SELECT-only queries)
- Simple and interactive UI using Streamlit
- Supports SQL Server database connections

## 🔹 Tech Stack
- Python
- Streamlit
- SQL Server (pyodbc)
- LLM API (Grok / OpenAI compatible)
- REST APIs

## 🔹 How It Works
1. User enters a question in plain English  
2. LLM converts it into SQL query  
3. Query is validated (no destructive operations allowed)  
4. Query is executed and results are shown  

## 🔹 Setup Instructions

```bash
pip install -r requirements.txt
streamlit run app.py
