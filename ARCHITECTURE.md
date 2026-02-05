# 🏗️ System Architecture: Conversational Multi-Agent AI Analytics System

## Overview

A production-grade, context-aware conversational analytics system that transforms natural language queries into SQL, executes them safely against a PostgreSQL database, and returns insights with visualizations.

---

## 🧩 Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Query                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              NLP Preprocessing Pipeline                      │
│  • Spelling & Grammar Correction                             │
│  • Business Term Normalization (revenue→sales)               │
│  • Intent Classification                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          AGENT 1: Context Rewriter Agent                     │
│          Model: Groq LLaMA-3.1-70B                           │
│  • Converts follow-up questions into standalone queries      │
│  • Uses session context (last 3-5 turns)                     │
│  • Handles: "What about last year?", "Only West region"      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          AGENT 2: SQL Generation Agent                       │
│          Model: SQLCoder-7B (HF Inference API)               │
│          Fallback: Groq LLaMA-3 with SQL prompt              │
│  • Generates SELECT queries only                             │
│  • Context: Full schema + sample rows                        │
│  • Strict output: JSON with "sql" field                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          SQL Validation Layer (Non-LLM)                      │
│  • Whitelist: SELECT only                                    │
│  • Block: INSERT, UPDATE, DELETE, DROP, ALTER                │
│  • Table whitelist enforcement                               │
│  • Auto-inject LIMIT if missing                              │
│  • SQL injection pattern detection                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          PostgreSQL Execution (Neon Cloud)                   │
│  • Read-only connection                                      │
│  • Timeout: 30 seconds                                       │
│  • Returns: JSON rows                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
           ┌───────────────┴────────────────┐
           │                                 │
           ▼                                 ▼
┌──────────────────────┐        ┌──────────────────────┐
│  AGENT 3:            │        │  AGENT 4:            │
│  Analysis Agent      │        │  Visualization Agent │
│  Model: Groq LLaMA-3 │        │  Model: Groq LLaMA-3 │
│                      │        │                      │
│  • Business summary  │        │  • Chart type        │
│  • Key insights      │        │  • X/Y axis mapping  │
│  • Plain English     │        │  • bar/line/table    │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Unified Response                          │
│  {                                                           │
│    "rewritten_question": "...",                              │
│    "sql": "...",                                             │
│    "data": [...],                                            │
│    "summary": "...",                                         │
│    "insights": [...],                                        │
│    "chart": {...},                                           │
│    "confidence": "high"                                      │
│  }                                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Frontend UI                               │
│  • Table rendering                                           │
│  • Chart.js visualization                                    │
│  • Business summary display                                  │
│  • SQL transparency (collapsible)                            │
│  • Session memory (recent questions)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security & Safety Layers

### Layer 1: Input Validation
- Intent classification (reject non-analytics queries)
- Question length limits
- Rate limiting (per session)

### Layer 2: SQL Safety
- Regex-based SQL keyword blocking
- AST parsing for query validation
- Read-only database connection
- Query timeout enforcement

### Layer 3: Output Sanitization
- No raw error messages exposed
- Data size limits (max 1000 rows)
- Sensitive data masking (if needed)

---

## 💾 Session Context Management

```python
SessionContext = {
    "session_id": "uuid",
    "history": [
        {
            "question": "Total sales by region",
            "rewritten": "Total sales by region",
            "sql": "SELECT region, SUM(sales)...",
            "intent": "sales",
            "timestamp": "2026-01-30T12:00:00"
        }
    ],
    "last_intent": "sales",
    "last_columns": ["region", "sales"]
}
```

- **Stored**: In-memory (Redis optional for scale)
- **TTL**: 1 hour
- **Size**: Last 5 queries max

---

## 🧠 Agent Prompt Engineering

### Agent 1: Context Rewriter Prompt Template
```
You are a context rewriter for a business analytics system.

Previous context:
{history}

Current follow-up question: {question}

Rewrite this into a standalone question that can be understood without context.
Rules:
- Preserve all business terms
- Infer missing details from history
- If context is insufficient, return the original question
- Output JSON only: {"rewritten_question": "..."}
```

### Agent 2: SQL Generation Prompt Template
```
You are an expert PostgreSQL SQL generator for business analytics.

Database schema:
Table: superstore
Columns: {schema_info}

Sample rows:
{sample_data}

User question: {question}

Generate a SELECT query.
Rules:
- ONLY SELECT statements
- Use aggregation when needed (SUM, AVG, COUNT)
- Add LIMIT 100 for large results
- Use proper date functions for time queries
- Output JSON only: {"sql": "SELECT ..."}
```

### Agent 3: Analysis Prompt Template
```
You are a business analyst explaining SQL query results.

Question: {question}
SQL Query: {sql}
Results: {data}

Provide:
1. A 2-sentence business summary
2. 2-3 key insights

Output JSON:
{
  "summary": "...",
  "insights": ["...", "..."]
}
```

### Agent 4: Visualization Prompt Template
```
You are a data visualization expert.

Question: {question}
Columns: {columns}
Data sample: {sample}

Choose the best chart type and axes.

Output JSON:
{
  "chart_type": "bar" | "line" | "table",
  "x_axis": "column_name",
  "y_axis": "column_name"
}
```

---

## 📊 Data Flow Sequence

1. **User Input**: "What about last year?"
2. **NLP Pipeline**: Normalize, check intent
3. **Context Rewriter**: → "Total sales for 2025"
4. **SQL Agent**: → `SELECT SUM(sales) FROM superstore WHERE EXTRACT(YEAR FROM order_date) = 2025`
5. **Validator**: ✅ Pass (SELECT only, valid table)
6. **Execute**: PostgreSQL returns `[{"sum": 125000}]`
7. **Analysis Agent**: → "Sales in 2025 totaled $125K, down 10% from previous year"
8. **Viz Agent**: → `{"chart_type": "table", ...}`
9. **Response**: JSON to frontend
10. **Update Context**: Store in session

---

## 🌐 API Design

### Endpoint: `POST /query`

**Request:**
```json
{
  "question": "Total sales by region",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "rewritten_question": "Total sales by region",
    "sql": "SELECT region, SUM(sales) AS total_sales FROM superstore GROUP BY region ORDER BY total_sales DESC",
    "data": [
      {"region": "West", "total_sales": 725458.0},
      {"region": "East", "total_sales": 678781.2}
    ],
    "summary": "The West region leads with $725K in total sales, followed by East at $679K.",
    "insights": [
      "West region accounts for 35% of total sales",
      "East and Central regions show similar performance"
    ],
    "chart": {
      "type": "bar",
      "x_axis": "region",
      "y_axis": "total_sales"
    },
    "confidence": "high",
    "metadata": {
      "execution_time": 0.45,
      "row_count": 4
    }
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "message": "I couldn't understand that question. Try asking about sales, profit, customers, or time trends.",
    "code": "INVALID_INTENT",
    "suggestions": [
      "Total sales by category",
      "Most profitable products"
    ]
  }
}
```

---

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────┐
│   Hugging Face Spaces (Docker)      │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  FastAPI Backend            │  │
│   │  - Agent orchestration      │  │
│   │  - API endpoints            │  │
│   │  - Static file serving      │  │
│   └─────────────────────────────┘  │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  Frontend (served by FastAPI)│ │
│   │  - HTML + JS + Tailwind     │  │
│   │  - Chart.js                 │  │
│   └─────────────────────────────┘  │
└─────────────┬───────────────────────┘
              │
              │ HTTPS
              ▼
┌─────────────────────────────────────┐
│  External Services                  │
│  - Groq API (LLaMA-3)               │
│  - HF Inference (SQLCoder-7B)       │
│  - Neon PostgreSQL                  │
└─────────────────────────────────────┘
```

**Environment Variables:**
- `GROQ_API_KEY`
- `HF_TOKEN`
- `DATABASE_URL`

---

## 📈 Performance Considerations

- **Response Time Target**: < 3 seconds
- **Caching**: Schema metadata cached in-memory
- **Async**: All LLM calls use async/await
- **Timeout**: 30s per query
- **Connection Pool**: PostgreSQL (min=1, max=5)

---

## 🧪 Testing Strategy

1. **Unit Tests**: Each agent independently
2. **Integration Tests**: Full pipeline
3. **Safety Tests**: SQL injection attempts
4. **UX Tests**: Context resolution accuracy
5. **Load Tests**: 10 concurrent users

---

## 🎯 Success Metrics

- Query success rate: > 90%
- SQL safety: 100% (no unsafe queries executed)
- User satisfaction: Context resolution accuracy > 85%
- Response time: P95 < 5s

---

This architecture balances production-grade reliability, security, and user experience while using only free-tier services.
