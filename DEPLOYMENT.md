# 🚀 Deployment Guide: Conversational Analytics System

Complete step-by-step guide to deploy your production-grade AI analytics system.

---

## 📋 Prerequisites

Before deployment, ensure you have:

1. **Accounts**:
   - [HuggingFace](https://huggingface.co) account (free)
   - [Groq](https://console.groq.com) account (free API key)
   - [Neon](https://neon.tech) account (free PostgreSQL)

2. **Local Development** (optional):
   - Python 3.10+
   - Git
   - Docker (for local testing)

---

## 🗄️ Step 1: Setup PostgreSQL Database on Neon

### 1.1 Create Database

1. Go to [neon.tech](https://neon.tech) and sign up
2. Click **"Create a Project"**
3. Name: `analytics-db`
4. Region: Choose nearest to you
5. Click **"Create Project"**

### 1.2 Get Connection String

1. In your Neon dashboard, click **"Connection Details"**
2. Copy the connection string (PostgreSQL format):
   ```
   postgresql://user:password@ep-xxx.neon.tech:5432/dbname?sslmode=require
   ```
3. Save this for later

### 1.3 Load Superstore Dataset

**Option A: Using Neon SQL Editor**

1. Download the Superstore dataset CSV
2. In Neon dashboard, go to **"SQL Editor"**
3. Create the table:

```sql
CREATE TABLE superstore (
    row_id INTEGER PRIMARY KEY,
    order_id TEXT,
    order_date DATE,
    ship_date DATE,
    ship_mode TEXT,
    customer_id TEXT,
    customer_name TEXT,
    segment TEXT,
    country TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    region TEXT,
    product_id TEXT,
    category TEXT,
    sub_category TEXT,
    product_name TEXT,
    sales NUMERIC,
    quantity INTEGER,
    discount NUMERIC,
    profit NUMERIC
);
```

4. Import CSV data using Neon's import tool or:

```sql
COPY superstore FROM '/path/to/superstore.csv' 
WITH (FORMAT csv, HEADER true);
```

**Option B: Using Python Script**

```python
import pandas as pd
import asyncpg
import asyncio

async def load_data():
    conn = await asyncpg.connect('your_neon_connection_string')
    
    # Read CSV
    df = pd.read_csv('data.csv')
    
    # Insert data
    await conn.copy_records_to_table(
        'superstore',
        records=df.to_records(index=False),
        columns=df.columns.tolist()
    )
    
    await conn.close()
    print("Data loaded successfully!")

asyncio.run(load_data())
```

5. Verify data:
```sql
SELECT COUNT(*) FROM superstore;
-- Should return number of rows
```

---

## 🔑 Step 2: Get API Keys

### 2.1 Groq API Key (LLaMA-3.1-70B)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / Log in
3. Navigate to **API Keys**
4. Click **"Create API Key"**
5. Name: `analytics-assistant`
6. Copy the key (starts with `gsk_...`)
7. Save securely

### 2.2 HuggingFace Token (SQLCoder-7B)

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **"New token"**
3. Name: `analytics-sql-coder`
4. Type: **Read**
5. Click **"Generate"**
6. Copy the token (starts with `hf_...`)
7. Save securely

---

## 🐳 Step 3: Deploy to HuggingFace Spaces

### 3.1 Create New Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Fill in details:
   - **Space name**: `conversational-analytics`
   - **License**: MIT
   - **SDK**: Docker
   - **Visibility**: Public or Private
3. Click **"Create Space"**

### 3.2 Clone Repository Locally

```bash
# Clone your new Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/conversational-analytics
cd conversational-analytics

# Copy all project files
cp -r path/to/your/project/* .
```

### 3.3 Configure Environment Variables

In HuggingFace Spaces:

1. Go to your Space settings
2. Click **"Settings"** → **"Repository secrets"**
3. Add three secrets:

   **Secret 1: GROQ_API_KEY**
   - Name: `GROQ_API_KEY`
   - Value: Your Groq API key

   **Secret 2: HF_TOKEN**
   - Name: `HF_TOKEN`
   - Value: Your HuggingFace token

   **Secret 3: DATABASE_URL**
   - Name: `DATABASE_URL`
   - Value: Your Neon connection string

### 3.4 Push Code to Space

```bash
# Add all files
git add .

# Commit
git commit -m "Initial deployment"

# Push to HuggingFace
git push
```

### 3.5 Monitor Deployment

1. Go to your Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/conversational-analytics`
2. Watch the **"Logs"** tab
3. Wait for "Running on https://..." message
4. Click **"Open"** to access your app

---

## 🧪 Step 4: Test Your Deployment

### 4.1 Health Check

Visit: `https://YOUR_USERNAME-conversational-analytics.hf.space/health`

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T...",
  "database": true,
  "agents": {
    "context_rewriter": true,
    "sql_generator": true,
    "analysis": true,
    "visualization": true
  }
}
```

### 4.2 Test Queries

Try these sample questions in the UI:

1. **Simple Query**: "Total sales by region"
2. **Follow-up**: "What about last year?"
3. **Complex**: "Top 10 most profitable products"
4. **Trend**: "Monthly sales trend for 2023"

### 4.3 Verify Features

- ✅ Query executes successfully
- ✅ Data table displays
- ✅ Chart renders
- ✅ Business summary appears
- ✅ SQL is shown (collapsible)
- ✅ Confidence indicator visible
- ✅ Recent questions update

---

## 🔧 Step 5: Troubleshooting

### Issue: "Database connection failed"

**Solution:**
- Verify `DATABASE_URL` is correct in Secrets
- Check Neon database is running
- Ensure SSL mode is included: `?sslmode=require`

### Issue: "SQLCoder-7B model loading"

**Solution:**
- Wait 1-2 minutes for model to load on HF
- System will automatically fallback to Groq LLaMA-3
- Check HF_TOKEN is valid

### Issue: "Groq API error"

**Solution:**
- Verify GROQ_API_KEY is correct
- Check API quota at console.groq.com
- Ensure key has proper permissions

### Issue: "Application won't start"

**Solution:**
- Check Dockerfile syntax
- Review Space logs for errors
- Verify requirements.txt has all dependencies
- Ensure Python version is 3.10+

---

## 📊 Step 6: Monitor & Maintain

### 6.1 View Logs

```bash
# In HuggingFace Space interface, click "Logs" tab
# Monitor real-time application logs
```

### 6.2 Check Database Usage

```sql
-- Connect to Neon and run:
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename = 'superstore';
```

### 6.3 Monitor API Usage

- **Groq**: Visit [console.groq.com](https://console.groq.com) → Usage
- **HuggingFace**: Check Inference API limits in dashboard

---

## 🚀 Step 7: Optional Enhancements

### 7.1 Custom Domain (HF Spaces)

1. Go to Space Settings
2. Enable "Custom Domain"
3. Configure DNS records

### 7.2 Add Analytics

```javascript
// Add to static/index.html
<script async src="https://your-analytics.com/script.js"></script>
```

### 7.3 Enable Authentication

```python
# In backend/main.py, add authentication middleware
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/query")
async def process_query(request: QueryRequest, token: str = Depends(security)):
    # Validate token
    if not validate_token(token):
        raise HTTPException(status_code=401)
    # ... rest of code
```

### 7.4 Scale with Redis

```python
# Install: pip install redis
from redis import asyncio as aioredis

redis = await aioredis.from_url("redis://localhost")
```

---

## 📈 Performance Optimization

### Database Indexing

```sql
-- Add indexes for better query performance
CREATE INDEX idx_order_date ON superstore(order_date);
CREATE INDEX idx_region ON superstore(region);
CREATE INDEX idx_category ON superstore(category);
CREATE INDEX idx_customer_id ON superstore(customer_id);
```

### Connection Pooling

Already configured in `database.py`:
- Min connections: 1
- Max connections: 5
- Query timeout: 30s

### Caching (Future Enhancement)

```python
# Add Redis caching for frequent queries
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_query(sql: str):
    return await db.execute_query(sql)
```

---

## 🔒 Security Checklist

- ✅ Database uses read-only connection
- ✅ SQL validation blocks DML/DDL
- ✅ Environment variables in Secrets (not code)
- ✅ HTTPS enforced (HuggingFace default)
- ✅ Error messages sanitized
- ✅ Query timeouts enforced
- ✅ Rate limiting (consider adding)
- ✅ Input validation on all endpoints

---

## 📞 Support & Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [HuggingFace Spaces](https://huggingface.co/docs/hub/spaces)
- [Groq API](https://console.groq.com/docs)
- [Neon Docs](https://neon.tech/docs)

### Community
- HuggingFace Discord
- FastAPI Discord
- GitHub Issues

---

## ✅ Deployment Checklist

Before going live:

- [ ] Database loaded with data
- [ ] All environment variables set
- [ ] Health endpoint returns "healthy"
- [ ] Sample queries work
- [ ] Charts render correctly
- [ ] SQL validation tested
- [ ] Error handling tested
- [ ] Performance is acceptable (< 5s response)
- [ ] Logs are clean (no errors)
- [ ] README updated with your Space URL

---

## 🎉 Congratulations!

Your production-grade conversational analytics system is now live!

**Next Steps:**
1. Share your Space URL
2. Gather user feedback
3. Monitor usage patterns
4. Iterate and improve

**Your Space URL:**
```
https://huggingface.co/spaces/YOUR_USERNAME/conversational-analytics
```

---

## 📝 Quick Commands Reference

```bash
# Local development
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Docker local testing
docker build -t analytics-app .
docker run -p 7860:7860 --env-file .env analytics-app

# Git deployment to HF Spaces
git add .
git commit -m "Update"
git push

# Database backup (Neon)
pg_dump $DATABASE_URL > backup.sql
```

---

**Need Help?** Check logs, review error messages, and consult the Architecture documentation.
