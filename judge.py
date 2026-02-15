"""
LLM Judge -- compares OptiMUS and OptiMind solutions, picks a winner,
and generates a professional natural-language explanation.

CLI usage:
    python judge.py                        # compare solutions in current_query/
    python judge.py --dir current_query    # explicit directory

Programmatic usage:
    from judge import compare_solutions
    verdict = compare_solutions("current_query")
"""

import os
import json
import argparse

from optimus_utils import get_response

JUDGE_MODEL = "gpt-4o"
FINAL_OUTPUT_DIR = "final_output"

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read a file and return its contents, or None if it doesn't exist."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return f.read().strip()


def _read_json(path):
    """Read a JSON file and return the parsed dict, or None if missing."""
    text = _read_file(path)
    if text is None:
        return None
    return json.loads(text)


def load_problem(problem_dir):
    """Load the original problem description and parameters."""
    model_dir = os.path.join(problem_dir, "model_input")
    desc = _read_file(os.path.join(model_dir, "desc.txt"))
    params = _read_json(os.path.join(model_dir, "params.json"))
    return {"description": desc, "parameters": params}


def load_optimus_output(problem_dir):
    """Load OptiMUS solver output. Returns a dict with available data."""
    out_dir = os.path.join(problem_dir, "optimus_output")
    if not os.path.isdir(out_dir):
        return None

    state = _read_json(os.path.join(out_dir, "state_6_code.json"))
    code = _read_file(os.path.join(out_dir, "code.py"))
    code_output = _read_file(os.path.join(out_dir, "code_output.txt"))
    objective_value = _read_file(os.path.join(out_dir, "output_solution.txt"))

    # Try to parse objective as a number
    obj_numeric = None
    if objective_value:
        try:
            obj_numeric = float(objective_value)
        except ValueError:
            pass

    return {
        "solver": "optimus",
        "state": state,
        "code": code,
        "code_output": code_output,
        "objective_value": obj_numeric,
        "objective_raw": objective_value,
        "available": state is not None or code is not None,
    }


def load_optimind_output(problem_dir):
    """
    Load OptiMind solver output. Returns a dict with available data.

    The exact file names and format may evolve as OptiMind's execution
    pipeline is finalized. This loader reads whatever is available.
    """
    out_dir = os.path.join(problem_dir, "optimind_output")
    if not os.path.isdir(out_dir):
        return None

    response = _read_file(os.path.join(out_dir, "optimind_response.txt"))
    code = _read_file(os.path.join(out_dir, "optimind_code.py"))
    code_output = _read_file(os.path.join(out_dir, "code_output.txt"))
    objective_value = _read_file(os.path.join(out_dir, "output_solution.txt"))

    # Try to parse objective as a number
    obj_numeric = None
    if objective_value:
        try:
            obj_numeric = float(objective_value)
        except ValueError:
            pass

    return {
        "solver": "optimind",
        "response": response,
        "code": code,
        "code_output": code_output,
        "objective_value": obj_numeric,
        "objective_raw": objective_value,
        "available": response is not None or code is not None,
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_optimus_for_judge(optimus):
    """Build a text summary of the OptiMUS solution for the judge prompt."""
    if not optimus or not optimus["available"]:
        return "OptiMUS: No output available."

    parts = ["=== OptiMUS Solution ==="]

    state = optimus.get("state")
    if state:
        # Objective
        obj = state.get("objective", {})
        parts.append(f"\nObjective: {obj.get('description', 'N/A')}")
        parts.append(f"Formulation: {obj.get('formulation', 'N/A')}")
        parts.append(f"Code: {obj.get('code', 'N/A')}")

        # Constraints
        constraints = state.get("constraints", [])
        parts.append(f"\nConstraints ({len(constraints)}):")
        for i, c in enumerate(constraints, 1):
            parts.append(f"  {i}. {c.get('description', 'N/A')}")
            parts.append(f"     Formulation: {c.get('formulation', 'N/A')}")
            parts.append(f"     Code: {c.get('code', 'N/A')}")

        # Variables
        variables = state.get("variables", {})
        parts.append(f"\nVariables ({len(variables)}):")
        for name, info in variables.items():
            parts.append(f"  {name}: {info.get('definition', 'N/A')} (type: {info.get('type', 'N/A')})")

    if optimus.get("code"):
        parts.append(f"\nGenerated Code:\n{optimus['code']}")

    if optimus.get("objective_value") is not None:
        parts.append(f"\nObjective Value: {optimus['objective_value']}")
    elif optimus.get("code_output"):
        parts.append(f"\nExecution Output:\n{optimus['code_output']}")

    return "\n".join(parts)


def _format_optimind_for_judge(optimind):
    """Build a text summary of the OptiMind solution for the judge prompt."""
    if not optimind or not optimind["available"]:
        return "OptiMind: No output available."

    parts = ["=== OptiMind Solution ==="]

    if optimind.get("response"):
        parts.append(f"\nModel Response (reasoning + formulation):\n{optimind['response']}")

    if optimind.get("code"):
        parts.append(f"\nGenerated Code:\n{optimind['code']}")

    if optimind.get("objective_value") is not None:
        parts.append(f"\nObjective Value: {optimind['objective_value']}")
    elif optimind.get("code_output"):
        parts.append(f"\nExecution Output:\n{optimind['code_output']}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------

COMPARISON_PROMPT = """You are an expert judge evaluating two optimization solvers. Your job is to compare their solutions to the same problem and determine which is better.

## Original Problem

{problem_description}

## Solver Outputs

{optimus_summary}

{optimind_summary}

## Your Task

Evaluate both solutions on these criteria (in order of importance):

1. **Execution**: Did the code run successfully and produce a result?
2. **Formulation Quality**: Did the solver correctly identify all constraints, the objective, and variable types from the problem description? Are the mathematical formulations accurate?
3. **Code Correctness**: Does the generated code correctly implement the stated formulation? Are there bugs (wrong indices, flipped inequalities, missing loops)?
4. **Objective Value**: Given both formulations are correct, which achieved a better objective value?

If only one solver produced output, evaluate that solver's correctness on its own.

Respond with a JSON object (and nothing else) in this exact format:
{{
    "winner": "optimus" or "optimind",
    "direction": "maximize" or "minimize",
    "reasoning": "2-3 sentence explanation of why this solver was chosen",
    "optimus_assessment": "1-2 sentence assessment of OptiMUS's solution",
    "optimind_assessment": "1-2 sentence assessment of OptiMind's solution"
}}
"""

EXPLANATION_PROMPT = """You are a senior management consultant presenting optimization results to a non-technical executive audience. Your tone is professional, clear, and actionable.

## The Problem

{problem_description}

## The Winning Solution

{winner_details}

## Your Task

Write a two-part response:

**PART 1 — EXECUTIVE SUMMARY**

Write a clear, jargon-free explanation of:
- What was being optimized and why
- What the optimal solution recommends (specific numbers and actions)
- What the expected outcome is (the objective value, in business terms)
- Any key trade-offs or considerations

Write this as if advising a CEO. No math, no code. Use concrete language ("produce 40 units" not "set x_A = 40").

**PART 2 — TECHNICAL APPENDIX**

Present the mathematical details for technical stakeholders:
- The objective function (in LaTeX/math notation)
- All constraints (in LaTeX/math notation)
- The generated solver code
- The solver output and optimal value

Separate the two parts with the line: --- TECHNICAL APPENDIX ---
"""


def evaluate_solutions(problem, optimus, optimind, model=JUDGE_MODEL):
    """
    Call the LLM judge to compare both solutions.
    Returns the parsed comparison dict.
    """
    optimus_summary = _format_optimus_for_judge(optimus)
    optimind_summary = _format_optimind_for_judge(optimind)

    prompt = COMPARISON_PROMPT.format(
        problem_description=problem["description"],
        optimus_summary=optimus_summary,
        optimind_summary=optimind_summary,
    )

    response = get_response(prompt, model=model)

    # Parse JSON from response
    try:
        # Handle case where LLM wraps JSON in markdown code blocks
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        # Fallback: return raw response as reasoning
        return {
            "winner": "optimus",
            "direction": "unknown",
            "reasoning": f"Judge response could not be parsed as JSON. Raw: {response[:500]}",
            "optimus_assessment": "N/A",
            "optimind_assessment": "N/A",
        }


def generate_explanation(problem, winner_data, comparison, model=JUDGE_MODEL):
    """
    Generate a professional natural-language explanation of the winning solution.
    Returns a dict with 'summary' and 'technical' fields.
    """
    winner_name = comparison.get("winner", "optimus")

    if winner_name == "optimus":
        winner_details = _format_optimus_for_judge(winner_data)
    else:
        winner_details = _format_optimind_for_judge(winner_data)

    prompt = EXPLANATION_PROMPT.format(
        problem_description=problem["description"],
        winner_details=winner_details,
    )

    response = get_response(prompt, model=model)

    # Split into summary and technical sections
    separator = "--- TECHNICAL APPENDIX ---"
    if separator in response:
        parts = response.split(separator, 1)
        summary = parts[0].strip()
        technical = parts[1].strip()
    else:
        summary = response.strip()
        technical = ""

    return {"summary": summary, "technical": technical}


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def compare_solutions(problem_dir="current_query", model=JUDGE_MODEL):
    """
    Compare OptiMUS and OptiMind solutions, pick a winner, and generate
    a professional explanation.

    Writes results to {problem_dir}/final_output/:
        - verdict.json   — structured result for the frontend
        - explanation.txt — full NL explanation

    Returns the verdict dict.
    """
    # Load everything
    problem = load_problem(problem_dir)
    optimus = load_optimus_output(problem_dir)
    optimind = load_optimind_output(problem_dir)

    if not problem["description"]:
        raise FileNotFoundError(f"No problem description found at {problem_dir}/model_input/desc.txt")

    optimus_available = optimus and optimus["available"]
    optimind_available = optimind and optimind["available"]

    if not optimus_available and not optimind_available:
        raise RuntimeError("Neither solver produced output. Nothing to judge.")

    # --- Layer 1: Programmatic triage ---
    # If only one solver has output, it wins by default but we still
    # evaluate its quality and generate the explanation.
    if not optimind_available:
        print("[judge] Only OptiMUS output available. Evaluating OptiMUS solution.")
    elif not optimus_available:
        print("[judge] Only OptiMind output available. Evaluating OptiMind solution.")
    else:
        print("[judge] Both solvers produced output. Comparing solutions.")

    # --- Layer 2: LLM comparison ---
    print("[judge] Calling LLM judge for evaluation...")
    comparison = evaluate_solutions(problem, optimus, optimind, model=model)
    winner_name = comparison.get("winner", "optimus")
    print(f"[judge] Winner: {winner_name}")

    # --- Layer 3: NL explanation ---
    print("[judge] Generating professional explanation...")
    winner_data = optimus if winner_name == "optimus" else optimind
    explanation = generate_explanation(problem, winner_data, comparison, model=model)
    print("[judge] Explanation generated.")

    # --- Build verdict ---
    verdict = {
        "winner": winner_name,
        "objective_value": (
            optimus.get("objective_value") if winner_name == "optimus"
            else (optimind.get("objective_value") if optimind else None)
        ),
        "direction": comparison.get("direction", "unknown"),
        "solvers": {
            "optimus": {
                "status": "success" if optimus_available and optimus.get("objective_value") is not None else
                          "executed" if optimus_available else "not_available",
                "objective_value": optimus.get("objective_value") if optimus else None,
            },
            "optimind": {
                "status": "success" if optimind_available and optimind.get("objective_value") is not None else
                          "executed" if optimind_available else "not_available",
                "objective_value": optimind.get("objective_value") if optimind else None,
            },
        },
        "reasoning": comparison.get("reasoning", ""),
        "optimus_assessment": comparison.get("optimus_assessment", ""),
        "optimind_assessment": comparison.get("optimind_assessment", ""),
        "explanation": explanation["summary"],
        "technical_details": explanation["technical"],
    }

    # --- Write output ---
    output_dir = os.path.join(problem_dir, FINAL_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    verdict_path = os.path.join(output_dir, "verdict.json")
    with open(verdict_path, "w") as f:
        json.dump(verdict, f, indent=2)
    print(f"[judge] Verdict written to {verdict_path}")

    explanation_path = os.path.join(output_dir, "explanation.txt")
    full_explanation = explanation["summary"]
    if explanation["technical"]:
        full_explanation += "\n\n--- TECHNICAL APPENDIX ---\n\n" + explanation["technical"]
    with open(explanation_path, "w") as f:
        f.write(full_explanation)
    print(f"[judge] Explanation written to {explanation_path}")

    return verdict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare OptiMUS and OptiMind solutions, pick a winner"
    )
    parser.add_argument("--dir", type=str, default="current_query",
                        help="Problem directory (default: current_query)")
    parser.add_argument("--model", type=str, default=JUDGE_MODEL,
                        help=f"LLM model for judging (default: {JUDGE_MODEL})")
    args = parser.parse_args()

    verdict = compare_solutions(problem_dir=args.dir, model=args.model)

    print(f"\n{'='*60}")
    print(f"  Winner: {verdict['winner'].upper()}")
    print(f"  Objective: {verdict['objective_value']}")
    print(f"  Reasoning: {verdict['reasoning']}")
    print(f"{'='*60}")
