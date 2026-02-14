# OptiMUS + OptiMind + LLM Judge + Frontend — Project Plan

**Team:** 3–4 people, ~10 hours of AI-assisted coding  
**Date:** February 14, 2026  
**Current state:** OptiMUS pipeline works end-to-end via CLI. `run_optimind.py` exists but needs a GPU server. No backend API, no frontend, no judge logic.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js Frontend (UI)                  │
│  Problem Input → Progress Dashboard → Results + Avatar   │
└──────────────────────┬──────────────────────────────────┘
                       │  REST API / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│              FastAPI Backend (your MacBook)               │
│                                                          │
│  ┌─────────┐   ┌──────────┐   ┌──────────────────────┐  │
│  │ OptiMUS  │   │ OptiMind │   │   LLM Judge (Claude) │  │
│  │ Pipeline │   │  Client  │   │   Compare & Select   │  │
│  │ (local)  │   │ (remote) │   │                      │  │
│  └────┬─────┘   └────┬─────┘   └──────────┬───────────┘  │
│       │              │                     │              │
│       │              │    ┌────────────────┘              │
│       ▼              ▼    ▼                               │
│   [results A]   [results B] → Best Solution → HeyGen     │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS (OpenAI-compatible API)
┌──────────────────────▼──────────────────────────────────┐
│        Remote GPU Server (RunPod / Lambda / Vast.ai)     │
│                                                          │
│  SGLang Server + microsoft/OptiMind-SFT                  │
│  Exposed on port 30000, OpenAI-compatible /v1 endpoint   │
└─────────────────────────────────────────────────────────┘
```

---

## Work Assignment Summary

| Person | Phase | Hours | Key Deliverables |
|--------|-------|-------|------------------|
| **A** | Phase 1: OptiMind on GPU | ~3h | Working remote GPU server, tested OptiMind client |
| **B** | Phase 2: Backend API + Judge | ~3.5h | FastAPI API, judge logic, orchestrator |
| **C** | Phase 3: Next.js Frontend | ~3h | Input page, progress view, results page |
| **D** (or shared) | Phase 4: Integration & Deploy | ~1.5h | Docker, deployment, end-to-end testing |

> Persons A, B, and C can start in parallel. A gives B the server URL once live. B and C agree on API contract up front. Phase 4 begins once A+B+C converge.

---

## Phase 1 — Get OptiMind Working on a Remote GPU (Person A, ~3 h)

### 1.1 Provision a GPU Server (~30 min)

**Recommended:** [RunPod](https://runpod.io) (~$0.50–0.75/hr for an A100 40 GB).

| Provider | GPU | $/hr | Setup Ease |
|----------|-----|------|------------|
| RunPod | A100 40 GB | ~$0.74 | Very easy (templates) |
| Lambda Cloud | A100 40 GB | ~$1.10 | Easy |
| Vast.ai | A100 40 GB | ~$0.50 | Medium |
| Modal | A100 40 GB | ~$0.60 | Easy (serverless) |

**Minimum specs:**
- 1× NVIDIA A100 40 GB (OptiMind-SFT is ~14 GB FP16; 24 GB is tight, 40 GB is safe)
- 32 GB RAM, 50 GB disk
- Ubuntu 22.04, Python 3.12+

**Steps:**
- [ ] Create account on RunPod (or chosen provider)
- [ ] Deploy a pod with the **PyTorch 2.x** template
- [ ] SSH into the pod and note down the public IP + port

### 1.2 Install & Launch SGLang + OptiMind (~45 min)

```bash
# On the GPU server
pip install "sglang[all]>=0.4.5" \
  --find-links https://flashinfer.ai/whl/cu124/torch2.5/flashinfer-python
pip install gurobipy

python -m sglang.launch_server \
  --model-path microsoft/OptiMind-SFT \
  --host 0.0.0.0 --port 30000 \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --mem-fraction-static 0.85
```

First launch downloads ~28 GB of weights (10–15 min on fast connection).  
Server is ready when you see `"The server is fired up and ready to roll!"`.

- [ ] Install SGLang and dependencies
- [ ] Launch the model server
- [ ] Verify with `curl http://<IP>:30000/v1/models` from your MacBook

### 1.3 Update `run_optimind.py` for Remote Server (~30 min)

- [ ] Add `--server-url` argument (default `http://localhost:30000/v1`)
- [ ] Add connection error handling and configurable timeout (OptiMind can take 30–60 s)
- [ ] Add automatic code execution with structured result capture
- [ ] Test locally pointing at the remote server

### 1.4 End-to-End Testing (~45 min)

- [ ] Run OptiMind on the existing `example_problem` / `current_query`
- [ ] Verify it generates valid Gurobi code
- [ ] Execute the generated code locally
- [ ] Compare manually with OptiMUS output
- [ ] Test on 2–3 additional problems for reliability

### 1.5 Secure the Connection (~30 min)

Pick one:

| Option | Complexity | Security |
|--------|-----------|----------|
| SSH tunnel `ssh -L 30000:localhost:30000 user@gpu` | Low | High |
| RunPod built-in proxy + API key | Low | Medium |
| nginx reverse proxy with API key header | Medium | High |

- [ ] Set up chosen security mechanism
- [ ] Verify connection still works through the secure channel
- [ ] Document the connection details for Person B

---

## Phase 2 — Backend API + LLM Judge (Person B, ~3.5 h)

### 2.1 Scaffold FastAPI Backend (~30 min)

```
backend/
├── main.py              # FastAPI app entry
├── routers/
│   ├── problems.py      # POST /problems, GET /problems/{id}
│   └── results.py       # GET /results/{id}
├── services/
│   ├── optimus.py       # Wraps OptiMUS pipeline
│   ├── optimind.py      # Wraps OptiMind client
│   ├── judge.py         # LLM Judge logic
│   ├── orchestrator.py  # Parallel execution + coordination
│   └── executor.py      # Gurobi code execution
├── models/
│   └── schemas.py       # Pydantic models
├── requirements.txt
└── .env
```

**API endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/problems` | Submit new optimization problem |
| `GET` | `/api/problems/{id}/status` | Poll status (running / complete) |
| `GET` | `/api/problems/{id}/results` | Get final results + judge decision |
| `WS` | `/api/problems/{id}/stream` | *(Optional)* Live progress |

- [ ] Create directory structure
- [ ] Set up FastAPI app with CORS
- [ ] Define Pydantic schemas for request/response
- [ ] Create stub endpoints returning mock data
- [ ] Share API contract (OpenAPI spec) with Person C

### 2.2 Wrap OptiMUS as a Service (~30 min)

```python
async def run_optimus(problem_desc: str, parameters: dict, labels: dict) -> OptimusResult:
    """Run the full OptiMUS pipeline and return structured results."""
```

- [ ] Create `backend/services/optimus.py`
- [ ] Create temp problem directory from API input (write `desc.txt`, `params.json`, `labels.json`)
- [ ] Call pipeline steps programmatically (import from `pipeline/`)
- [ ] Return structured results: formulation, generated code, execution output, objective value
- [ ] Handle errors/timeouts gracefully

### 2.3 Wrap OptiMind as a Service (~30 min)

```python
async def run_optimind(problem_desc: str, parameters: dict, server_url: str) -> OptimindResult:
    """Call remote OptiMind server and return structured results."""
```

- [ ] Create `backend/services/optimind.py`
- [ ] Reuse prompt formatting from `run_optimind.py`
- [ ] Call the remote SGLang server (URL from Person A)
- [ ] Extract code from response, execute Gurobi locally
- [ ] Return structured results: model response, code, output, objective value

### 2.4 Build the LLM Judge (~1 h)

**Judge evaluates on five criteria:**

1. **Correctness** — Does the formulation faithfully represent the problem?
2. **Feasibility** — Did the code execute without errors? Is the solution feasible?
3. **Optimality** — Which objective value is better (lower for min, higher for max)?
4. **Completeness** — Are edge cases handled? All parameters used?
5. **Code Quality** — Is the solver code clean and efficient?

**Judge input:**

```python
@dataclass
class JudgeInput:
    problem_description: str
    parameters: dict

    optimus_formulation: dict       # constraints, objective, variables
    optimus_code: str
    optimus_output: str
    optimus_objective_value: float | None

    optimind_formulation: str       # OptiMind's reasoning
    optimind_code: str
    optimind_output: str
    optimind_objective_value: float | None
```

**Judge output:**

```python
@dataclass
class JudgeResult:
    winner: str              # "optimus" | "optimind" | "tie"
    confidence: float        # 0.0–1.0
    reasoning: str           # Detailed explanation
    criteria_scores: dict    # Per-criterion scores for both
    recommendation: str      # Plain-language recommendation
    best_objective_value: float | None
```

**Edge cases:**
- One agent fails → other wins by default
- Both fail → report failure with diagnostics
- Both succeed, different values → compare numerically, use formulation quality as tiebreaker
- Values very close → judge formulation quality

- [ ] Create `backend/services/judge.py`
- [ ] Design and iterate on judge prompt (Claude Sonnet)
- [ ] Implement structured output parsing
- [ ] Handle all edge cases above
- [ ] Test with at least 2 real problem pairs

### 2.5 Orchestrate Parallel Execution (~30 min)

```python
async def solve_problem(problem_id: str, problem: ProblemInput) -> FinalResult:
    optimus_task = asyncio.create_task(run_optimus(problem))
    optimind_task = asyncio.create_task(run_optimind(problem))
    optimus_result, optimind_result = await asyncio.gather(
        optimus_task, optimind_task, return_exceptions=True
    )
    judge_result = await run_judge(problem, optimus_result, optimind_result)
    best = optimus_result if judge_result.winner == "optimus" else optimind_result
    explanation = await generate_explanation(problem, best, judge_result)
    return FinalResult(judge=judge_result, optimus=optimus_result,
                       optimind=optimind_result, explanation=explanation)
```

- [ ] Create `backend/services/orchestrator.py`
- [ ] Wire up parallel agent execution
- [ ] Add status tracking (store state per `problem_id`)
- [ ] Wire orchestrator into API endpoints
- [ ] Test full pipeline: submit → poll → results

### 2.6 Plain-Language Output Generator (~30 min)

A final Claude call that produces:
- Non-technical summary of the optimization result
- Key recommendations in bullet points
- Sensitivity insights ("if X changes by 10%, result changes by Y")
- This text doubles as the HeyGen avatar script

- [ ] Create explanation prompt
- [ ] Integrate into orchestrator as final step
- [ ] Test output quality on 2–3 problems

---

## Phase 3 — Next.js Frontend (Person C, ~3 h)

### 3.1 Scaffold the App (~20 min)

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
cd frontend && npm install axios framer-motion lucide-react
```

- [ ] Create Next.js app with TypeScript + Tailwind
- [ ] Install UI dependencies
- [ ] Set up API client utility pointing at backend
- [ ] Create basic layout component (nav, footer)

### 3.2 Problem Input Page — `/` (~1 h)

Components:
1. **Text area** — optimization problem description (with example templates)
2. **Data upload** — drag-and-drop CSV/JSON, or structured parameter form
3. **Problem type selector** — maximize / minimize, domain tags
4. **"Solve" button** — calls `POST /api/problems`

- [ ] Build the main input form component
- [ ] Build the parameter entry / data upload component
- [ ] Add form validation (non-empty description, well-formed params)
- [ ] Add example problem templates users can click to pre-fill
- [ ] Wire submit to backend API
- [ ] Redirect to status page on successful submission

### 3.3 Progress Page — `/problems/[id]` (~45 min)

1. **Stepper / timeline** showing: "Running OptiMUS…" → "Running OptiMind…" → "Judging…" → "Complete"
2. Poll `GET /api/problems/{id}/status` every 2–3 s
3. Show intermediate outputs as they arrive
4. Estimated time remaining

- [ ] Build stepper / timeline UI component
- [ ] Implement polling logic with `useEffect` / SWR
- [ ] Show intermediate formulation previews
- [ ] Auto-redirect to results when complete
- [ ] Handle error / timeout states

### 3.4 Results Page — `/problems/[id]/results` (~1 h)

**Section 1 — Winner Banner:**
- "OptiMUS produced the best solution" with confidence score
- Judge reasoning in a collapsible card

**Section 2 — Plain-Language Explanation:**
- Non-technical summary
- Key recommendations as styled cards

**Section 3 — Side-by-Side Comparison** (collapsible, for technical users):
- Formulation comparison
- Code comparison (syntax-highlighted)
- Objective value comparison
- Per-criterion scores (radar chart or bar chart)

**Section 4 — Avatar Video** (if HeyGen ready):
- Embedded video player, or text fallback

- [ ] Build winner banner component
- [ ] Build plain-language explanation section
- [ ] Build side-by-side comparison (collapsible)
- [ ] Add syntax highlighting for code blocks
- [ ] Build avatar video section (with text fallback)
- [ ] Test with mock data, then real backend data

### 3.5 HeyGen Avatar Integration (Optional, ~30 min)

- [ ] Set up HeyGen API client
- [ ] Call API with plain-language explanation as script
- [ ] Poll for video generation completion
- [ ] Embed video in results page
- [ ] Graceful fallback to text if video not ready / API unavailable

---

## Phase 4 — Integration, Testing & Deployment (Person D / shared, ~1.5 h)

### 4.1 Wire Frontend ↔ Backend (~30 min)

- [ ] Configure CORS in FastAPI for the frontend origin
- [ ] Set environment variable / proxy for backend URL in Next.js
- [ ] Test full flow end-to-end: input → agents → judge → results
- [ ] Handle error states gracefully (server down, timeout, Gurobi license)

### 4.2 Dockerize (~30 min)

```yaml
# docker-compose.yml
version: "3.8"
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./data:/app/data
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on: [backend]
```

*(GPU server is external — not in Compose.)*

- [ ] Write `Dockerfile` for backend
- [ ] Write `Dockerfile` for frontend
- [ ] Write `docker-compose.yml`
- [ ] Test `docker compose up` locally
- [ ] Document environment variables

### 4.3 Deploy (~30 min)

| Component | Where | Cost |
|-----------|-------|------|
| Frontend (Next.js) | Vercel (free tier) | $0 |
| Backend (FastAPI) | Railway / Render / Fly.io | ~$7/mo |
| GPU Server (OptiMind) | RunPod on-demand or serverless | ~$0.50–0.75/hr |

**Gurobi licensing note:** Academic license is node-locked. For cloud deployment, use Gurobi Web License Service (WLS, free for academics) or switch to HiGHS/SCIP.

- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway / Render
- [ ] Configure environment variables in all environments
- [ ] Verify GPU server accessible from deployed backend
- [ ] Smoke-test the full deployed pipeline

---

## Priority Order (if time runs short)

| # | Item | Priority |
|---|------|----------|
| 1 | OptiMind working on GPU server (Phase 1.1–1.4) | **Must have** |
| 2 | FastAPI backend with both agents + judge (Phase 2.1–2.5) | **Must have** |
| 3 | Minimal frontend: input + results pages (Phase 3.1–3.4) | **Should have** |
| 4 | Plain-language generator (Phase 2.6) | Nice to have |
| 5 | HeyGen avatar (Phase 3.5) | Nice to have |
| 6 | Docker + cloud deployment (Phase 4.2–4.3) | Nice to have |

> A working demo is achievable with priorities 1–3 in ~8 hours.

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| OptiMind model too large for GPU | Medium | Use A100 40 GB minimum; `--mem-fraction-static 0.85` |
| SGLang installation issues | Medium | Use RunPod's PyTorch template (CUDA pre-configured) |
| Gurobi license on remote server | High | Use WLS cloud license, or execute code locally only |
| OptiMind generates invalid code | Medium | Code validation + fallback to OptiMUS-only mode |
| HeyGen API latency too high | Low | Make avatar optional; show text immediately |
| 10 hours not enough | Medium | Prioritize Phases 1+2; Phase 3 can be minimal viable |
