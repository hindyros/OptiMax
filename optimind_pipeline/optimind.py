#!/usr/bin/env python3
"""
Client for Microsoft OptiMind-SFT (Hugging Face: microsoft/OptiMind-SFT).

Run natural-language optimization problems through the OptiMind model;
optionally extract and execute the generated Gurobi code.

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
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
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


# ---------------------------------------------------------------------------
# Structured result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OptimindResult:
    """Structured result from an OptiMind run."""
    problem_name: str
    success: bool
    model_response: str
    code: str | None
    has_gurobipy: bool
    execution_output: str | None
    execution_status: str | None        # "Success" | "Error" | None (not executed)
    objective_value: float | None
    error_message: str | None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Client + model query with retry logic
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 120  # seconds — OptiMind can take 30-60s per problem
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 4.0  # seconds


def get_client(
    base_url: str = "http://localhost:30000/v1",
    api_key: str = "EMPTY",
    timeout: float = DEFAULT_TIMEOUT,
) -> OpenAI:
    """Create an OpenAI-compatible client with configurable timeout."""
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)


def query_model(
    client: OpenAI,
    user_problem: str,
    *,
    model: str = "microsoft/OptiMind-SFT",
    temperature: float = 0.9,
    top_p: float = 1.0,
    max_tokens: int = 4096,
    max_retries: int = MAX_RETRIES,
) -> str:
    """
    Query the OptiMind model with automatic retry on transient failures.

    Retries on: connection errors, timeouts, 5xx server errors, rate limits.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
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
        except KeyboardInterrupt:
            raise
        except Exception as e:
            last_error = e
            err_name = type(e).__name__
            is_retryable = any(keyword in err_name for keyword in (
                "Timeout", "Connection", "APIConnection", "InternalServerError",
                "RateLimitError", "ServiceUnavailable",
            )) or (hasattr(e, "status_code") and e.status_code in (500, 502, 503, 429, 529))

            if not is_retryable or attempt == max_retries - 1:
                raise

            delay = RETRY_BACKOFF_BASE * (2 ** attempt)
            print(
                f"[optimind] Attempt {attempt + 1}/{max_retries} failed ({err_name}). "
                f"Retrying in {delay:.0f}s...",
                file=sys.stderr,
            )
            time.sleep(delay)

    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Code extraction helpers
# ---------------------------------------------------------------------------

def extract_python_blocks(text: str) -> list[str]:
    """Extract ```python ... ``` code blocks from model output."""
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


def pick_best_code_block(blocks: list[str]) -> str | None:
    """Pick the best code block: prefer one with gurobipy, else first block."""
    if not blocks:
        return None
    for b in blocks:
        if "gurobipy" in b and ("import gurobipy" in b or "from gurobipy" in b):
            return b
    return blocks[0]


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

def execute_gurobi_code(code: str, work_dir: str, timeout: int = 120) -> tuple[str, str]:
    """
    Execute a Gurobi Python script and capture its output.

    Returns (output, status) where status is "Success" or "Error".
    """
    code_path = os.path.join(work_dir, "optimind_code.py")
    output_path = os.path.join(work_dir, "optimind_code_output.txt")

    os.makedirs(work_dir, exist_ok=True)
    with open(code_path, "w") as f:
        f.write(code)

    try:
        result = subprocess.run(
            [sys.executable, "optimind_code.py"],
            capture_output=True,
            text=True,
            check=True,
            cwd=work_dir,
            timeout=timeout,
        )
        output = result.stdout or "(no stdout)\n"
        with open(output_path, "w") as f:
            f.write(output)
        return output, "Success"
    except subprocess.TimeoutExpired:
        msg = f"Code execution timed out after {timeout}s"
        with open(output_path, "w") as f:
            f.write(f"Execution failed:\n{msg}")
        return msg, "Error"
    except subprocess.CalledProcessError as e:
        error_output = e.stderr or e.stdout or str(e)
        with open(output_path, "w") as f:
            f.write(f"Execution failed:\n{error_output}")
        return error_output, "Error"
    except Exception as e:
        with open(output_path, "w") as f:
            f.write(f"Execution failed:\n{str(e)}")
        return str(e), "Error"


def parse_objective_value(execution_output: str) -> float | None:
    """
    Try to extract the optimal objective value from Gurobi solver output.

    Looks for common patterns like:
      - "Optimal objective  1.234e+02"
      - "Objective value: 123.4"
      - "Optimal Objective Value: 123.4"
    """
    if not execution_output:
        return None

    patterns = [
        r"[Oo]ptimal\s+[Oo]bjective\s*[=:]?\s*([\d.eE+\-]+)",
        r"[Oo]bjective\s+[Vv]alue\s*[=:]?\s*([\d.eE+\-]+)",
        r"[Oo]ptimal\s+[Vv]alue\s*[=:]?\s*([\d.eE+\-]+)",
        r"[Bb]est\s+[Oo]bjective\s*[=:]?\s*([\d.eE+\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, execution_output)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Main run function (programmatic API)
# ---------------------------------------------------------------------------

def run_optimind(
    client: OpenAI,
    problem: str,
    problem_name: str = "custom",
    extract_code: bool = True,
    execute: bool = False,
    out_dir: str | None = None,
) -> OptimindResult:
    """
    Send problem to OptiMind, optionally execute generated code, and return
    a structured OptimindResult.

    This is the main programmatic entry point for the OptiMind client.
    """
    print(f"\n{'='*60}")
    print(f"Problem [{problem_name}]")
    print(f"{'='*60}")
    print(problem[:200] + ("..." if len(problem) > 200 else ""))
    print()

    # --- Query the model ---
    try:
        content = query_model(client, problem)
    except Exception as e:
        print(f"[optimind] Request failed: {e}", file=sys.stderr)
        return OptimindResult(
            problem_name=problem_name,
            success=False,
            model_response="",
            code=None,
            has_gurobipy=False,
            execution_output=None,
            execution_status=None,
            objective_value=None,
            error_message=str(e),
        )

    print("--- Model response ---")
    print(content)

    # --- Extract code blocks ---
    selected_code = None
    has_gurobi = False

    if extract_code:
        blocks = extract_python_blocks(content)
        if blocks:
            has_gurobi, gurobi_blocks = check_gurobipy(blocks)
            print("\n--- Extracted code blocks ---")
            for i, b in enumerate(blocks, 1):
                print(
                    f"[Block {i}] ({'gurobipy' if b in gurobi_blocks else 'no gurobipy'}): "
                    f"{len(b)} chars"
                )
            if not has_gurobi:
                print("(No block contained gurobipy import; model may have used another format.)")

            selected_code = pick_best_code_block(blocks)

            # Save code to disk
            if out_dir and selected_code:
                os.makedirs(out_dir, exist_ok=True)
                code_path = os.path.join(out_dir, "optimind_code.py")
                with open(code_path, "w") as f:
                    f.write(selected_code)
                print(f"\nSaved code to {code_path}")

    # --- Save full response ---
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        response_path = os.path.join(out_dir, "optimind_response.txt")
        with open(response_path, "w") as f:
            f.write(content)
        print(f"Saved full response to {response_path}")

    # --- Execute code ---
    exec_output = None
    exec_status = None
    objective_value = None

    if execute and selected_code:
        work_dir = out_dir or os.path.join(".", "_optimind_tmp")
        print("\n--- Executing generated code ---")
        exec_output, exec_status = execute_gurobi_code(selected_code, work_dir)
        if exec_status == "Success":
            print(f"[optimind] Execution succeeded.")
            objective_value = parse_objective_value(exec_output)
            if objective_value is not None:
                print(f"[optimind] Objective value: {objective_value}")
            else:
                print("[optimind] Could not parse objective value from output.")
        else:
            print(f"[optimind] Execution failed:\n{exec_output[:500]}", file=sys.stderr)
    elif execute and not selected_code:
        print("[optimind] --execute requested but no code block was extracted.", file=sys.stderr)

    # --- Build structured result ---
    result = OptimindResult(
        problem_name=problem_name,
        success=True,
        model_response=content,
        code=selected_code,
        has_gurobipy=has_gurobi,
        execution_output=exec_output,
        execution_status=exec_status,
        objective_value=objective_value,
        error_message=None,
    )

    # Save structured result as JSON
    if out_dir:
        summary_path = os.path.join(out_dir, "optimind_result.json")
        with open(summary_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"Saved result summary to {summary_path}")

    print()
    return result


# ---------------------------------------------------------------------------
# Legacy wrapper (for backward compat)
# ---------------------------------------------------------------------------

def run_test(
    client: OpenAI,
    problem: str,
    problem_name: str = "custom",
    extract_code: bool = True,
    out_dir: str | None = None,
) -> str:
    """
    Legacy wrapper — same interface as before, returns raw response string.
    Now delegates to run_optimind() internally.
    """
    result = run_optimind(
        client, problem, problem_name=problem_name,
        extract_code=extract_code, execute=False, out_dir=out_dir,
    )
    return result.model_response


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run Microsoft OptiMind-SFT via SGLang: solve optimization problems in natural language."
    )
    ap.add_argument(
        "--base-url",
        default="http://localhost:30000/v1",
        help="SGLang API base URL (default: http://localhost:30000/v1)",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT}). "
             "Increase for large problems or slow servers.",
    )
    ap.add_argument(
        "--retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Max retries on transient failures (default: {MAX_RETRIES}).",
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
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Execute the extracted Gurobi code locally after generation. "
             "Requires a valid Gurobi license.",
    )
    ap.add_argument(
        "--out-dir",
        type=str,
        metavar="DIR",
        help="Directory to save model response, extracted code, and result JSON.",
    )
    args = ap.parse_args()

    if args.list_samples:
        for name, text in SAMPLE_PROBLEMS.items():
            print(f"  {name}: {text[:80]}...")
        return

    # Create client with configured timeout
    client = get_client(base_url=args.base_url, timeout=args.timeout)

    # Check server connectivity before running
    try:
        client.models.list()
        print(f"[optimind] Connected to SGLang server at {args.base_url}")
    except Exception as e:
        print(
            f"[optimind] WARNING: Cannot reach server at {args.base_url}: {e}\n"
            f"  Make sure the SGLang server is running. Proceeding anyway...",
            file=sys.stderr,
        )

    extract = not args.no_extract_code
    out_dir = getattr(args, "out_dir", None)

    if args.run_all_samples:
        for name, problem in SAMPLE_PROBLEMS.items():
            run_optimind(
                client, problem, problem_name=name,
                extract_code=extract, execute=args.execute,
                out_dir=os.path.join(out_dir, name) if out_dir else None,
            )
        return

    if args.problem:
        run_optimind(
            client, args.problem, problem_name="custom",
            extract_code=extract, execute=args.execute,
            out_dir=out_dir,
        )
        return

    if args.sample:
        run_optimind(
            client, SAMPLE_PROBLEMS[args.sample], problem_name=args.sample,
            extract_code=extract, execute=args.execute,
            out_dir=out_dir,
        )
        return

    # Default: run the factory sample from the model card
    run_optimind(
        client, SAMPLE_PROBLEMS["factory"],
        problem_name="factory (default)",
        extract_code=extract, execute=args.execute,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
