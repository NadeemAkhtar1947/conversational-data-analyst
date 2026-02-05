# ⚡ Quick Start Guide

Get your Conversational Analytics system running in **15 minutes**!

---

## 🚀 Option 1: Deploy to HuggingFace Spaces (Recommended)

### Step 1: Get API Keys (5 minutes)

1. **Groq API Key**
   - Visit [console.groq.com](https://console.groq.com)
   - Sign up/Login → API Keys → Create → Copy

2. **HuggingFace Token**
   - Visit [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - New token → Read access → Generate → Copy

3. **Neon Database**
   - Visit [neon.tech](https://neon.tech)
   - Create Project → Copy connection string

### Step 2: Setup Database (5 minutes)

```sql
-- In Neon SQL Editor, create table:
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

-- Import your data.csv using Neon's import tool
```

### Step 3: Deploy to HuggingFace (5 minutes)

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Name: `conversational-analytics`
3. SDK: **Docker**
4. Create Space

5. Clone and push:
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/conversational-analytics
cd conversational-analytics
# Copy all project files here
git add .
git commit -m "Initial deployment"
git push
```

6. Add Secrets (Settings → Repository secrets):
   - `GROQ_API_KEY` = your_groq_key
   - `HF_TOKEN` = your_hf_token
   - `DATABASE_URL` = your_neon_url

7. Wait 2-3 minutes for build → Open Space!

**Done!** 🎉

---

## 💻 Option 2: Run Locally

### Step 1: Setup Environment

```bash
# Clone repository
git clone <your-repo-url>
cd "Conversational Data Analyst"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell (if you get execution policy error, see below):
venv\Scripts\activate

# Windows Command Prompt (alternative):
venv\Scripts\activate.bat

# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your keys:
# GROQ_API_KEY=gsk_...
# HF_TOKEN=hf_...
# DATABASE_URL=postgresql://...
```

### Step 3: Run Application

```bash
# Start server
uvicorn backend.main:app --reload --port 7860

# Open browser
# http://localhost:7860
```

**Done!** 🎉

---

## 🐳 Option 3: Docker

```bash
# Build image
docker build -t analytics-app .

# Run container
docker run -p 7860:7860 --env-file .env analytics-app

# Open browser
# http://localhost:7860
```

---

## ✅ Verify Installation

1. **Health Check**
   - Visit: `http://localhost:7860/health` or your Space URL + `/health`
   - Should see: `{"status": "healthy", "database": true, ...}`

2. **Try Sample Query**
   - Click "Total sales by region"
   - Should see: Data table + chart + insights
   - Response time: < 5 seconds

3. **Test Follow-up**
   - Type: "What about West region?"
   - Should see: Context indicator + filtered results

---

## 🎯 Sample Questions

**Start with these:**

1. "Total sales by region" ← Click this first!
2. "What about West region?" ← Test follow-up
3. "Top 10 most profitable products"
4. "Monthly sales trend for 2023"

---

## 🆘 Common Issues

### Issue: "Database connection failed"
**Fix**: Check DATABASE_URL in Secrets/Environment

### Issue: "SQLCoder model loading"
**Fix**: Wait 1-2 minutes, system will use fallback automatically

### Issue: "Port already in use"
**Fix**: Change port: `uvicorn backend.main:app --port 8000`

### Issue: "Module not found"
**Fix**: Activate venv and reinstall: `pip install -r requirements.txt`

### Issue: "Scripts cannot be loaded" (Windows PowerShell)
**Error**: `running scripts is disabled on this system`

**Fix Options**:

1. **Use Command Prompt instead**:
   ```cmd
   venv\Scripts\activate.bat
   ```

2. **Bypass policy for current session**:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   venv\Scripts\activate
   ```

3. **Change user policy** (recommended):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   venv\Scripts\activate
   ```

---

## 📚 Next Steps

1. ✅ Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. ✅ Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment
3. ✅ Review [RESUME_INTERVIEW_GUIDE.md](RESUME_INTERVIEW_GUIDE.md) for career materials
4. ✅ Explore the code in `backend/` folder

---

## 🎉 You're All Set!

Your production-grade conversational analytics system is running!

**Share your deployment:**
- Tweet your HuggingFace Space URL
- Add to your portfolio
- Show in interviews

**Need help?** Check the documentation or open an issue.

---

**Happy Analyzing! 📊🤖**
