# OptiMax

This repo implements an ensemble NL-based optimization solver that compares solutions from an improved OptiMUS and improved OptiMind.

Built for Treehacks 2026, with credit to original creators of OptiMUS and OptiMind.

## Setup

```bash
conda activate optimax
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
OPTIMIND_SERVER_URL=http://<VM_EXTERNAL_IP>:30000/v1
```

A [Gurobi license](https://www.gurobi.com/academia/academic-program-and-licenses/) is required to execute generated solver code.

---

## OptiMUS

OptiMUS is a structured, multi-step pipeline that converts a natural-language optimization problem into a Gurobi solver script. It decomposes the problem into parameters, objectives, and constraints, formulates each mathematically, generates code, then executes and debugs it.

### Pipeline Steps

| Step | File | What it does |
|------|------|--------------|
| 1 | `step01_parameters.py` | Extract parameters from the problem description |
| 2 | `step02_objective.py` | Identify the optimization objective |
| 3 | `step03_constraints.py` | Extract constraints |
| 4 | `step04_constraint_model.py` | Formulate constraints in LaTeX |
| 5 | `step05_objective_model.py` | Formulate objective in LaTeX |
| 6 | `step06_target_code.py` | Generate Gurobi code for each constraint/objective |
| 7 | `step07_generate_code.py` | Assemble the complete solver script |
| 8 | `step08_execute_code.py` | Execute the script; if it errors, reflect and retry |

All step files live in `optimus_pipeline/`.

### Usage

**1. Clear the workspace** (archives any previous results to `query_history/`):

```bash
python optimus.py --clear
```

**2. Place your problem files** in `current_query/`:

- `desc.txt` — Natural-language problem description
- `params.json` — Parameters with shapes, types, and concrete values

**3. Run the pipeline:**

```bash
python optimus.py
```

**4. Check results** in `current_query/optimus_output/`:

- `code.py` — The generated Gurobi solver
- `code_output.txt` — Solver output (optimal value)
- `state_*.json` — Intermediate state at each pipeline step
- `log.txt` — Full LLM interaction log

### Options

```
--dir DIR        Problem directory (default: current_query)
--model MODEL    LLM model (default: gpt-4o-mini)
--no-archive     With --clear, skip archiving (just wipe)
```

### Programmatic Usage

```python
from optimus import run_pipeline

state = run_pipeline("current_query", model="gpt-4o-mini")
print(state["objective"])
```

---

## OptiMind

OptiMind is Microsoft Research's fine-tuned LLM for optimization. Given a natural-language problem description, it reasons step-by-step, produces a mathematical formulation, and generates executable GurobiPy code in a single pass.

- **Model:** `microsoft/OptiMind-SFT` (20B params, MoE architecture with 3.6B activated)
- **Base model:** `gpt-oss-20b-BF16`
- **Paper:** [OptiMind: Teaching LLMs to Think Like Optimization Experts](https://arxiv.org/abs/2509.22979)

### Deployment

The model is self-hosted on a GCP VM (`cs229p1`, `us-central1-c`, project `cs229p`) with a single NVIDIA L4 GPU (24GB VRAM). It is served via **llama.cpp** with Q4_K_M quantization.

**How we got it running:**

The full-precision model is ~40GB (BF16), which exceeds the L4's 24GB VRAM. Standard serving frameworks (SGLang FP8, vLLM bitsandbytes, HuggingFace transformers + 4-bit) all failed because they load full-precision weights into VRAM before quantizing. The solution was offline quantization via llama.cpp's GGUF format:

1. Built llama.cpp from source with CUDA support (`-DGGML_CUDA=ON`)
2. Downloaded model from HuggingFace (~40GB safetensors, 10 shards)
3. Converted to GGUF Q8_0 intermediate using `convert_hf_to_gguf.py` (~22GB)
4. Quantized Q8_0 to Q4_K_M using `llama-quantize --allow-requantize` (~15GB)
5. Serving with `llama-server` with all layers offloaded to GPU (`--n-gpu-layers 99`)

The Q4_K_M model fits comfortably in 24GB VRAM and produces correct formulations + code at ~72 tokens/sec.

### Server commands

**Start the server** (on the VM):

```bash
cd ~/llama.cpp && nohup ./build/bin/llama-server \
  --model ~/optimind-sft-Q4_K_M.gguf \
  --host 0.0.0.0 --port 30000 \
  --n-gpu-layers 99 --ctx-size 4096 -fa on \
  > ~/server.log 2>&1 &
```

**Check if running:**

```bash
pgrep llama-server && echo 'running' || echo 'down'
```

**Stop the VM after the hackathon:**

```bash
gcloud compute instances stop cs229p1 --zone us-central1-c --project cs229p
```

### Configuration

Add to `.env`:

```
OPTIMIND_SERVER_URL=http://<VM_EXTERNAL_IP>:30000/v1
```

The current external IP is `136.115.38.186` (may change if VM is restarted).

### Usage

```bash
python optimind.py
```

This reads the problem from `current_query/`, sends it to the OptiMind server, extracts the generated code, executes it, and writes results to `current_query/optimind_output/`.

### Options

```
--optimus-dir DIR              Problem directory (default: current_query)
--optimind-output-subdir DIR   Output subdirectory (default: optimind_output)
--base-url URL                 Server URL (default: from OPTIMIND_SERVER_URL env var)
```

---

## Judge

The judge compares solutions from OptiMUS and OptiMind, picks a winner, and generates a professional natural-language explanation.

### How it Works

1. **Programmatic Triage** — Checks which solvers produced output. If only one solver ran, it is evaluated solo.
2. **LLM Comparison** — GPT-4o evaluates both solutions on execution success, formulation quality, code correctness, and objective value.
3. **NL Explanation** — A second LLM call generates a consultant-style executive summary and technical appendix.

### Usage

After running one or both solvers:

```bash
python judge.py
```

### Output

Results are written to `current_query/final_output/`:

| File | Contents |
|------|----------|
| `verdict.json` | Structured result consumed by the frontend |
| `explanation.txt` | Full NL explanation (executive summary + technical appendix) |

### `verdict.json` Schema

```json
{
    "winner": "optimus",
    "objective_value": 280.0,
    "direction": "maximize",
    "solvers": {
        "optimus":  { "status": "success", "objective_value": 280.0 },
        "optimind": { "status": "not_available", "objective_value": null }
    },
    "reasoning": "Why this solver was chosen...",
    "optimus_assessment": "Assessment of OptiMUS solution...",
    "optimind_assessment": "Assessment of OptiMind solution...",
    "explanation": "Executive summary text...",
    "technical_details": "Mathematical formulation, code, solver output..."
}
```

**Solver status values:** `"success"` (ran and produced objective value), `"executed"` (ran but no numeric result), `"not_available"` (no output found).

### Options

```
--dir DIR      Problem directory (default: current_query)
--model MODEL  LLM model for judging (default: gpt-4o)
```

### Programmatic Usage

```python
from judge import compare_solutions

verdict = compare_solutions("current_query")
print(verdict["winner"], verdict["objective_value"])
```
