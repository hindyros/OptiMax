# OptiMax

An ensemble NL-based optimization solver that compares solutions from OptiMUS and OptiMind, then uses an LLM judge to pick the best one.

Built for Treehacks 2026, with credit to original creators of OptiMUS and OptiMind.

## Setup

```bash
conda activate optimax
pip install -r requirements.txt
```

Create a `.env` file in the project root (gitignored). Copy from `.env.example` and fill in your keys:

```
OPENAI_API_KEY=your-openai-key
OPENAI_ORG_ID=your-org-id
ANTHROPIC_API_KEY=your-anthropic-key
GROQ_API_KEY=your-groq-key
OPTIMIND_SERVER_URL=http://<VM_IP>:30000/v1
```

A [Gurobi license](https://www.gurobi.com/academia/academic-program-and-licenses/) is required to execute generated solver code.

---

## Workflow

```bash
# 1. Clear workspace (archives previous results to query_history/)
python query_manager.py

# 2. Place input files in current_query/model_input/
#    - desc.txt       Natural-language problem description
#    - params.json    Parameters with shapes, types, and concrete values

# 3. Run solvers
python optimus.py      # OptiMUS  (structured multi-step pipeline)
python optimind.py     # OptiMind (single-pass LLM solver)

# 4. Compare solutions
python judge.py
```

Results appear in `current_query/`:

| Directory | Contents |
|-----------|----------|
| `optimus_output/` | Generated code, solver output, intermediate state, logs |
| `optimind_output/` | Raw LLM response, extracted code |
| `final_output/` | `verdict.json` and `explanation.txt` from the judge |

### `query_manager.py`

Manages the `current_query/` workspace shared by both solvers. Running it archives the current contents to `query_history/<timestamp>/` then wipes the workspace clean.

```
python query_manager.py              # archive + clear (default)
python query_manager.py --no-archive # just wipe, skip archiving
python query_manager.py --dir DIR    # target a different directory
```

Archives are capped at 20 (oldest pruned automatically).

**Programmatic usage:**

```python
from query_manager import prepare_workspace
prepare_workspace()  # archive + clear current_query/
```

### Creating inputs from data (CSV / Excel)

Turn a data file and a description into the expected `model_input/` format:

```bash
python data_to_optimax.py --data my_data.csv --description "Maximize profit subject to..."
python data_to_optimax.py --data sheet.xlsx --description path/to/desc.txt
```

Output is written to `current_query/raw_input/` and `current_query/model_input/`. Then run the solvers with no extra args.

**Options:**

| Flag | Description |
|------|-------------|
| `--data` | One or more CSV / Excel files |
| `--description` | Problem description text, or path to a `.txt` file |
| `--output DIR` | Problem directory (default: `current_query`) |
| `--simple` | Disable expert reasoning; one parameter per column |
| `--no-llm` | No LLM at all; column-based definitions |
| `--model MODEL` | LLM model for extraction (default: `gpt-4o-mini`) |

---

## OptiMUS

A structured, multi-step pipeline that converts a natural-language optimization problem into a Gurobi solver script. It decomposes the problem into parameters, objectives, and constraints, formulates each mathematically, generates code, then executes and debugs it.

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

### Options

```
--dir DIR      Problem directory (default: current_query)
--model MODEL  LLM model (default: gpt-4o-mini)
```

### Programmatic Usage

```python
from optimus import run_pipeline

state = run_pipeline("current_query", model="gpt-4o-mini")
print(state["objective"])
```

### Output

Written to `current_query/optimus_output/`:

| File | Contents |
|------|----------|
| `code.py` | Generated Gurobi solver |
| `code_output.txt` | Solver output (optimal value) |
| `state_*.json` | Intermediate state at each pipeline step |
| `log.txt` | Full LLM interaction log |

---

## OptiMind

Microsoft Research's fine-tuned LLM for optimization. Given a natural-language problem description, it reasons step-by-step, produces a mathematical formulation, and generates executable GurobiPy code in a single pass.

- **Model:** `microsoft/OptiMind-SFT` (20B params, MoE architecture with 3.6B activated)
- **Base model:** `gpt-oss-20b-BF16`
- **Paper:** [OptiMind: Teaching LLMs to Think Like Optimization Experts](https://arxiv.org/abs/2509.22979)

### Deployment

The model is self-hosted on a GCP VM with a single NVIDIA L4 GPU (24GB VRAM), served via **llama.cpp** with Q4_K_M quantization.

**How we got it running:** The full-precision model is ~40GB (BF16), which exceeds the L4's 24GB VRAM. Standard serving frameworks (SGLang FP8, vLLM bitsandbytes, HuggingFace transformers + 4-bit) failed because they load full-precision weights into VRAM before quantizing. The solution was offline quantization via llama.cpp's GGUF format:

1. Build llama.cpp from source with CUDA support (`-DGGML_CUDA=ON`)
2. Download model from HuggingFace (~40GB safetensors, 10 shards)
3. Convert to GGUF Q8_0 intermediate using `convert_hf_to_gguf.py` (~22GB)
4. Quantize Q8_0 to Q4_K_M using `llama-quantize --allow-requantize` (~15GB)
5. Serve with `llama-server` with all layers offloaded to GPU (`--n-gpu-layers 99`)

The Q4_K_M model fits in 24GB VRAM. For step-by-step GCP setup, see **[docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md](docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md)**.

**Start the server** (on the VM):

```bash
cd ~/llama.cpp && nohup ./build/bin/llama-server \
  --model ~/optimind-sft-Q4_K_M.gguf \
  --host 0.0.0.0 --port 30000 \
  --n-gpu-layers 99 --ctx-size 4096 -fa on \
  > ~/server.log 2>&1 &
```

**Check if running:** `pgrep llama-server && echo 'running' || echo 'down'`

**Stop the VM when done:** `gcloud compute instances stop <INSTANCE> --zone <ZONE> --project <PROJECT>`

### Configuration

Set in `.env`:

```
OPTIMIND_SERVER_URL=http://<VM_EXTERNAL_IP>:30000/v1
```

### Options

```
--dir DIR          Problem directory (default: current_query)
--base-url URL     Server URL (default: from OPTIMIND_SERVER_URL env var)
```

### Programmatic Usage

```python
from optimind import run_pipeline

result = run_pipeline("current_query")
```

### Output

Written to `current_query/optimind_output/`:

| File | Contents |
|------|----------|
| `optimind_response.txt` | Full LLM response (reasoning + code) |
| `optimind_code.py` | Extracted GurobiPy solver code |

---

## Judge

Compares solutions from OptiMUS and OptiMind, picks a winner, and generates a professional natural-language explanation.

### How it Works

1. **Programmatic Triage** -- Checks which solvers produced output. If only one ran, it is evaluated solo.
2. **LLM Comparison** -- GPT-4o evaluates both solutions on execution success, formulation quality, code correctness, and objective value.
3. **NL Explanation** -- A second LLM call generates a consultant-style executive summary and technical appendix.

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

### Output

Written to `current_query/final_output/`:

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
