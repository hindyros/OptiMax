#!/usr/bin/env python3
"""
OptiMind solver entry point.

Queries the self-hosted OptiMind model (llama.cpp on GCP), extracts the
generated GurobiPy code, executes it, and saves all artefacts to
current_query/optimind_output/.

CLI usage:
    python optimind.py                     # run on current_query/
    python optimind.py --dir other_dir     # different problem directory

Programmatic usage:
    from optimind import run_pipeline
    result = run_pipeline("current_query")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DIR = "optimind_output"
DEFAULT_BASE_URL = os.environ.get(
    "OPTIMIND_SERVER_URL", "http://localhost:30000/v1"
)
EXECUTE_TIMEOUT = 120  # seconds

SYSTEM_PROMPT = (
    "You are an expert in optimization and mixed integer programming. "
    "You are given an optimization problem and you need to solve it using gurobipy.\n"
    "Reason step by step before generating the gurobipy code.\n"
    "When you respond, first think carefully.\n"
    "After thinking, output the math modeling of the problem.\n"
    "Finally output a ```python ...``` code block that solves the problem.\n"
    "The code must include:\n"
    "import gurobipy as gp\n"
    "from gurobipy import GRB\n"
)

# Template appended to extracted code so Gurobi writes objective value to a
# file, matching the convention used by OptiMUS.  {var} is replaced with the
# actual Gurobi model variable name found in the generated code.
SOLUTION_TEMPLATE = """

# --- Optima: save objective value ---
if {var}.status == GRB.OPTIMAL:
    with open("output_solution.txt", "w") as _f:
        _f.write(str({var}.objVal))
    print("Optimal Objective Value:", {var}.objVal)
else:
    with open("output_solution.txt", "w") as _f:
        _f.write(str({var}.status))
    print("Model status:", {var}.status)
"""


# ---------------------------------------------------------------------------
# Server client
# ---------------------------------------------------------------------------


def _get_client(base_url: str, api_key: str = "EMPTY") -> OpenAI:
    """Return an OpenAI-compatible client pointed at the OptiMind server."""
    return OpenAI(base_url=base_url, api_key=api_key, timeout=300.0)


def _query_model(
    client: OpenAI,
    problem_text: str,
    *,
    model: str = "microsoft/OptiMind-SFT",
    temperature: float = 0.9,
    top_p: float = 1.0,
    max_tokens: int = 4096,
) -> str:
    """Send the problem to the OptiMind server and return the raw response."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": problem_text},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Input / extraction helpers
# ---------------------------------------------------------------------------


<<<<<<< HEAD
def check_gurobipy(code_blocks: list[str]) -> tuple[bool, list[str]]:
    """Check if any block contains gurobipy imports. Returns (has_gurobi, list of blocks that do)."""
    found = []
    for block in code_blocks:
        if "gurobipy" in block and ("import gurobipy" in block or "from gurobipy" in block):
            found.append(block)
    return (len(found) > 0, found)


def build_problem_from_optimus_dir(problem_dir: str, run_subdir: str = "optimus_output") -> str:
=======
def _read_problem(problem_dir: str) -> str:
>>>>>>> a1473fe4ea3aaca72cca7fc7a0a950b0f2484931
    """
    Build a single problem string from model_input/desc.txt + params.json.

    Only reads from model_input/ — completely independent of OptiMUS output.
    """
    model_dir = os.path.join(problem_dir, "model_input")

    desc_path = os.path.join(model_dir, "desc.txt")
    if not os.path.isfile(desc_path):
        raise FileNotFoundError(
            f"Missing model_input/desc.txt in {problem_dir}"
        )

    params_path = os.path.join(model_dir, "params.json")
    if not os.path.isfile(params_path):
        raise FileNotFoundError(
            f"Missing model_input/params.json in {problem_dir}"
        )

    with open(desc_path) as f:
        description = f.read().strip()

    with open(params_path) as f:
        params = json.load(f)

    data = {k: v["value"] for k, v in params.items()}
    return description + "\n\nUse the following data:\n" + json.dumps(data, indent=2)


def _extract_code(response_text: str) -> str | None:
    """
    Extract the best Python code block from the model response.

    Prefers a block that imports gurobipy; falls back to the first block.
    Returns None if no code blocks are found.
    """
    pattern = r"```(?:python)?\s*\n(.*?)```"
    blocks = [m.strip() for m in re.findall(pattern, response_text, re.DOTALL)]
    if not blocks:
        return None

    # Prefer blocks with gurobipy
    for block in blocks:
        if "gurobipy" in block and (
            "import gurobipy" in block or "from gurobipy" in block
        ):
            return block
    return blocks[0]


def _find_model_var(code: str) -> str:
    """
    Detect the Gurobi Model variable name from generated code.

    Looks for patterns like ``m = gp.Model(...)`` or ``model = Model(...)``.
    Falls back to "model" if nothing is found.
    """
    match = re.search(r"(\w+)\s*=\s*(?:gp\.)?Model\s*\(", code)
    return match.group(1) if match else "model"


def _patch_code(code: str) -> str:
    """
    Ensure the code writes output_solution.txt with the objective value.

    If the code already writes to output_solution.txt we leave it alone;
    otherwise we detect the Gurobi model variable name and append the
    standard snippet.
    """
    if "output_solution.txt" in code:
        return code
    var = _find_model_var(code)
    return code + SOLUTION_TEMPLATE.format(var=var)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_code(code_path: str, cwd: str) -> tuple[str, bool]:
    """
    Run the generated code from *cwd* and save stdout to code_output.txt.

    Returns (output_text, success).
    """
    output_path = os.path.join(cwd, "code_output.txt")
    try:
        result = subprocess.run(
            ["python", os.path.basename(code_path)],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=EXECUTE_TIMEOUT,
        )
        output = result.stdout + result.stderr
        with open(output_path, "w") as f:
            f.write(output or "(no output)\n")
        return output, result.returncode == 0

    except subprocess.TimeoutExpired as exc:
        msg = f"Execution timed out after {EXECUTE_TIMEOUT}s.\n"
        msg += (exc.stdout or "") + (exc.stderr or "")
        with open(output_path, "w") as f:
            f.write(msg)
        return msg, False

    except Exception as exc:
        msg = f"Execution failed: {exc}\n"
        with open(output_path, "w") as f:
            f.write(msg)
        return msg, False


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    problem_dir: str = "current_query",
    base_url: str | None = None,
) -> dict:
    """
    Run the full OptiMind pipeline.

    1. Read problem from model_input/
    2. Query OptiMind server
    3. Extract + patch code
    4. Execute code (writes output_solution.txt)
    5. Save all artefacts to optimind_output/

    Args:
        problem_dir: Path to the problem folder (default: current_query).
        base_url:    OptiMind server URL (default: OPTIMIND_SERVER_URL env var).

    Returns:
        dict with keys: response, code, code_output, success, objective_value
    """
    if base_url is None:
        base_url = DEFAULT_BASE_URL

    out_dir = os.path.join(problem_dir, OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    # ---- 1. Read problem ----
    problem_text = _read_problem(problem_dir)
    print(f"\n{'=' * 60}")
    print("OptiMind")
    print(f"{'=' * 60}")
    print(f"Server: {base_url}")
    print(f"Problem (first 200 chars): {problem_text[:200]}{'...' if len(problem_text) > 200 else ''}")
    print()

    # ---- 2. Query model ----
    client = _get_client(base_url)
    try:
        response_text = _query_model(client, problem_text)
    except Exception as exc:
        print(f"[OptiMind] Request failed: {exc}", file=sys.stderr)
        return {"response": "", "code": None, "code_output": None,
                "success": False, "objective_value": None}

    # Save full response
    response_path = os.path.join(out_dir, "optimind_response.txt")
    with open(response_path, "w") as f:
        f.write(response_text)
    print(f"Saved response  -> {response_path}")

    # ---- 3. Extract + patch code ----
    code = _extract_code(response_text)
    if code is None:
        print("[OptiMind] No code blocks found in response.")
        return {"response": response_text, "code": None, "code_output": None,
                "success": False, "objective_value": None}

    code = _patch_code(code)

    code_path = os.path.join(out_dir, "optimind_code.py")
    with open(code_path, "w") as f:
        f.write(code)
    print(f"Saved code      -> {code_path}")

    # ---- 4. Execute ----
    print(f"\nExecuting generated code...")
    code_output, success = _execute_code(code_path, cwd=out_dir)

    if success:
        print("[OptiMind] Execution succeeded.")
    else:
        print("[OptiMind] Execution failed. See code_output.txt for details.")

    # ---- 5. Read objective value (written by the executed code) ----
    obj_path = os.path.join(out_dir, "output_solution.txt")
    objective_value = None
    if os.path.isfile(obj_path):
        with open(obj_path) as f:
            raw = f.read().strip()
        try:
            objective_value = float(raw)
        except ValueError:
            objective_value = raw  # non-numeric status

    if objective_value is not None:
        print(f"[OptiMind] Objective value: {objective_value}")

    print()
    return {
        "response": response_text,
        "code": code,
        "code_output": code_output,
        "success": success,
        "objective_value": objective_value,
    }


<<<<<<< HEAD
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run Microsoft OptiMind-SFT (e.g. via SGLang) for comparison with OptiMUS."
    )
    ap.add_argument(
        "--base-url",
        default="http://localhost:30000/v1",
        help="SGLang API base URL (default: http://localhost:30000/v1)",
    )
    ap.add_argument(
        "--problem",
        type=str,
        help="Custom optimization problem (natural language).",
    )
    ap.add_argument(
        "--sample",
        choices=list(SAMPLE_PROBLEMS),
        help="Use a built-in sample problem.",
    )
    ap.add_argument(
        "--list-samples",
        action="store_true",
        help="Print sample problem names and exit.",
    )
    ap.add_argument(
        "--run-all-samples",
        action="store_true",
        help="Run all sample problems.",
    )
    ap.add_argument(
        "--no-extract-code",
        action="store_true",
        help="Do not extract or summarize code blocks.",
    )
    # OptiMUS comparison: run on same problem dir as main.py --dir
    ap.add_argument(
        "--optimus-dir",
        type=str,
        metavar="DIR",
        help="OptiMUS problem directory (e.g. example_problem). Builds problem from desc.txt + data, saves response and code to run_dev/ for comparison with OptiMUS.",
    )
    ap.add_argument(
        "--optimus-run-subdir",
        type=str,
        default="optimus_output",
        help="Subdir under --optimus-dir for data.json and output (default: optimus_output).",
    )
    args = ap.parse_args()

    if args.list_samples:
        for name, text in SAMPLE_PROBLEMS.items():
            print(f"  {name}: {text[:80]}...")
        return

    if args.optimus_dir:
        problem = build_problem_from_optimus_dir(args.optimus_dir, args.optimus_run_subdir)
        out_dir = os.path.join(args.optimus_dir, args.optimus_run_subdir)
        client = get_client(base_url=args.base_url)
        run_test(
            client,
            problem,
            problem_name="optimus_problem",
            extract_code=not args.no_extract_code,
            out_dir=out_dir,
        )
        print("Compare with OptiMUS: run main.py --dir", args.optimus_dir, "then diff formulations/code in", out_dir)
        return

    if args.run_all_samples:
        client = get_client(base_url=args.base_url)
        for name, problem in SAMPLE_PROBLEMS.items():
            run_test(client, problem, problem_name=name, extract_code=not args.no_extract_code)
        return

    if args.problem:
        client = get_client(base_url=args.base_url)
        run_test(client, args.problem, problem_name="custom", extract_code=not args.no_extract_code)
        return

    if args.sample:
        client = get_client(base_url=args.base_url)
        run_test(
            client,
            SAMPLE_PROBLEMS[args.sample],
            problem_name=args.sample,
            extract_code=not args.no_extract_code,
        )
        return

    # Default: run the factory sample from the model card
    client = get_client(base_url=args.base_url)
    run_test(
        client,
        SAMPLE_PROBLEMS["factory"],
        problem_name="factory (default)",
        extract_code=not args.no_extract_code,
    )

=======
# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
>>>>>>> a1473fe4ea3aaca72cca7fc7a0a950b0f2484931

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the OptiMind optimization solver"
    )
    parser.add_argument(
        "--dir", type=str, default="current_query",
        help="Problem directory (default: current_query)",
    )
    parser.add_argument(
        "--base-url", type=str, default=None,
        help="OptiMind server URL (default: from OPTIMIND_SERVER_URL env var)",
    )
    args = parser.parse_args()

    result = run_pipeline(problem_dir=args.dir, base_url=args.base_url)
    if not result["success"]:
        sys.exit(1)
