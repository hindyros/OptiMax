# OptiMax

This repo implements an ensemble NL-based optimization solver that compares solutions from an improved OptiMUS and improved OptiMind.

Built for Treehacks 2026, with credit to original creators of OptiMUS and OptiMind.

## Setup

```bash
conda activate optimax
pip install -r requirements.txt
```

Create a local file for API keys (both are gitignored):

- **`.env`** or **`api_keys.env`** in the project root

Copy from `.env.example` and add your keys:

```
OPENAI_API_KEY=your-openai-key
OPENAI_ORG_ID=your-org-id
ANTHROPIC_API_KEY=your-anthropic-key
GROQ_API_KEY=your-groq-key
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

### Creating inputs from data (CSV / Excel)

To turn a data file and a natural-language problem description into OptiMUS inputs (`desc.txt`, `params.json`, `labels.json`), use:

```bash
python scripts/data_to_optimus.py --data my_data.csv --description "Maximize profit subject to..."
python scripts/data_to_optimus.py --data sheet.xlsx --description path/to/desc.txt
```

Output is written to **`current_query/`** by default (the folder OptiMUS uses). Then run OptiMUS with no extra args: `python optimus.py`. Use `--output DIR` only if you want a different problem folder, then run `python optimus.py --dir DIR`.

**Expert mode (default):** The script uses an LLM to reason like a consultant: it treats the description as a client brief and the data as their spreadsheet. It identifies **parameters** (quantities that appear in the math: capacities, demands, costs, etc.) and can add **derived dimensions** (e.g. NumberOfProducts from row count or distinct IDs) so the formulation has the right structure. ID columns are used for indexing/dimensions rather than as numeric parameters. Optionally it writes a short **model summary** to `assumptions.txt` for the client. No manual specification of parameters is required.

**Options:**

- **`--data`** — One or more paths to CSV or Excel files (e.g. `--data inventory.csv stores.csv`). With multiple files, the expert maps each parameter to a dataset by name (filename stem).
- **`--description`** — Natural-language problem description, or path to a .txt file containing it.
- **`--output`** — Directory where to write the three files (default: `current_query`; use this to align with OptiMUS).
- **`--simple`** — Disable expert reasoning: one parameter per column, with optional LLM polish for definitions/labels.
- **`--no-llm`** — No LLM at all; one parameter per column, column-based definitions and default labels.
- **`--model`** — LLM model for parameter extraction and/or definitions/labels (default: `gpt-4o-mini`).
- **`--labels-file`** — Path to an existing `labels.json` to use as-is.

---

## OptiMind (GPU server)

OptiMind runs via an SGLang server on a machine with an NVIDIA GPU. To use it from this repo you need to:

1. **Provision a GPU VM** — e.g. on **Google Cloud** (recommended): see **[docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md](docs/OPTIMIND_GOOGLE_CLOUD_SETUP.md)** for creating a Compute Engine VM (A100 or L4), installing SGLang, and opening port 30000. A script is provided: `scripts/setup-optimind-gcp.sh`.
2. **Run the client** from your Mac (or any machine with the repo and network access to the VM):

```bash
python -m optimind_pipeline --base-url http://<VM_EXTERNAL_IP>:30000/v1 --sample factory --execute
```
