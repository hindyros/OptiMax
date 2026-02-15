#!/usr/bin/env python3
"""
Test client for Microsoft OptiMind-SFT (Hugging Face: microsoft/OptiMind-SFT).

Use this script to run OptiMind and compare formulations/results with OptiMUS.

Expects SGLang server running with:
  python -m sglang.launch_server \\
    --model-path microsoft/OptiMind-SFT \\
    --host 0.0.0.0 --port 30000 \\
    --tensor-parallel-size 1 --trust-remote-code

Requires: Python >= 3.12, valid Gurobi license for running generated code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from openai import OpenAI

# ---------------------------------------------------------------------------
# Model card system prompt (from Hugging Face)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert in optimization and mixed integer programming. You are given an
optimization problem and you need to solve it using gurobipy.
Reason step by step before generating the gurobipy code.
When you respond, first think carefully.
After thinking, output the math modeling of the problem.
Finally output a ```python ...``` code block that solves the problem.
The code must include:
import gurobipy as gp
from gurobipy import GRB
"""

# ---------------------------------------------------------------------------
# Sample optimization problems for testing
# ---------------------------------------------------------------------------

SAMPLE_PROBLEMS = {
    "factory": (
        "A factory produces products A and B. Each unit of A needs 2 hours of labor and 1 unit of "
        "raw material; each unit of B needs 1 hour of labor and 2 units of raw material. "
        "Available: 100 hours labor, 80 units raw material. Profit per unit: A = $3, B = $2. "
        "Maximize total profit."
    ),
    "knapsack": (
        "Knapsack: 5 items with weights [2, 3, 4, 5, 6] and values [3, 7, 5, 9, 8]. "
        "Knapsack capacity is 15. Select items to maximize total value (each item at most once)."
    ),
    "scheduling": (
        "Schedule 3 jobs on 2 machines. Job 1: processing times (machine1=2, machine2=3), "
        "Job 2: (4, 1), Job 3: (3, 2). Each job must be done on both machines in order (1 then 2). "
        "Minimize makespan."
    ),
    "blend": (
        "Blend two ingredients I1 and I2 to make a product. I1 costs $2/kg and has 30% protein; "
        "I2 costs $4/kg and has 50% protein. Need at least 40% protein in the blend. "
        "Produce 100 kg at minimum cost."
    ),
}


def get_client(base_url: str = "http://localhost:30000/v1", api_key: str = "EMPTY") -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def query_model(
    client: OpenAI,
    user_problem: str,
    *,
    model: str = "microsoft/OptiMind-SFT",
    temperature: float = 0.9,
    top_p: float = 1.0,
    max_tokens: int = 4096,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_problem},
        ],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


def extract_python_blocks(text: str) -> list[str]:
    """Extract ```python ... ``` code blocks from model output (for inspection only)."""
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches]


def check_gurobipy(code_blocks: list[str]) -> tuple[bool, list[str]]:
    """Check if any block contains gurobipy imports. Returns (has_gurobi, list of blocks that do)."""
    found = []
    for block in code_blocks:
        if "gurobipy" in block and ("import gurobipy" in block or "from gurobipy" in block):
            found.append(block)
    return (len(found) > 0, found)


def build_problem_from_optimus_dir(problem_dir: str, run_subdir: str = "optimus_output") -> str:
    """
    Build a single natural-language problem string from an OptiMUS problem directory,
    so OptiMind can be run on the same instance as OptiMUS for comparison.

    Uses:
      - problem_dir/desc.txt for the problem description
      - problem_dir/run_subdir/data.json for concrete data (if present), else
      - problem_dir/params.json "value" fields for data
    """
    desc_path = os.path.join(problem_dir, "desc.txt")
    if not os.path.isfile(desc_path):
        raise FileNotFoundError(f"OptiMUS problem dir must contain desc.txt: {desc_path}")

    with open(desc_path, "r") as f:
        description = f.read().strip()

    data_path = os.path.join(problem_dir, run_subdir, "data.json")
    if os.path.isfile(data_path):
        with open(data_path, "r") as f:
            data = json.load(f)
    else:
        params_path = os.path.join(problem_dir, "params.json")
        if not os.path.isfile(params_path):
            raise FileNotFoundError(
                f"Need either {data_path} or {params_path} for problem data."
            )
        with open(params_path, "r") as f:
            params = json.load(f)
        data = {k: v["value"] for k, v in params.items()}

    problem_text = description + "\n\nUse the following data:\n" + json.dumps(data, indent=2)
    return problem_text


def run_test(
    client: OpenAI,
    problem: str,
    problem_name: str = "custom",
    extract_code: bool = True,
    out_dir: str | None = None,
) -> str:
    """
    Send problem to OptiMind and optionally save response/code under out_dir.
    Returns the raw model response string.
    """
    print(f"\n{'='*60}")
    print(f"Problem [{problem_name}]")
    print(f"{'='*60}")
    print(problem[:200] + ("..." if len(problem) > 200 else ""))
    print()
    try:
        content = query_model(client, problem)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return ""

    print("--- Model response ---")
    print(content)

    if extract_code:
        blocks = extract_python_blocks(content)
        if blocks:
            has_gurobi, gurobi_blocks = check_gurobipy(blocks)
            print("\n--- Extracted code blocks ---")
            for i, b in enumerate(blocks, 1):
                print(
                    f"[Block {i}] ({'gurobipy' if b in gurobi_blocks else 'no gurobipy'}): {len(b)} chars"
                )
            if not has_gurobi and blocks:
                print("(No block contained gurobipy import; model may have used another format.)")

            if out_dir and blocks:
                os.makedirs(out_dir, exist_ok=True)
                # Save first gurobipy block as runnable script, else first block
                code_to_save = None
                for b in blocks:
                    if "gurobipy" in b and ("import gurobipy" in b or "from gurobipy" in b):
                        code_to_save = b
                        break
                if code_to_save is None:
                    code_to_save = blocks[0]
                code_path = os.path.join(out_dir, "optimind_code.py")
                with open(code_path, "w") as f:
                    f.write(code_to_save)
                print(f"\nSaved code to {code_path}")

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        response_path = os.path.join(out_dir, "optimind_response.txt")
        with open(response_path, "w") as f:
            f.write(content)
        print(f"Saved full response to {response_path}")

    print()
    return content


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


if __name__ == "__main__":
    main()
