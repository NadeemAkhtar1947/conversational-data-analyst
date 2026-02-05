# Deployment Guide - Render Free Tier

## Pre-Deployment Checklist

Files created:
- `render.yaml` - Render configuration
- `.renderignore` - Files to exclude from deployment
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (DO NOT commit this)

##  Deploy to Render (Free)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/NadeemAkhtar1947/conversational-data-analyst
git push -u origin main
```

### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (free, no credit card needed)
3. Authorize Render to access your repositories

### Step 3: Deploy
1. Click **"New +"** → **"Blueprint"**
2. Connect your GitHub repository
3. Render will detect `render.yaml` automatically
4. Click **"Apply"**

### Step 4: Set Environment Variable
1. Go to your service dashboard
2. Click **"Environment"** tab
3. Add: `DATABASE_URL` = `postgresql://neondb_owner:npg_PJ2gUXjqcQ4S@ep-bold-paper-a1q1nje6-pooler.ap-southeast-1.aws.neon.tech/neondb`
4. Click **"Save Changes"**

### Step 5: Wait for Deployment
- First deploy takes ~5-10 minutes
- Watch logs in the dashboard
- Once complete, you'll get a URL like: `https://conversational-data-analyst.onrender.com`

## ⚡ Important Notes

### Free Tier Limitations:
- **Sleeps after 15 min inactivity** → First request will take 30-60 seconds
- 512MB RAM (enough for your app)
- 750 hours/month compute time

### Keep It Awake:
Use a free cron service to ping every 10 minutes:
1. Go to https://cron-job.org (free)
2. Create account
3. Add cron job: `https://your-app.onrender.com/health` every 10 minutes

### Update Groq API Key:
In Render dashboard, add environment variable:
- `GROQ_API_KEY` = Your Groq API key (if not hardcoded)

## 🔧 Local Testing Before Deploy
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export DATABASE_URL="postgresql://neondb_owner:npg_PJ2gUXjqcQ4S@ep-bold-paper-a1q1nje6-pooler.ap-southeast-1.aws.neon.tech/neondb"

# Run locally
uvicorn backend.main:app --host 0.0.0.0 --port 7860

# Test at http://localhost:7860
```

## Post-Deployment

### Your Live URLs:
- **App**: `https://your-app.onrender.com`
- **Health Check**: `https://your-app.onrender.com/health`
- **API Docs**: `https://your-app.onrender.com/docs`

### Monitor:
- Check logs in Render dashboard
- Health status: Green = running, Orange = sleeping

## 🐛 Troubleshooting

### Deployment fails?
- Check logs in Render dashboard
- Verify `requirements.txt` includes all dependencies
- Ensure DATABASE_URL is set correctly

### App sleeps too much?
- Set up cron job to ping every 10 minutes
- Or upgrade to paid tier ($7/month for always-on)

### Database connection fails?
- Check Neon database is active
- Verify DATABASE_URL format
- Check Neon connection limits (free tier: 1 concurrent connection)

