"""
OptiMUS solver entry point.

CLI usage:
    python optimus.py --clear              # Step 1: archive + wipe workspace
    # ... place desc.txt, params.json, labels.json into current_query/ ...
    python optimus.py                      # Step 2: run the pipeline

Programmatic usage:
    from optimus import run_pipeline
    state = run_pipeline("current_query")
"""

import os
import argparse

from optimus_pipeline import (
    get_params,
    get_constraints,
    get_constraint_formulations,
    get_codes,
    generate_code,
    get_objective,
    get_objective_formulation,
    execute_and_debug,
)
from optimus_utils import load_state, save_state, Logger, create_state, get_labels
from optimus_rag.rag_utils import RAGMode
from query_manager import prepare_workspace

OUTPUT_DIR = "output"
DEFAULT_MODEL = "gpt-4o-mini"


def run_pipeline(
    problem_dir="current_query",
    rag_mode=None,
    model=DEFAULT_MODEL,
    error_correction=True,
):
    """
    Run the full OptiMUS pipeline on a problem directory.

    Expects the workspace to already contain desc.txt, params.json, and
    labels.json.  Use prepare_workspace() or ``python optimus.py --clear``
    to archive and wipe old results *before* placing new input files.

    Args:
        problem_dir:      Path to the problem folder.
        rag_mode:         RAGMode enum or None.
        model:            LLM model identifier.
        error_correction: Enable self-correction checks at each step.

    Returns:
        dict: The final pipeline state.
    """
    run_dir = os.path.join(problem_dir, OUTPUT_DIR)
    os.makedirs(run_dir, exist_ok=True)

    # Initialize state from problem description + params
    state = create_state(problem_dir, run_dir)
    labels = get_labels(problem_dir)
    save_state(state, os.path.join(run_dir, "state_1_params.json"))

    logger = Logger(os.path.join(run_dir, "log.txt"))
    logger.reset()

    # Step 2: Extract objective
    state = load_state(os.path.join(run_dir, "state_1_params.json"))
    objective = get_objective(
        state["description"],
        state["parameters"],
        check=error_correction,
        logger=logger,
        model=model,
        rag_mode=rag_mode,
        labels=labels,
    )
    print(objective)
    state["objective"] = objective
    save_state(state, os.path.join(run_dir, "state_2_objective.json"))

    # Step 3: Extract constraints
    state = load_state(os.path.join(run_dir, "state_2_objective.json"))
    constraints = get_constraints(
        state["description"],
        state["parameters"],
        check=error_correction,
        logger=logger,
        model=model,
        rag_mode=rag_mode,
        labels=labels,
    )
    print(constraints)
    state["constraints"] = constraints
    save_state(state, os.path.join(run_dir, "state_3_constraints.json"))

    # Step 4: Formulate constraints (LaTeX)
    state = load_state(os.path.join(run_dir, "state_3_constraints.json"))
    constraints, variables = get_constraint_formulations(
        state["description"],
        state["parameters"],
        state["constraints"],
        check=error_correction,
        logger=logger,
        model=model,
        rag_mode=rag_mode,
        labels=labels,
    )
    state["constraints"] = constraints
    state["variables"] = variables
    save_state(state, os.path.join(run_dir, "state_4_constraints_modeled.json"))

    # Step 5: Formulate objective (LaTeX)
    state = load_state(os.path.join(run_dir, "state_4_constraints_modeled.json"))
    objective = get_objective_formulation(
        state["description"],
        state["parameters"],
        state["variables"],
        state["objective"],
        model=model,
        check=error_correction,
        rag_mode=rag_mode,
        labels=labels,
    )
    state["objective"] = objective
    print("DONE OBJECTIVE FORMULATION")
    save_state(state, os.path.join(run_dir, "state_5_objective_modeled.json"))

    # Step 6: Generate code for constraints + objective
    state = load_state(os.path.join(run_dir, "state_5_objective_modeled.json"))
    constraints, objective = get_codes(
        state["description"],
        state["parameters"],
        state["variables"],
        state["constraints"],
        state["objective"],
        model=model,
        check=error_correction,
    )
    state["constraints"] = constraints
    state["objective"] = objective
    save_state(state, os.path.join(run_dir, "state_6_code.json"))

    # Steps 7-8: Assemble and execute code
    state = load_state(os.path.join(run_dir, "state_6_code.json"))
    generate_code(state, run_dir)
    execute_and_debug(state, model=model, dir=run_dir, logger=logger)

    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the OptiMUS optimization pipeline")
    parser.add_argument("--dir", type=str, default="current_query",
                        help="Problem directory (default: current_query)")
    parser.add_argument("--clear", action="store_true",
                        help="Archive old results, wipe workspace, then exit. "
                             "Place new input files afterward, then run again without --clear.")
    parser.add_argument("--no-archive", action="store_true",
                        help="When used with --clear, skip archiving (just wipe)")
    parser.add_argument("--rag-mode", type=RAGMode, choices=list(RAGMode),
                        default=None, help="RAG retrieval mode")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"LLM model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    if args.clear:
        prepare_workspace(query_dir=args.dir, archive=not args.no_archive)
        print(f"\nWorkspace '{args.dir}/' is ready. Place your input files:")
        print(f"  {args.dir}/desc.txt       - Problem description")
        print(f"  {args.dir}/params.json    - Parameters with values")
        print(f"  {args.dir}/labels.json    - Problem category labels")
        print(f"\nThen run:  python optimus.py")
    else:
        run_pipeline(
            problem_dir=args.dir,
            rag_mode=args.rag_mode,
            model=args.model,
            error_correction=True,
        )
