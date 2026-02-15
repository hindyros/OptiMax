"""
LLM Judge -- compares OptiMUS and OptiMind solutions and picks a winner.

Decision pipeline:
    1. Load & classify each solver's output (optimal / error / infeasible / none)
    2. Programmatic fast-path for clear-cut cases (one solver missing or crashed)
    3. LLM evaluation for ambiguous cases (both ran, need formulation review)
    4. Sanity-check override (LLM can't pick a crashed solver over a working one)

The judge does NOT generate the final report -- that is handled by
consultant.py, which runs after the judge.

CLI usage:
    python judge.py                        # compare solutions in current_query/
    python judge.py --dir current_query    # explicit directory

Programmatic usage:
    from judge import compare_solutions
    verdict = compare_solutions("current_query")
"""

import os
import re
import json
import argparse

from optimus_pipeline.optimus_utils import get_response

JUDGE_MODEL = "gpt-4o"
FINAL_OUTPUT_DIR = "final_output"


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════


def _read_file(path):
    """Read a text file; return stripped contents or None if missing/empty."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        text = f.read().strip()
    return text or None


def _read_json(path):
    """Read a JSON file; return parsed dict or None."""
    text = _read_file(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_objective(raw):
    """Try to parse a numeric objective value from a string."""
    if raw is None:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _detect_direction(code):
    """Detect maximize/minimize from solver code. Returns str or None."""
    if not code:
        return None
    upper = code.upper()
    if "MAXIMIZE" in upper or "GRB.MAXIMIZE" in upper:
        return "maximize"
    if "MINIMIZE" in upper or "GRB.MINIMIZE" in upper:
        return "minimize"
    return None


def _classify_execution(code_output, objective_value):
    """
    Classify solver execution into a status string.

    Returns one of:
        "optimal"     - Gurobi found proven optimal, numeric objective available
        "feasible"    - Code ran, numeric objective available (not necessarily proven optimal)
        "infeasible"  - Gurobi reported model infeasible
        "unbounded"   - Gurobi reported model unbounded
        "error"       - Code crashed (traceback or execution failure)
        "no_result"   - Code ran but no numeric objective
        "not_run"     - No code_output at all
    """
    if code_output is None:
        return "not_run"

    if "Traceback" in code_output or "Execution failed" in code_output:
        return "error"

    upper = code_output.upper()
    if "INFEASIBLE" in upper and "OPTIMAL" not in upper:
        return "infeasible"
    if "UNBOUNDED" in upper and "OPTIMAL" not in upper:
        return "unbounded"

    if objective_value is not None:
        if "OPTIMAL" in upper:
            return "optimal"
        return "feasible"

    return "no_result"


def _trim_gurobi_output(code_output, max_lines=15):
    """
    Strip Gurobi license banner, statistics tables, and presolve noise.
    Keep only the meaningful result lines for the LLM judge.
    """
    if not code_output:
        return code_output

    skip_patterns = [
        "Set parameter",
        "Academic license",
        "Gurobi Optimizer version",
        "CPU model:",
        "Thread count",
        "Model fingerprint",
        "Coefficient statistics",
        "  Matrix range",
        "  Objective range",
        "  Bounds range",
        "  RHS range",
        "Presolve removed",
        "Presolve time",
        "Presolved:",
        "Variable types:",
        "Root relaxation:",
        "Explored ",
        "Thread count was",
        "Iteration ",
        "    Nodes",
        " Expl Unexpl",
        "Found heuristic",
    ]

    lines = code_output.strip().splitlines()
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("*"):  # Gurobi node table entries
            continue
        if any(stripped.startswith(p) for p in skip_patterns):
            continue
        # Skip the Gurobi tabular output (columns of numbers with |)
        if "|" in stripped and re.match(r"^\s*\d", stripped):
            continue
        kept.append(line)

    if not kept:
        # Everything was noise; fall back to last few lines of original
        kept = lines[-5:]

    return "\n".join(kept[-max_lines:])


# ---------------------------------------------------------------------------
# Loader functions
# ---------------------------------------------------------------------------


def load_problem(problem_dir):
    """Load the original problem description and parameters."""
    model_dir = os.path.join(problem_dir, "model_input")
    return {
        "description": _read_file(os.path.join(model_dir, "desc.txt")),
        "parameters": _read_json(os.path.join(model_dir, "params.json")),
    }


def _load_solver(out_dir, code_filename):
    """Generic loader for a solver's output directory."""
    if not os.path.isdir(out_dir):
        return None

    code = _read_file(os.path.join(out_dir, code_filename))
    code_output_raw = _read_file(os.path.join(out_dir, "code_output.txt"))
    objective_raw = _read_file(os.path.join(out_dir, "output_solution.txt"))
    objective_value = _parse_objective(objective_raw)
    execution_status = _classify_execution(code_output_raw, objective_value)

    return {
        "code": code,
        "code_output_raw": code_output_raw,
        "code_output_clean": _trim_gurobi_output(code_output_raw),
        "objective_value": objective_value,
        "objective_raw": objective_raw,
        "execution_status": execution_status,
        "direction": _detect_direction(code),
        "available": code is not None or code_output_raw is not None,
    }


def load_optimus_output(problem_dir):
    """Load OptiMUS solver output."""
    out_dir = os.path.join(problem_dir, "optimus_output")
    data = _load_solver(out_dir, "code.py")
    if data is None:
        return None

    # OptiMUS also has structured state with formulation details
    state = _read_json(os.path.join(out_dir, "state_6_code.json"))
    data["solver"] = "optimus"
    data["state"] = state
    return data


def load_optimind_output(problem_dir):
    """Load OptiMind solver output."""
    out_dir = os.path.join(problem_dir, "optimind_output")
    data = _load_solver(out_dir, "optimind_code.py")
    if data is None:
        return None

    # OptiMind also has the full model reasoning response
    response = _read_file(os.path.join(out_dir, "optimind_response.txt"))
    data["solver"] = "optimind"
    data["response"] = response
    return data


# ═══════════════════════════════════════════════════════════════════════════
# Prompt formatting
# ═══════════════════════════════════════════════════════════════════════════


_STATUS_LABELS = {
    "optimal": "OPTIMAL (proven optimal solution found)",
    "feasible": "FEASIBLE (solution found, optimality not proven)",
    "infeasible": "INFEASIBLE (no feasible solution exists)",
    "unbounded": "UNBOUNDED (objective is unbounded)",
    "error": "ERROR (code crashed during execution)",
    "no_result": "EXECUTED (code ran but produced no numeric result)",
    "not_run": "NOT RUN",
}


def _format_optimus_for_judge(optimus):
    """Build a clean summary of the OptiMUS solution for the judge prompt."""
    if not optimus or not optimus.get("available"):
        return "OptiMUS: No output available.\n"

    parts = ["=== OptiMUS Solution ==="]
    parts.append(f"Execution status: {_STATUS_LABELS.get(optimus['execution_status'], optimus['execution_status'])}")

    if optimus.get("objective_value") is not None:
        parts.append(f"Objective value: {optimus['objective_value']}")

    state = optimus.get("state")
    if state:
        obj = state.get("objective", {})
        parts.append(f"\nObjective: {obj.get('description', 'N/A')}")
        parts.append(f"Formulation: {obj.get('formulation', 'N/A')}")

        constraints = state.get("constraints", [])
        if constraints:
            parts.append(f"\nConstraints ({len(constraints)}):")
            for i, c in enumerate(constraints, 1):
                parts.append(f"  {i}. {c.get('description', 'N/A')}")
                parts.append(f"     Formulation: {c.get('formulation', 'N/A')}")

        variables = state.get("variables", {})
        if variables:
            parts.append(f"\nVariables ({len(variables)}):")
            for name, info in variables.items():
                parts.append(f"  {name}: {info.get('definition', 'N/A')} ({info.get('type', 'N/A')})")

    if optimus.get("code"):
        parts.append(f"\nGenerated Code:\n```python\n{optimus['code']}\n```")

    if optimus.get("code_output_clean"):
        parts.append(f"\nExecution Output:\n{optimus['code_output_clean']}")

    return "\n".join(parts)


def _format_optimind_for_judge(optimind):
    """Build a clean summary of the OptiMind solution for the judge prompt."""
    if not optimind or not optimind.get("available"):
        return "OptiMind: No output available.\n"

    parts = ["=== OptiMind Solution ==="]
    parts.append(f"Execution status: {_STATUS_LABELS.get(optimind['execution_status'], optimind['execution_status'])}")

    if optimind.get("objective_value") is not None:
        parts.append(f"Objective value: {optimind['objective_value']}")

    # Show reasoning/formulation from the model response (but not the code
    # block, since we show the extracted code separately below)
    response = optimind.get("response")
    if response:
        # Strip code fences from the response to avoid duplication
        reasoning = re.split(r"```(?:python)?", response)[0].strip()
        if reasoning:
            parts.append(f"\nModel Reasoning & Formulation:\n{reasoning}")

    if optimind.get("code"):
        parts.append(f"\nGenerated Code:\n```python\n{optimind['code']}\n```")

    if optimind.get("code_output_clean"):
        parts.append(f"\nExecution Output:\n{optimind['code_output_clean']}")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Decision logic
# ═══════════════════════════════════════════════════════════════════════════


def _programmatic_winner(optimus, optimind):
    """
    Determine winner from objective facts, without calling the LLM.

    Returns (winner_name, reason) if the decision is clear-cut,
    or (None, reason) if the LLM is needed.
    """
    opt_ok = optimus and optimus.get("available")
    mind_ok = optimind and optimind.get("available")

    # --- Neither available ---
    if not opt_ok and not mind_ok:
        return None, "neither solver produced output"

    opt_status = optimus["execution_status"] if opt_ok else "not_run"
    mind_status = optimind["execution_status"] if mind_ok else "not_run"

    # --- Only one produced output ---
    if not mind_ok:
        return "optimus", "only OptiMUS produced output"
    if not opt_ok:
        return "optimind", "only OptiMind produced output"

    # --- One succeeded, one failed ---
    success_statuses = {"optimal", "feasible"}
    fail_statuses = {"error", "infeasible", "unbounded", "not_run", "no_result"}

    opt_success = opt_status in success_statuses
    mind_success = mind_status in success_statuses

    if opt_success and not mind_success:
        return "optimus", f"OptiMUS succeeded ({opt_status}), OptiMind failed ({mind_status})"
    if mind_success and not opt_success:
        return "optimind", f"OptiMind succeeded ({mind_status}), OptiMUS failed ({opt_status})"

    # --- Both failed ---
    if not opt_success and not mind_success:
        return None, f"both solvers failed (OptiMUS: {opt_status}, OptiMind: {mind_status})"

    # --- Both succeeded: compare objectives ---
    opt_val = optimus.get("objective_value")
    mind_val = optimind.get("objective_value")

    if opt_val is not None and mind_val is not None and opt_val == mind_val:
        return None, f"both achieved same objective ({opt_val}); LLM to evaluate formulation quality"

    # Both succeeded with different objectives -- LLM must verify correctness
    # before we trust the objective comparison
    return None, "both succeeded with output; LLM to evaluate correctness and compare"


def _sanity_check(llm_winner, optimus, optimind):
    """
    Override the LLM's pick if it contradicts clear programmatic evidence.

    Returns (final_winner, was_overridden, override_reason).
    """
    opt_ok = optimus and optimus.get("available")
    mind_ok = optimind and optimind.get("available")
    opt_status = optimus.get("execution_status") if opt_ok else "not_run"
    mind_status = optimind.get("execution_status") if mind_ok else "not_run"

    success = {"optimal", "feasible"}

    # LLM picked a solver that crashed, but the other succeeded
    if llm_winner == "optimus" and opt_status not in success and mind_status in success:
        return "optimind", True, f"LLM picked OptiMUS ({opt_status}) but OptiMind succeeded ({mind_status})"
    if llm_winner == "optimind" and mind_status not in success and opt_status in success:
        return "optimus", True, f"LLM picked OptiMind ({mind_status}) but OptiMUS succeeded ({opt_status})"

    # LLM picked a solver with no output
    if llm_winner == "optimus" and not opt_ok and mind_ok:
        return "optimind", True, "LLM picked OptiMUS but it has no output"
    if llm_winner == "optimind" and not mind_ok and opt_ok:
        return "optimus", True, "LLM picked OptiMind but it has no output"

    return llm_winner, False, None


# ═══════════════════════════════════════════════════════════════════════════
# LLM prompts
# ═══════════════════════════════════════════════════════════════════════════


COMPARISON_PROMPT = """\
You are an expert in mathematical optimization and operations research. \
Your role is to act as a rigorous judge comparing two automated solvers' \
outputs for the same optimization problem.

## Original Problem

{problem_description}

## Solver Outputs

{optimus_summary}

---

{optimind_summary}

## Evaluation Criteria (apply in order; later criteria break ties)

1. **Execution success** — Did the code run and produce a result? A solver \
that crashes or returns INFEASIBLE/UNBOUNDED (when the problem is feasible) \
cannot win unless the other also failed.

2. **Formulation correctness** — Is the objective correct (right direction, \
right expression)? Are all constraints from the problem captured with correct \
signs, bounds, and variable types?

3. **Implementation fidelity** — Does the code correctly implement the stated \
formulation? Check indices, coefficients, constraint sense (≤ vs ≥ vs =), \
and that the solver is invoked properly.

4. **Objective value** — If both are correct and executed, which achieves a \
strictly better objective (higher for maximize, lower for minimize)?

If only one solver produced output, evaluate it on criteria 2–4 and it wins \
by default on execution.

Respond with a JSON object **and nothing else**:
{{
    "winner": "optimus" or "optimind",
    "direction": "maximize" or "minimize",
    "reasoning": "2-4 sentences: why this solver won, citing specific formulation or implementation strengths/weaknesses",
    "optimus_assessment": "1-2 sentence assessment of OptiMUS",
    "optimind_assessment": "1-2 sentence assessment of OptiMind"
}}"""


# ═══════════════════════════════════════════════════════════════════════════
# LLM calls
# ═══════════════════════════════════════════════════════════════════════════


def _parse_llm_json(response_text):
    """Robustly parse JSON from LLM output, handling markdown fences."""
    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def evaluate_solutions(problem, optimus, optimind, model=JUDGE_MODEL):
    """
    Call the LLM judge to compare both solutions.
    Returns the parsed comparison dict.
    """
    prompt = COMPARISON_PROMPT.format(
        problem_description=problem["description"] or "(no description)",
        optimus_summary=_format_optimus_for_judge(optimus),
        optimind_summary=_format_optimind_for_judge(optimind),
    )

    response = get_response(prompt, model=model)
    parsed = _parse_llm_json(response)

    if parsed and "winner" in parsed:
        return parsed

    # Fallback: couldn't parse
    return {
        "winner": "optimus",
        "direction": "unknown",
        "reasoning": f"Judge response could not be parsed. Raw: {response[:500]}",
        "optimus_assessment": "N/A",
        "optimind_assessment": "N/A",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main orchestration
# ═══════════════════════════════════════════════════════════════════════════


def compare_solutions(problem_dir="current_query", model=JUDGE_MODEL):
    """
    Compare OptiMUS and OptiMind solutions and pick a winner.

    Writes results to {problem_dir}/final_output/verdict.json.

    Returns the verdict dict.
    """
    # ── Load ──
    problem = load_problem(problem_dir)
    optimus = load_optimus_output(problem_dir)
    optimind = load_optimind_output(problem_dir)

    if not problem["description"]:
        raise FileNotFoundError(
            f"No problem description at {problem_dir}/model_input/desc.txt"
        )

    opt_ok = optimus and optimus.get("available")
    mind_ok = optimind and optimind.get("available")

    if not opt_ok and not mind_ok:
        raise RuntimeError("Neither solver produced output. Nothing to judge.")

    # ── Layer 1: Programmatic fast-path ──
    prog_winner, prog_reason = _programmatic_winner(optimus, optimind)

    if prog_winner:
        print(f"[judge] Programmatic winner: {prog_winner} ({prog_reason})")
        winner_name = prog_winner
        # Still call LLM for quality assessment
        print("[judge] Calling LLM for quality assessment...")
        comparison = evaluate_solutions(problem, optimus, optimind, model=model)
        # Override LLM's winner with our programmatic decision
        comparison["winner"] = prog_winner
        comparison["programmatic_reason"] = prog_reason
    else:
        # ── Layer 2: LLM comparison ──
        print(f"[judge] Both solvers have output. {prog_reason}")
        print("[judge] Calling LLM judge for comparison...")
        comparison = evaluate_solutions(problem, optimus, optimind, model=model)
        winner_name = comparison.get("winner", "optimus")

        # ── Layer 3: Sanity check ──
        winner_name, overridden, override_reason = _sanity_check(
            winner_name, optimus, optimind
        )
        if overridden:
            print(f"[judge] OVERRIDE: {override_reason}")
            comparison["winner"] = winner_name
            comparison["override_reason"] = override_reason

    print(f"[judge] Winner: {winner_name}")

    # ── Detect direction ──
    direction = comparison.get("direction", "unknown")
    if direction == "unknown":
        for solver in (optimus, optimind):
            if solver and solver.get("direction"):
                direction = solver["direction"]
                break

    # ── Build verdict ──
    winner_data = optimus if winner_name == "optimus" else optimind

    def _solver_status(solver):
        if not solver or not solver.get("available"):
            return "not_available"
        s = solver.get("execution_status", "not_run")
        if s in ("optimal", "feasible"):
            return "success"
        return s

    verdict = {
        "winner": winner_name,
        "objective_value": (
            winner_data.get("objective_value") if winner_data else None
        ),
        "direction": direction,
        "solvers": {
            "optimus": {
                "status": _solver_status(optimus),
                "objective_value": optimus.get("objective_value") if optimus else None,
            },
            "optimind": {
                "status": _solver_status(optimind),
                "objective_value": optimind.get("objective_value") if optimind else None,
            },
        },
        "reasoning": comparison.get("reasoning", ""),
        "optimus_assessment": comparison.get("optimus_assessment", ""),
        "optimind_assessment": comparison.get("optimind_assessment", ""),
    }

    # ── Write output ──
    output_dir = os.path.join(problem_dir, FINAL_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    verdict_path = os.path.join(output_dir, "verdict.json")
    with open(verdict_path, "w") as f:
        json.dump(verdict, f, indent=2)
    print(f"[judge] Verdict written to {verdict_path}")

    return verdict


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare OptiMUS and OptiMind solutions, pick a winner"
    )
    parser.add_argument(
        "--dir", type=str, default="current_query",
        help="Problem directory (default: current_query)",
    )
    parser.add_argument(
        "--model", type=str, default=JUDGE_MODEL,
        help=f"LLM model for judging (default: {JUDGE_MODEL})",
    )
    args = parser.parse_args()

    verdict = compare_solutions(problem_dir=args.dir, model=args.model)

    print(f"\n{'=' * 60}")
    print(f"  Winner:    {verdict['winner'].upper()}")
    print(f"  Objective: {verdict['objective_value']}")
    print(f"  Direction: {verdict['direction']}")
    print(f"  OptiMUS:   {verdict['solvers']['optimus']['status']} "
          f"(obj={verdict['solvers']['optimus']['objective_value']})")
    print(f"  OptiMind:  {verdict['solvers']['optimind']['status']} "
          f"(obj={verdict['solvers']['optimind']['objective_value']})")
    print(f"  Reasoning: {verdict['reasoning']}")
    print(f"{'=' * 60}")
