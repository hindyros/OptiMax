#!/usr/bin/env python3
"""
Optimization Consultant — generates a professional report for the winning
solution, including baseline comparison and technical appendix.

Reads:
    final_output/verdict.json      - Judge's comparison result
    model_input/desc.txt           - Problem description
    model_input/params.json        - Structured parameters
    model_input/baseline.txt       - Client's current baseline strategy
    Winner's solver output         - Code, execution output, objective value

Writes:
    final_output/report.md         - Full professional Markdown report
    final_output/verdict.json      - Enriched with report summary fields

CLI usage:
    python consultant.py                       # run on current_query/
    python consultant.py --dir current_query   # explicit directory

Programmatic usage:
    from consultant import generate_report
    report = generate_report("current_query")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from optimus_pipeline.optimus_utils import get_response

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONSULTANT_MODEL = "gpt-4o"
FINAL_OUTPUT_DIR = "final_output"


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _read_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        text = f.read().strip()
    return text or None


def _read_json(path: str) -> dict | None:
    text = _read_file(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Parameter summarization (keep prompts compact)
# ---------------------------------------------------------------------------


def _summarize_params_for_prompt(
    params: dict,
    max_vector_display: int = 10,
) -> str:
    """
    Produce a compact summary of parameters for the consultant prompt.

    Scalars and small vectors (≤ *max_vector_display* elements) are shown in
    full.  Large vectors are replaced with summary statistics so the LLM can
    still reason about the data without consuming thousands of tokens.
    """
    if not params:
        return "{}"

    summary: dict = {}
    for name, spec in params.items():
        value = spec.get("value")
        definition = spec.get("definition", "")
        shape = spec.get("shape", [])
        ptype = spec.get("type", "float")

        entry: dict = {
            "definition": definition,
            "type": ptype,
            "shape": shape,
        }

        if isinstance(value, list) and len(value) > max_vector_display:
            numeric_vals = [v for v in value if isinstance(v, (int, float))]
            if numeric_vals:
                entry["count"] = len(value)
                entry["min"] = min(numeric_vals)
                entry["max"] = max(numeric_vals)
                entry["mean"] = round(sum(numeric_vals) / len(numeric_vals), 4)
                entry["sample (first 5)"] = value[:5]
                entry["note"] = f"Vector of {len(value)} values (summarized)"
            else:
                entry["value"] = value[:max_vector_display]
                entry["note"] = (
                    f"Showing first {max_vector_display} of {len(value)} values"
                )
        else:
            entry["value"] = value

        summary[name] = entry

    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# Gurobi statistics parser
# ---------------------------------------------------------------------------


def _parse_gurobi_stats(code_output: str | None) -> dict:
    """
    Extract key solver statistics from Gurobi's stdout/stderr.

    Returns a dict with any of: mip_gap, solve_time, nodes_explored,
    status_detail, best_objective, best_bound.
    """
    stats: dict = {}
    if not code_output:
        return stats

    # MIP Gap: "Best objective 2.800e+02, best bound 2.800e+02, gap 0.0000%"
    gap_match = re.search(
        r"Best objective\s+([\d.e+\-]+),\s*best bound\s+([\d.e+\-]+),\s*gap\s+([\d.]+)%",
        code_output,
    )
    if gap_match:
        stats["best_objective"] = float(gap_match.group(1))
        stats["best_bound"] = float(gap_match.group(2))
        stats["mip_gap_pct"] = float(gap_match.group(3))

    # Solve time: "Solved in X iterations and Y seconds"
    time_match = re.search(r"in\s+\d+\s+iterations?\s+and\s+([\d.]+)\s+seconds?", code_output)
    if time_match:
        stats["solve_time_s"] = float(time_match.group(1))

    # Nodes: "Explored X nodes"
    nodes_match = re.search(r"Explored\s+(\d+)\s+nodes?", code_output)
    if nodes_match:
        stats["nodes_explored"] = int(nodes_match.group(1))

    # Optimal solution found (tolerance ...)
    if "Optimal solution found" in code_output:
        stats["status_detail"] = "Optimal solution found"
    elif "Time limit reached" in code_output:
        stats["status_detail"] = "Time limit reached"

    return stats


# ---------------------------------------------------------------------------
# Context loader
# ---------------------------------------------------------------------------


def _load_context(problem_dir: str) -> dict:
    """Load all inputs needed for the consultant report."""
    model_dir = os.path.join(problem_dir, "model_input")
    final_dir = os.path.join(problem_dir, FINAL_OUTPUT_DIR)

    # Problem inputs
    description = _read_file(os.path.join(model_dir, "desc.txt"))
    parameters = _read_json(os.path.join(model_dir, "params.json"))
    baseline = _read_file(os.path.join(model_dir, "baseline.txt"))

    # Verdict from judge
    verdict = _read_json(os.path.join(final_dir, "verdict.json"))
    if not verdict:
        raise FileNotFoundError(
            f"No verdict.json found in {final_dir}/. Run judge.py first."
        )

    # Winner's solver output
    winner_name = verdict["winner"]
    if winner_name == "optimus":
        out_dir = os.path.join(problem_dir, "optimus_output")
        code = _read_file(os.path.join(out_dir, "code.py"))
        code_output = _read_file(os.path.join(out_dir, "code_output.txt"))
        state = _read_json(os.path.join(out_dir, "state_6_code.json"))
    else:
        out_dir = os.path.join(problem_dir, "optimind_output")
        code = _read_file(os.path.join(out_dir, "optimind_code.py"))
        code_output = _read_file(os.path.join(out_dir, "code_output.txt"))
        state = None  # OptiMind doesn't have structured state

    # Parse Gurobi statistics from solver output
    gurobi_stats = _parse_gurobi_stats(code_output)

    return {
        "description": description,
        "parameters": parameters,
        "baseline": baseline,
        "verdict": verdict,
        "winner_name": winner_name,
        "code": code,
        "code_output": code_output,
        "state": state,
        "gurobi_stats": gurobi_stats,
    }


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _format_winner_details(ctx: dict) -> str:
    """Build a rich summary of the winning solution for the consultant."""
    parts = []

    parts.append(f"Winner: {ctx['winner_name'].upper()}")
    parts.append(f"Objective value: {ctx['verdict'].get('objective_value', 'N/A')}")
    parts.append(f"Direction: {ctx['verdict'].get('direction', 'unknown')}")
    parts.append(f"Solver status: {ctx['verdict']['solvers'][ctx['winner_name']]['status']}")

    # Formulation details (OptiMUS only)
    state = ctx.get("state")
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
            parts.append(f"\nDecision Variables ({len(variables)}):")
            for name, info in variables.items():
                parts.append(f"  {name}: {info.get('definition', 'N/A')} ({info.get('type', 'N/A')})")

    # Gurobi stats
    gs = ctx.get("gurobi_stats", {})
    if gs:
        parts.append("\nSolver Statistics:")
        if "mip_gap_pct" in gs:
            parts.append(f"  MIP Gap: {gs['mip_gap_pct']}%")
        if "solve_time_s" in gs:
            parts.append(f"  Solve time: {gs['solve_time_s']}s")
        if "nodes_explored" in gs:
            parts.append(f"  Nodes explored: {gs['nodes_explored']}")
        if "best_bound" in gs:
            parts.append(f"  Best bound: {gs['best_bound']}")

    # Code
    if ctx.get("code"):
        parts.append(f"\nGenerated Code:\n```python\n{ctx['code']}\n```")

    # Execution output
    if ctx.get("code_output"):
        parts.append(f"\nFull Execution Output:\n{ctx['code_output']}")

    return "\n".join(parts)


def _build_prompt(ctx: dict) -> str:
    """Build the full consultant prompt."""
    winner_details = _format_winner_details(ctx)

    baseline_section = ""
    if ctx.get("baseline"):
        baseline_section = f"""
## Client's Current Baseline Strategy

{ctx['baseline']}

"""

    baseline_instructions = ""
    if ctx.get("baseline"):
        baseline_instructions = """
## Baseline Comparison

Compare the optimized solution against the client's current baseline strategy.
Present a comparison table:

| Metric | Current (Baseline) | Optimized | Change |
|--------|-------------------|-----------|--------|
| ... | ... | ... | ... |

Include:
- Summarize the baseline approach in 1-2 sentences
- Quantify the improvement (objective value, %, absolute delta)
- Identify what specifically changes from baseline to optimized
- Note any baseline practices that are already optimal and should be maintained
- Assess practical feasibility of transitioning from baseline to optimized
- If the baseline does not provide enough numerical detail for exact comparison,
  make reasonable inferences and note your assumptions
"""
    else:
        baseline_instructions = """
## Baseline Comparison

*Note: No baseline strategy was provided. Skip this section and note that
a baseline comparison was not possible.*
"""

    gap_instructions = ""
    gs = ctx.get("gurobi_stats", {})
    if "mip_gap_pct" in gs:
        gap_instructions = f"""
The solver reported a MIP gap of {gs['mip_gap_pct']}%. Interpret this for
both audiences: explain what it means for solution quality in the executive
summary (e.g. "the solution is proven optimal" or "within X% of the best
possible"), and give the precise gap and bound in the technical appendix.
"""

    return f"""\
You are a senior optimization consultant at a top-tier management consulting
firm. You have just completed an optimization engagement for a client and must
now deliver a comprehensive, polished report.

Your tone: authoritative, precise, client-ready. In the executive summary you
speak plainly to C-suite executives — no jargon, no math, concrete numbers
and actions. In the technical appendix you speak to engineers and data
scientists — full mathematical rigor, solver details, code.

# Inputs

## Problem Description

{ctx['description'] or '(no description)'}

## Parameters

{_summarize_params_for_prompt(ctx.get('parameters') or {})}
{baseline_section}
## Winning Solution

{winner_details}

## Judge's Assessment

{ctx['verdict'].get('reasoning', 'N/A')}
{gap_instructions}

# Report Structure

Produce a Markdown report with EXACTLY these sections. Use ## for top-level
headings and ### for subsections.

## Problem Statement

Reproduce the client's problem description verbatim as a blockquote
(use > prefix). Then add 1-2 sentences summarizing the core optimization
question in your own words.

## Executive Summary

Write for executives. No math, no code. Be specific and concrete:
- What was the business problem and why it matters
- What the optimal solution recommends — cite SPECIFIC numbers, quantities,
  allocations, and the CONDITIONS/CONSTRAINTS that shape them
- The bottom-line impact (objective value in business terms: "$X profit",
  "Y% cost reduction", etc.)
- Key trade-offs, caveats, or implementation considerations
- If the solution achieves the global optimum, state this clearly
{baseline_instructions}
## Key Recommendations

Numbered, actionable steps the client should take. Be concrete:
"Increase production of Product A to 40 units/week" not "Adjust production."

---

## Technical Appendix

The entire Technical Appendix must be written in a rigorous, publication-quality
mathematical style. Use LaTeX math heavily throughout — every formula, every
variable reference, every constraint must be typeset as math. This section is
for engineers and data scientists who expect the level of detail found in an
optimization textbook or journal paper.

CRITICAL FORMATTING RULE: Use $...$ for ALL inline math and $$...$$ on its
own line for ALL display math. NEVER use \\(...\\) or \\[...\\] delimiters.

### Problem Formulation

Present a complete mathematical program:

1. **Sets and indices** — define any index sets (e.g. $i \\in \\{{1, \\ldots, n\\}}$)
2. **Parameters** — list all given data with symbols, definitions, and values
   in a Markdown table: | Symbol | Definition | Value |
3. **Decision variables** — define each variable with symbol, domain, and bounds
4. **Objective function** — state maximize/minimize and write the full objective
   as a display-math equation using $$...$$
5. **Constraints** — number each constraint, write it as display math, and add
   a brief note on what it encodes

### Optimal Solution

Present a table of decision variable values at optimum:
| Variable | Value | Description |

Then discuss:
- Which constraints are **active (binding)** at the optimum? Why does this
  matter?
- Which constraints have **slack**? What does the slack value mean?
- Any sensitivity or robustness observations from the solver output

### Solver Statistics

Present as a clean table:
| Metric | Value |
Including: solver status, objective value, MIP gap (if applicable), best bound,
solve time, iterations, nodes explored (where available).

### Generated Code

Include the full solver code in a ```python code block.

---

Output ONLY the Markdown report. Do not wrap it in code fences or add
preamble/postamble text."""


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    problem_dir: str = "current_query",
    model: str = CONSULTANT_MODEL,
) -> dict:
    """
    Generate a professional optimization report.

    Reads verdict.json (from judge), solver outputs, baseline, and parameters.
    Writes report.md and enriches verdict.json with summary fields.

    Returns dict with keys: report_md, executive_summary.
    """
    print(f"\n{'=' * 60}")
    print("Consultant")
    print(f"{'=' * 60}")

    # ── Load context ──
    ctx = _load_context(problem_dir)
    has_baseline = ctx.get("baseline") is not None

    print(f"Winner: {ctx['winner_name']}")
    print(f"Objective: {ctx['verdict'].get('objective_value')}")
    print(f"Baseline: {'provided' if has_baseline else 'not provided'}")
    print()

    # ── Generate report ──
    print("[consultant] Generating report...")
    prompt = _build_prompt(ctx)
    report_md = get_response(prompt, model=model)
    print("[consultant] Report generated.")

    # ── Extract executive summary for JSON ──
    exec_summary = ""
    match = re.search(
        r"## Executive Summary\s*\n(.*?)(?=\n## )", report_md, re.DOTALL
    )
    if match:
        exec_summary = match.group(1).strip()

    # ── Write report.md ──
    output_dir = os.path.join(problem_dir, FINAL_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w") as f:
        f.write(report_md)
    print(f"[consultant] Report written to {report_path}")

    # ── Enrich verdict.json ──
    verdict_path = os.path.join(output_dir, "verdict.json")
    verdict = ctx["verdict"]
    verdict["executive_summary"] = exec_summary
    verdict["has_baseline_comparison"] = has_baseline
    verdict["gurobi_stats"] = ctx.get("gurobi_stats", {})

    with open(verdict_path, "w") as f:
        json.dump(verdict, f, indent=2)
    print(f"[consultant] Verdict enriched at {verdict_path}")

    print()
    return {"report_md": report_md, "executive_summary": exec_summary}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a professional optimization report"
    )
    parser.add_argument(
        "--dir", type=str, default="current_query",
        help="Problem directory (default: current_query)",
    )
    parser.add_argument(
        "--model", type=str, default=CONSULTANT_MODEL,
        help=f"LLM model (default: {CONSULTANT_MODEL})",
    )
    args = parser.parse_args()

    result = generate_report(problem_dir=args.dir, model=args.model)

    print(f"Report length: {len(result['report_md'])} chars")
    print(f"Executive summary: {result['executive_summary'][:200]}...")
