# OptiMATE Deployment Guide

## 🎯 Overview

This guide covers deploying OptiMATE to **Render** (recommended) and **Vercel** (frontend only).

### Quick Architecture Summary

- **Frontend**: Next.js app (API routes call Python backend)
- **Backend**: Python pipeline (5-15 min optimization cycles)
- **Dependencies**: Gurobi, OpenAI, Anthropic, OptiMind server, HeyGen
- **Storage**: File-based communication (`current_query/`, `data_upload/`)

---

## 🚀 Option 1: Full Stack on Render (RECOMMENDED)

### Why Render?

✅ Supports both Python and Node.js
✅ No timeout limits (critical for 15-min processes)
✅ Persistent disk for file storage
✅ Simple deployment
✅ Free tier available ($7/mo recommended for disk)

### Prerequisites

1. GitHub repository pushed
2. [Render account](https://render.com) created
3. API keys ready:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `GRB_WLSACCESSID`, `GRB_WLSSECRET`, `GRB_LICENSEID` (Gurobi WLS)
   - `OPTIMIND_SERVER_URL`
   - `NEXT_PUBLIC_HEYGEN_API_KEY`

### Deployment Steps

#### Step 1: Push to GitHub

```bash
cd /home/mildness/Documents/treehacks/OptiMax
git add .
git commit -m "Prepare for Render deployment"
git push origin master
```

#### Step 2: Create Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `optimate`
   - **Region**: Oregon (US West) - lowest latency
   - **Branch**: `master` or `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     cd backend && pip install -r requirements.txt && cd ../frontend && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs && npm install && npm run build
     ```
   - **Start Command**:
     ```bash
     cd frontend && npm start
     ```
   - **Plan**: Select **Starter** ($7/month) for persistent disk

#### Step 3: Add Environment Variables

In Render dashboard → Environment:

**Backend Python:**

- `OPENAI_API_KEY` = `your-key`
- `ANTHROPIC_API_KEY` = `your-key`
- `OPTIMIND_SERVER_URL` = `http://your-vm-ip/v1`

**Gurobi (Cloud License):**

- `GRB_WLSACCESSID` = `your-access-id`
- `GRB_WLSSECRET` = `your-secret`
- `GRB_LICENSEID` = `your-license-id`

**Frontend:**

- `NEXT_PUBLIC_HEYGEN_API_KEY` = `your-key`
- `NODE_ENV` = `production`

#### Step 4: Add Persistent Disk (IMPORTANT!)

1. In service settings → **Disks**
2. Click **Add Disk**
3. Configure:
   - **Name**: `optimate-data`
   - **Mount Path**: `/opt/render/project/src/backend`
   - **Size**: 10 GB
4. This ensures `current_query/` and file storage persists

#### Step 5: Deploy

1. Click **Create Web Service**
2. Wait 5-10 minutes for build
3. Monitor logs for errors
4. Once deployed, test at `https://optimate.onrender.com`

### Troubleshooting Render

**Build fails:**

- Check build logs for Python/Node errors
- Ensure all requirements.txt packages install
- Verify Gurobi license keys are correct

**App crashes on startup:**

- Check runtime logs
- Verify frontend `.next/` folder was built
- Test `npm start` works locally

**Optimization times out:**

- Render Starter plan has no timeout (unlike serverless)
- Check Python subprocess logs
- Verify Gurobi WLS license is active

---

## ⚡ Option 2: Hybrid - Vercel (Frontend) + Render (Backend API)

### Why Hybrid?

- Showcase both platforms for sponsors
- Faster frontend deployment on Vercel's CDN
- More complex but educational

### Architecture Changes Needed

This approach requires **refactoring** to separate frontend and backend:

#### Current (Monolithic):

```
Frontend Next.js → child_process.exec('python main.py') → File system
```

#### New (Microservices):

```
Frontend (Vercel) → HTTP API → Backend Flask/FastAPI (Render) → File system
```

### Step-by-Step Hybrid Deployment

#### Part A: Deploy Backend API to Render

##### 1. Create Flask API Wrapper

Create `backend/api.py`:

```python
from flask import Flask, request, jsonify
from query_manager import setup_workspace
import subprocess
import os

app = Flask(__name__)

@app.route('/api/optimize', methods=['POST'])
def optimize():
    # Get uploaded files and problem description
    data = request.json
    problem_desc = data.get('description')

    # Setup workspace
    workspace_id = setup_workspace()

    # Write inputs to current_query/
    with open(f'current_query/raw_input/desc.txt', 'w') as f:
        f.write(problem_desc)

    # Run main.py asynchronously (use Celery/RQ for production)
    result = subprocess.run(['python', 'main.py'],
                          capture_output=True,
                          text=True,
                          timeout=900)  # 15 min timeout

    # Read results
    with open('current_query/final_output/report.md') as f:
        report = f.read()

    return jsonify({
        'workspace_id': workspace_id,
        'report': report,
        'status': 'completed'
    })

@app.route('/api/status/<workspace_id>', methods=['GET'])
def get_status(workspace_id):
    # Check if optimization is complete
    # Return progress percentage
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
```

##### 2. Update requirements.txt:

```
flask==3.0.0
flask-cors==4.0.0
gunicorn==21.2.0
```

##### 3. Deploy Backend to Render:

- Create Python web service
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn api:app`
- Add persistent disk
- Note the service URL: `https://optimate-backend.onrender.com`

#### Part B: Deploy Frontend to Vercel

##### 1. Update Frontend API Calls

In `frontend/lib/utils/python-runner.ts`:

```typescript
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export async function runMainPipeline(): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description: problemText }),
  });

  const data = await response.json();
  return data;
}
```

##### 2. Create `vercel.json` in frontend/:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "env": {
    "NEXT_PUBLIC_BACKEND_URL": "https://optimate-backend.onrender.com",
    "NEXT_PUBLIC_HEYGEN_API_KEY": "@heygen-api-key"
  }
}
```

##### 3. Deploy to Vercel:

```bash
cd frontend
npx vercel --prod
```

### Hybrid Deployment Notes

**Pros:**

- Frontend on global CDN (fast)
- Backend can handle long processes
- Clean separation of concerns

**Cons:**

- More complex setup
- Need to refactor API communication
- CORS configuration required
- Two services to manage

---

## 🎯 Recommended Approach for Hackathon

**Use Option 1 (Full Render)** because:

1. Works with zero code changes
2. No refactoring needed
3. Reliable for 15-min processes
4. Single deployment to manage
5. You can still get Render sponsorship credit

**Only use Option 2 (Hybrid)** if:

- Judges specifically want to see both platforms
- You have time to refactor communication layer
- You want to showcase microservices architecture

---

## 📊 Testing Checklist

After deployment, test these flows:

### Frontend Tests:

- [ ] Landing page loads
- [ ] Dark/light mode works
- [ ] Input form submits
- [ ] Example problems load

### Backend Tests:

- [ ] Optimization runs without timeout
- [ ] Progress bar updates correctly
- [ ] Results page shows charts
- [ ] PDF download works
- [ ] HeyGen video generates

### API Tests:

- [ ] All environment variables loaded
- [ ] Gurobi license activates
- [ ] OptiMind server reachable
- [ ] File I/O works on persistent disk

---

## 🚨 Common Issues & Fixes

### Issue: "Gurobi license error"

**Fix**: Verify WLS environment variables are set correctly. Test locally first:

```python
import gurobipy as gp
env = gp.Env(empty=True)
env.start()  # Should not error
```

### Issue: "Module not found"

**Fix**: Ensure all dependencies in requirements.txt. Add missing:

```bash
pip freeze > requirements.txt
```

### Issue: "Permission denied writing files"

**Fix**: Check disk is mounted at correct path. Verify with:

```bash
ls -la /opt/render/project/src/backend/current_query
```

### Issue: "Process killed / OOM"

**Fix**: Upgrade Render plan (Standard provides 2GB RAM, enough for Gurobi)

### Issue: "Frontend can't find backend"

**Fix**: Verify backend path resolution:

```typescript
// In python-runner.ts, log the path:
console.log("Backend path:", getBackendPath());
```

---

## 💰 Sponsorship Credits

### Render:

- Email sponsor contact during hackathon
- Mention you deployed on Render
- Share your project URL
- Screenshot of Render dashboard

### Vercel (if using Option 2):

- Deploy with Pro trial (no credit card for hackathon)
- Use `npx vercel --prod` for proper deployment
- Share Vercel deployment URL

---

## 📞 Support

**Render Issues**: https://render.com/docs/troubleshooting
**Vercel Issues**: https://vercel.com/support
**Gurobi Licensing**: https://support.gurobi.com

---

## ✅ Pre-Deployment Checklist

- [ ] All API keys in .env.local (local testing)
- [ ] Git repository up to date
- [ ] `.gitignore` excludes sensitive files
- [ ] `requirements.txt` has all Python deps
- [ ] `package.json` has all Node deps
- [ ] Gurobi WLS license tested locally
- [ ] OptiMind server URL confirmed working
- [ ] HeyGen API key validated
- [ ] Build passes locally (`npm run build`)
- [ ] Python pipeline runs locally (`python main.py`)

---

## 🎉 Post-Deployment

Once deployed, share these links:

1. **Live App URL**: `https://optimate.onrender.com` or `https://optimate.vercel.app`
2. **GitHub Repo**: Your repository link
3. **Demo Video**: Record 2-min demo showing optimization workflow
4. **Sponsor Form**: Submit deployment screenshots for credits

Good luck at TreeHacks 2026! 🌳⚡
