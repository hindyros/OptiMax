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
- `labels.json` — Problem category labels

**3. Run the pipeline:**

```bash
python optimus.py
```

**4. Check results** in `current_query/output/`:

- `code.py` — The generated Gurobi solver
- `code_output.txt` — Solver output (optimal value)
- `state_*.json` — Intermediate state at each pipeline step
- `log.txt` — Full LLM interaction log

### Options

```
--dir DIR        Problem directory (default: current_query)
--model MODEL    LLM model (default: gpt-4o-mini)
--rag-mode MODE  RAG retrieval mode (optional)
--no-archive     With --clear, skip archiving (just wipe)
```

### Programmatic Usage

```python
from optimus import run_pipeline

state = run_pipeline("current_query", model="gpt-4o-mini")
print(state["objective"])
```

---

## OptiMind (GPU server)

OptiMind runs via an SGLang server on a machine with an NVIDIA GPU. To use it from this repo you need to:

1. **Provision a GPU VM** — e.g. on **Google Cloud** (recommended): see **[docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md](docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md)** for creating a Compute Engine VM (A100 or L4), installing SGLang, and opening port 30000. A script is provided: `scripts/setup-optimind-gcp.sh`.
2. **Run the client** from your Mac (or any machine with the repo and network access to the VM):

```bash
python -m optimind_pipeline --base-url http://<VM_EXTERNAL_IP>:30000/v1 --sample factory --execute
```
