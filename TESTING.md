# Testing Guide

## Running Tests Locally

### Setup Test Environment

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Create test environment file
cp .env.example .env.test
```

### Unit Tests

```bash
# Test individual agents
python backend/agents/context_rewriter.py
python backend/agents/sql_generator.py
python backend/agents/analysis_agent.py
python backend/agents/visualization_agent.py

# Test SQL validator
python backend/utils/sql_validator.py
```

### Integration Tests

```bash
# Run full test suite (coming soon)
pytest tests/ -v --cov=backend

# Test specific module
pytest tests/test_agents.py -v

# Test with coverage
pytest --cov=backend --cov-report=html
```

### Manual Testing

```bash
# Start server locally
uvicorn backend.main:app --reload --port 7860

# Test endpoints
curl http://localhost:7860/health
curl -X POST http://localhost:7860/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Total sales by region"}'
```

---

## Test Cases

### SQL Validation Tests

1. **Valid SELECT**:  Should pass
2. **Invalid UPDATE**:  Should block
3. **SQL Injection**:  Should block
4. **Invalid table**:  Should block
5. **Auto LIMIT**:  Should add LIMIT

### Agent Tests

1. **Context Rewriter**: Follow-up question → Standalone
2. **SQL Generator**: Natural language → SQL
3. **Analysis Agent**: Data → Business insights
4. **Visualization Agent**: Data → Chart type

### End-to-End Tests

1. Simple query workflow
2. Follow-up query with context
3. Error handling
4. Empty results handling

---

## Performance Benchmarks

- Query latency: < 3s average
- Database queries: < 500ms
- LLM calls: < 2s
- Frontend render: < 100ms
