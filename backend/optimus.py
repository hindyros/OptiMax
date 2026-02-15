"""
OptiMUS solver entry point.

CLI usage:
    python query_manager.py                # Step 1: archive + wipe workspace
    # ... place desc.txt, params.json into current_query/model_input/ ...
    python optimus.py                      # Step 2: run the pipeline

Programmatic usage:
    from optimus import run_pipeline
    state = run_pipeline("current_query")
"""

import os
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

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
from optimus_pipeline.optimus_utils import load_state, save_state, Logger, create_state

OUTPUT_DIR = "optimus_output"
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class _ThreadSafeLogger:
    """Wrapper around Logger that serialises writes with a lock."""

    def __init__(self, logger):
        self._logger = logger
        self._lock = threading.Lock()

    def log(self, text):
        with self._lock:
            self._logger.log(text)

    def reset(self):
        with self._lock:
            self._logger.reset()


def run_pipeline(
    problem_dir="current_query",
    model=DEFAULT_MODEL,
    error_correction=True,
):
    """
    Run the full OptiMUS pipeline on a problem directory.

    Expects the workspace to already contain model_input/desc.txt and model_input/params.json.
    Use prepare_workspace() or ``python query_manager.py``
    to archive and wipe old results *before* placing new input files.

    Args:
        problem_dir:      Path to the problem folder.
        model:            LLM model identifier.
        error_correction: Enable self-correction checks at each step.

    Returns:
        dict: The final pipeline state.
    """
    run_dir = os.path.join(problem_dir, OUTPUT_DIR)
    os.makedirs(run_dir, exist_ok=True)

    # Initialize state from problem description + params
    state = create_state(problem_dir, run_dir)
    save_state(state, os.path.join(run_dir, "state_1_params.json"))

    raw_logger = Logger(os.path.join(run_dir, "log.txt"))
    raw_logger.reset()
    logger = _ThreadSafeLogger(raw_logger)

    # Steps 2+3: Extract objective and constraints in parallel
    # (both depend only on description + parameters)
    state = load_state(os.path.join(run_dir, "state_1_params.json"))
    desc = state["description"]
    params = state["parameters"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        obj_future = executor.submit(
            get_objective, desc, params,
            check=error_correction, logger=logger, model=model,
        )
        con_future = executor.submit(
            get_constraints, desc, params,
            check=error_correction, logger=logger, model=model,
        )
        objective = obj_future.result()
        constraints = con_future.result()

    print(objective)
    print(constraints)

    state["objective"] = objective
    state["constraints"] = constraints
    save_state(state, os.path.join(run_dir, "state_2_objective.json"))
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
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"LLM model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    run_pipeline(
        problem_dir=args.dir,
        model=args.model,
        error_correction=True,
    )
