"""OptiMind pipeline — client for Microsoft OptiMind-SFT."""

from .optimind import (
    OptimindResult,
    get_client,
    query_model,
    run_optimind,
    run_test,
    extract_python_blocks,
    check_gurobipy,
    pick_best_code_block,
    execute_gurobi_code,
    parse_objective_value,
    SAMPLE_PROBLEMS,
    SYSTEM_PROMPT,
)

__all__ = [
    "OptimindResult",
    "get_client",
    "query_model",
    "run_optimind",
    "run_test",
    "extract_python_blocks",
    "check_gurobipy",
    "pick_best_code_block",
    "execute_gurobi_code",
    "parse_objective_value",
    "SAMPLE_PROBLEMS",
    "SYSTEM_PROMPT",
]
