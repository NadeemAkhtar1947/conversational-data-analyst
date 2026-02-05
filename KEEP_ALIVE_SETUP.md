# Keep-Alive Setup for Render Free Tier

## Why Keep-Alive?
Render free tier sleeps after 15 minutes of inactivity. This causes:
- First request after sleep: 30-60 second cold start
- Poor user experience

**Solution:** Ping your app every 10 minutes to keep it awake.

---

## Option 1: Cron-Job.org (Recommended) ⭐

### Step 1: Create Account
1. Go to https://cron-job.org/en/
2. Click **"Sign up for free"**
3. Verify email

### Step 2: Add Cron Job
1. Click **"Create cronjob"**
2. Fill in:
   - **Title**: Keep Render App Awake
   - **Address**: `https://YOUR-APP.onrender.com/health`
   - **Schedule**: 
     - Every **10 minutes**
     - Or use: `*/10 * * * *` (cron expression)
   - **Enabled**: ✅ Yes
3. Click **"Create cronjob"**

### Step 3: Test
- Click **"Run now"** to test
- Check "Execution history" - should show 200 OK

**Done!** Your app will stay awake 24/7 🎉

---

## Option 2: UptimeRobot (Alternative)

### Step 1: Create Account
1. Go to https://uptimerobot.com
2. Sign up (free - monitors up to 50 sites)

### Step 2: Add Monitor
1. Click **"+ Add New Monitor"**
2. Settings:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Conversational Data Analyst
   - **URL**: `https://YOUR-APP.onrender.com/health`
   - **Monitoring Interval**: 5 minutes (free tier)
3. Click **"Create Monitor"**

**Bonus:** UptimeRobot also sends alerts if your app goes down!

---

## Option 3: GitHub Actions (For GitHub Users)

Create `.github/workflows/keep-alive.yml`:

```yaml
name: Keep Alive

on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
  workflow_dispatch:  # Manual trigger

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping app
        run: |
          curl -f https://YOUR-APP.onrender.com/health || exit 0
```

**Note:** GitHub Actions free tier has limited minutes - use cron-job.org instead for unlimited pings.

---

## Verification

### Check if it's working:
1. **Render Dashboard** → Your service → Logs
2. You should see health check requests every 10 minutes:
   ```
   GET /health 200 OK
   ```

### Test cold start elimination:
1. Don't use your app for 30 minutes
2. Visit your app URL
3. Should load instantly (no 30s wait) ✅

---

## Recommended Setup

**Use Cron-Job.org:**
- ✅ Free forever
- ✅ Unlimited executions
- ✅ Reliable (99.9% uptime)
- ✅ Email notifications on failure
- ✅ No credit card needed

**Schedule:** Every 10 minutes (144 pings/day)

---

## Important Notes

⚠️ **Render Free Tier Limit**: 750 hours/month
- With keep-alive: Uses ~720 hours/month
- Still within free limit! ✅

⚠️ **Don't over-ping**: 
- 10 minutes is optimal
- 5 minutes = unnecessary
- 15 minutes = might sleep

---

## After Setup

Your deployment will have:
1. ✅ Free hosting on Render
2. ✅ Always awake (no cold starts)
3. ✅ Free database on Neon
4. ✅ Free monitoring
5. ✅ $0 total cost forever

**Your app will load instantly 24/7!** 🚀
