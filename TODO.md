# Project To-Do List

> Checklist for the OptiMUS + OptiMind + LLM Judge + Frontend project.  
> Assign each phase to a person. Check items off as you go.

---

## Phase 1 — Get OptiMind Working (Person A, ~3 h)

### 1.1 Provision a GPU Server
- [ ] Create account on RunPod (or Lambda / Vast.ai)
- [ ] Deploy a pod: A100 40 GB, PyTorch 2.x template, Ubuntu 22.04
- [ ] SSH into the pod
- [ ] Record public IP and exposed port

### 1.2 Install & Launch SGLang + OptiMind
- [ ] `pip install "sglang[all]>=0.4.5"` + flashinfer wheels
- [ ] `pip install gurobipy`
- [ ] Launch SGLang server with `microsoft/OptiMind-SFT`
- [ ] Wait for model download (~28 GB, 10–15 min)
- [ ] Confirm server ready ("fired up and ready to roll")
- [ ] Verify from MacBook: `curl http://<IP>:30000/v1/models`

### 1.3 Update `run_optimind.py` for Remote Server
- [ ] Add `--server-url` CLI argument
- [ ] Add connection error handling
- [ ] Add configurable timeout (30–60 s)
- [ ] Add automatic code execution + result capture
- [ ] Test locally pointing at the remote server

### 1.4 End-to-End Testing
- [ ] Run OptiMind on `example_problem`
- [ ] Verify generated Gurobi code is valid
- [ ] Execute generated code locally (check Gurobi license)
- [ ] Compare output with OptiMUS result (manual)
- [ ] Test on 2–3 additional problems

### 1.5 Secure the Connection
- [ ] Choose method: SSH tunnel / RunPod proxy / nginx
- [ ] Set up the chosen mechanism
- [ ] Verify connection through secure channel
- [ ] Document connection details for Person B

---

## Phase 2 — Backend API + LLM Judge (Person B, ~3.5 h)

### 2.1 Scaffold FastAPI Backend
- [ ] Create `backend/` directory structure
- [ ] Set up FastAPI app with CORS middleware
- [ ] Define Pydantic request/response schemas
- [ ] Create `POST /api/problems` endpoint (stub)
- [ ] Create `GET /api/problems/{id}/status` endpoint (stub)
- [ ] Create `GET /api/problems/{id}/results` endpoint (stub)
- [ ] Write `backend/requirements.txt`
- [ ] Share OpenAPI spec / API contract with Person C

### 2.2 Wrap OptiMUS as a Service
- [ ] Create `backend/services/optimus.py`
- [ ] Create temp problem dir from API input
- [ ] Write `desc.txt`, `params.json`, `labels.json` to temp dir
- [ ] Call OptiMUS pipeline steps programmatically
- [ ] Parse and return structured results (formulation, code, output, objective value)
- [ ] Handle errors and timeouts

### 2.3 Wrap OptiMind as a Service
- [ ] Create `backend/services/optimind.py`
- [ ] Reuse prompt formatting from `run_optimind.py`
- [ ] Call remote SGLang server (URL from Person A)
- [ ] Extract code blocks from model response
- [ ] Execute Gurobi code locally
- [ ] Return structured results (response, code, output, objective value)

### 2.4 Build the LLM Judge
- [ ] Create `backend/services/judge.py`
- [ ] Design judge prompt evaluating: correctness, feasibility, optimality, completeness, code quality
- [ ] Implement Claude API call (Sonnet recommended)
- [ ] Parse structured judge output (winner, confidence, reasoning, scores)
- [ ] Handle edge case: one agent fails → other wins
- [ ] Handle edge case: both fail → report failure
- [ ] Handle edge case: close objective values → use formulation quality tiebreaker
- [ ] Test judge with at least 2 real problem pairs

### 2.5 Orchestrate Parallel Execution
- [ ] Create `backend/services/orchestrator.py`
- [ ] Run OptiMUS and OptiMind in parallel (`asyncio.gather`)
- [ ] Feed both results into the judge
- [ ] Add status tracking per `problem_id` (in-memory dict or Redis)
- [ ] Wire orchestrator into the real API endpoints (replace stubs)
- [ ] Test full flow: submit problem → poll status → get results

### 2.6 Plain-Language Output Generator
- [ ] Design explanation prompt for Claude
- [ ] Generate: non-technical summary, bullet-point recommendations, sensitivity insights
- [ ] Integrate as final step in orchestrator
- [ ] Test output quality on 2–3 problems

---

## Phase 3 — Next.js Frontend (Person C, ~3 h)

### 3.1 Scaffold the App
- [ ] `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir`
- [ ] Install dependencies: `axios`, `framer-motion`, `lucide-react`
- [ ] Set up API client utility (base URL from env var)
- [ ] Create layout component (nav, footer)

### 3.2 Problem Input Page (`/`)
- [ ] Build text area for problem description
- [ ] Build parameter entry form (name, type, shape, value)
- [ ] Build data upload component (drag-and-drop CSV/JSON)
- [ ] Add problem type selector (maximize / minimize)
- [ ] Add example problem templates (click to pre-fill)
- [ ] Add form validation
- [ ] Wire "Solve" button to `POST /api/problems`
- [ ] Redirect to progress page on success

### 3.3 Progress Page (`/problems/[id]`)
- [ ] Build stepper / timeline UI component
- [ ] Implement polling (`GET /api/problems/{id}/status` every 2–3 s)
- [ ] Show intermediate outputs (parameter extraction, formulations)
- [ ] Display estimated time remaining
- [ ] Auto-redirect to results when complete
- [ ] Handle error / timeout states

### 3.4 Results Page (`/problems/[id]/results`)
- [ ] Build winner banner with confidence score
- [ ] Build collapsible judge reasoning card
- [ ] Build plain-language explanation section
- [ ] Build key recommendations cards
- [ ] Build side-by-side comparison (collapsible)
  - [ ] Formulation comparison
  - [ ] Code comparison with syntax highlighting
  - [ ] Objective value comparison
  - [ ] Per-criterion score visualization
- [ ] Build avatar video section (with text fallback)
- [ ] Test with mock data first, then real backend

### 3.5 HeyGen Avatar Integration (Optional)
- [ ] Set up HeyGen API client
- [ ] Send plain-language explanation as avatar script
- [ ] Poll for video generation completion
- [ ] Embed video player in results page
- [ ] Graceful fallback if API unavailable

---

## Phase 4 — Integration & Deployment (Person D / shared, ~1.5 h)

### 4.1 Wire Frontend ↔ Backend
- [ ] Configure CORS in FastAPI for frontend origin
- [ ] Set `NEXT_PUBLIC_API_URL` in frontend env
- [ ] Test full end-to-end flow
- [ ] Handle error states (server down, timeout, license issues)

### 4.2 Dockerize
- [ ] Write `backend/Dockerfile`
- [ ] Write `frontend/Dockerfile`
- [ ] Write `docker-compose.yml` (backend + frontend)
- [ ] Test `docker compose up` locally
- [ ] Document all required environment variables

### 4.3 Deploy
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway / Render / Fly.io
- [ ] Configure env vars in all environments
- [ ] Set up Gurobi WLS license (if deploying to cloud)
- [ ] Verify GPU server accessible from deployed backend
- [ ] Smoke-test full deployed pipeline end-to-end

---

## Quick Reference: Environment Variables

```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GROQ_API_KEY=...
OPTIMIND_SERVER_URL=http://<gpu-server>:30000/v1
GUROBI_LICENSE=...           # or WLS config for cloud
HEYGEN_API_KEY=...           # optional
NEXT_PUBLIC_API_URL=...      # frontend → backend
```
