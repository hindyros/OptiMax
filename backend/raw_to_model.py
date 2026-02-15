#!/usr/bin/env python3
"""
Convert raw user inputs into structured model inputs for the solvers.

Reads:
    current_query/raw_input/raw_desc.txt  - Natural-language problem description
    current_query/raw_input/*.csv         - One or more data CSVs with problem parameters

Writes:
    current_query/model_input/desc.txt    - Cleaned problem description
    current_query/model_input/params.json - Structured parameters with values (merged)

Two modes (chosen automatically):
    - CSV+Text mode: raw_desc.txt + one or more CSVs in raw_input/ -> LLM maps
      columns across all CSVs to parameters (informed by the problem description),
      then a second pass extracts additional numeric constants from the description
      that are NOT in the CSVs (costs, rates, budgets, etc.).  All parameters are
      merged into a single params.json.
    - Text mode: raw_desc.txt only -> LLM extracts params from the description

CLI usage:
    python raw_to_model.py                   # process current_query/
    python raw_to_model.py --dir other_dir   # different problem directory

Programmatic usage:
    from raw_to_model import run_pipeline
    result = run_pipeline("current_query")
"""

from __future__ import annotations

import argparse
import glob as glob_mod
import json
import os
import re
import sys

import pandas as pd

from optimus_pipeline.optimus_utils import get_response, extract_json_from_end

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAW_INPUT_DIR = "raw_input"
MODEL_INPUT_DIR = "model_input"
RAW_DESC_FILE = "raw_desc.txt"
DEFAULT_MODEL = "gpt-4o"

# Special data_column tokens for derived dimensions (not actual columns)
DERIVED_N_ROWS = "__n_rows__"
DERIVED_N_DISTINCT_PREFIX = "__n_distinct__:"


# ---------------------------------------------------------------------------
# Data summary (for the LLM prompt)
# ---------------------------------------------------------------------------


def _build_data_summary(df: pd.DataFrame, max_sample: int = 5) -> str:
    """
    Build a concise summary of the dataset for the LLM.
    Shows column names, dtypes, distinct counts, and sample values.
    """
    n_rows = len(df)
    lines = [
        f"Dataset: {n_rows} rows, {len(df.columns)} columns.",
        "",
        "Columns (use exact names in data_column when referring to a column):",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = df[col].dropna().head(max_sample).tolist()
        sample_str = json.dumps(sample) if sample else "[]"
        try:
            n_distinct = df[col].nunique()
            if n_distinct <= n_rows and n_distinct < 1000:
                lines.append(
                    f'  - "{col}": dtype={dtype}, distinct={n_distinct}, sample={sample_str}'
                )
            else:
                lines.append(f'  - "{col}": dtype={dtype}, sample={sample_str}')
        except Exception:
            lines.append(f'  - "{col}": dtype={dtype}, sample={sample_str}')

    lines.extend([
        "",
        "Derived dimensions (use as data_column when you need a scalar size, not a data column):",
        f'  - "{DERIVED_N_ROWS}" -> total number of rows ({n_rows})',
    ])
    for col in df.columns:
        try:
            n_distinct = df[col].nunique()
            if 1 < n_distinct <= min(n_rows, 500):
                lines.append(
                    f'  - "{DERIVED_N_DISTINCT_PREFIX}{col}" -> '
                    f'number of distinct values in "{col}" ({n_distinct})'
                )
        except Exception:
            pass
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM extraction prompt
# ---------------------------------------------------------------------------


def _build_multi_extraction_prompt(
    description: str,
    dataset_summaries: dict[str, str],
) -> str:
    """Build the prompt that asks the LLM to identify optimization parameters
    across one or more datasets."""

    # Combine per-dataset summaries
    combined = []
    for filename, summary in dataset_summaries.items():
        combined.append(f'--- Dataset: "{filename}" ---\n{summary}')
    datasets_block = "\n\n".join(combined)

    n_datasets = len(dataset_summaries)
    example_source = next(iter(dataset_summaries)) if dataset_summaries else "data.csv"

    return f"""You are an optimization expert. A client has described their business problem and provided {n_datasets} dataset(s). Your job is to identify the PARAMETERS (given data) that will feed into the optimization model.

Think like a consultant:
- Parameters are quantities that appear in the math: coefficients, right-hand sides, capacities, demands, costs, lead times. They must be numeric (or dates converted to numbers).
- ID columns (e.g. ProductId, StoreId) are usually for indexing/dimensions, not numeric parameters. Prefer deriving dimension sizes (e.g. NumberOfProducts) using the derived dimension tokens, and use actual data columns for StockLevels, Capacity, etc.
- Only include parameters the formulation will use.
- Parameters may come from ANY of the provided datasets. Use the correct data_source.

Client description:
-----
{description}
-----

Datasets:
-----
{datasets_block}
-----

Output a single JSON object with one key "parameters" whose value is an array of parameter specs. Each spec must have:
- "symbol": camelCase (e.g. NumberOfProducts, StockLevels, WarehouseCapacity)
- "definition": one short sentence describing the parameter
- "type": "float" or "integer"
- "shape": "[]" for scalar, "[N]" for vector (N = number of rows in the source dataset), "[N,M]" for matrix
- "data_source": the exact filename of the dataset this parameter comes from (one of: {json.dumps(list(dataset_summaries.keys()))})
- "data_column": either (a) exact column name from the source dataset, or (b) a derived token: "{DERIVED_N_ROWS}" for total rows in the source dataset, or "{DERIVED_N_DISTINCT_PREFIX}<ColumnName>" for number of distinct values (e.g. "{DERIVED_N_DISTINCT_PREFIX}Product ID").

Examples:
- Number of products (from "{example_source}"): {{"symbol": "NumberOfProducts", "definition": "Number of products", "type": "integer", "shape": "[]", "data_source": "{example_source}", "data_column": "{DERIVED_N_ROWS}"}}
- Stock level per product: {{"symbol": "StockLevels", "definition": "Current stock for each product", "type": "integer", "shape": "[N]", "data_source": "{example_source}", "data_column": "Stock Levels"}}
- Do NOT include ProductId/StoreId as numeric parameters unless the formulation truly needs them as numbers.

Output only the JSON object, no other text. Use exact column names and dataset filenames as shown above."""


# ---------------------------------------------------------------------------
# Value extraction helpers
# ---------------------------------------------------------------------------


def _resolve_column(df: pd.DataFrame, name: str) -> str:
    """Resolve data_column name to actual DataFrame column (exact or case-insensitive)."""
    if name in df.columns:
        return name
    name_lower = str(name).strip().lower()
    for col in df.columns:
        if col.lower() == name_lower:
            return col
    raise ValueError(f"Column '{name}' not found. Available: {list(df.columns)}")


def _to_json_serializable(val):
    """Coerce numpy/pandas scalars to native Python for JSON."""
    if isinstance(val, (list, tuple)):
        return [_to_json_serializable(x) for x in val]
    if hasattr(val, "item"):
        return val.item()
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return int(val) if val == int(val) else float(val)
    return val


def _looks_like_date(s: str) -> bool:
    """Heuristic: string looks like a date."""
    if not isinstance(s, str) or len(s) < 8:
        return False
    s = s.strip()
    return bool(
        re.match(r"^\d{4}-\d{2}-\d{2}", s)
        or re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", s)
    )


def _ensure_numeric(value, param_type: str):
    """
    Convert date-like strings to ordinal days so Gurobi can use them.
    OptiMUS/OptiMind code expects all parameter values to be numeric.
    """
    if isinstance(value, list):
        if value and isinstance(value[0], str) and _looks_like_date(value[0]):
            try:
                dates = pd.to_datetime(value)
                return (dates - pd.Timestamp("1970-01-01")).days.tolist()
            except Exception:
                pass
        return value
    if isinstance(value, str) and _looks_like_date(value):
        try:
            return int((pd.to_datetime(value) - pd.Timestamp("1970-01-01")).days)
        except Exception:
            pass
    return value


def _shape_string_to_list(shape_str: str, n_rows: int) -> list:
    """Convert shape string like '[]', '[N]', '[N,M]' to list."""
    if not shape_str or shape_str.strip() in ("[]", "''"):
        return []
    s = shape_str.strip().replace(" ", "")
    if s == "[]":
        return []
    if s.upper() in ("[N]", "[n]"):
        return [n_rows]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        out = []
        for p in parts:
            if p.upper() in ("N", "M"):
                out.append(n_rows)
            elif p.isdigit():
                out.append(int(p))
            else:
                out.append(n_rows)
        return out
    return []


def _get_value(df: pd.DataFrame, data_column: str, shape: list):
    """Extract parameter value from DataFrame given column name and shape."""
    col = _resolve_column(df, data_column)
    n_rows = len(df)

    if len(shape) == 0:
        # Scalar: first non-null value
        ser = df[col].dropna()
        if len(ser) == 0:
            raise ValueError(f"Column '{col}' has no non-null values")
        return _to_json_serializable(ser.iloc[0])

    if len(shape) == 1:
        # Vector
        vals = df[col].dropna().tolist()
        n = shape[0]
        if n is not None and n != len(vals):
            vals = vals[:n]
        return _to_json_serializable(vals)

    if len(shape) == 2:
        # Matrix
        vals = df[col].dropna().tolist()
        return _to_json_serializable(vals)

    return None


# ---------------------------------------------------------------------------
# Fallback: simple extraction (no LLM)
# ---------------------------------------------------------------------------


def _simple_extract(df: pd.DataFrame) -> dict:
    """One parameter per column, no LLM. Used as fallback if LLM fails."""
    params = {}
    for col in df.columns:
        name = re.sub(r"[^\w]", "_", str(col)).strip("_")
        if not name:
            name = "param"
        # Deduplicate
        base = name
        c = 0
        while name in params:
            c += 1
            name = f"{base}_{c}"

        series = df[col].dropna()
        vals = series.tolist()
        if not vals:
            continue
        is_int = pd.api.types.is_integer_dtype(series)
        ptype = "integer" if is_int else "float"
        if len(vals) == 1:
            shape, value = [], _to_json_serializable(vals[0])
        else:
            shape, value = [len(vals)], _to_json_serializable(vals)

        value = _ensure_numeric(value, ptype)
        params[name] = {
            "shape": shape,
            "definition": f"From column: {col}",
            "type": ptype,
            "value": value,
        }
    return params


def _multi_simple_extract(datasets: dict[str, pd.DataFrame]) -> dict:
    """One parameter per column across all datasets, no LLM.  Used as fallback
    if the LLM multi-extraction fails.  Symbol names are prefixed with a
    sanitised version of the filename to avoid collisions."""
    params = {}
    for filename, df in datasets.items():
        prefix = re.sub(r"\.csv$", "", filename, flags=re.IGNORECASE)
        prefix = re.sub(r"[^\w]", "_", prefix).strip("_")
        for col in df.columns:
            name = re.sub(r"[^\w]", "_", str(col)).strip("_")
            if not name:
                name = "param"
            full_name = f"{prefix}_{name}"
            # Deduplicate
            base = full_name
            c = 0
            while full_name in params:
                c += 1
                full_name = f"{base}_{c}"

            series = df[col].dropna()
            vals = series.tolist()
            if not vals:
                continue
            is_int = pd.api.types.is_integer_dtype(series)
            ptype = "integer" if is_int else "float"
            if len(vals) == 1:
                shape, value = [], _to_json_serializable(vals[0])
            else:
                shape, value = [len(vals)], _to_json_serializable(vals)

            value = _ensure_numeric(value, ptype)
            params[full_name] = {
                "shape": shape,
                "definition": f"From {filename}, column: {col}",
                "type": ptype,
                "value": value,
            }
    return params


# ---------------------------------------------------------------------------
# Expert extraction (LLM)
# ---------------------------------------------------------------------------


def _multi_expert_extract(
    description: str,
    datasets: dict[str, pd.DataFrame],
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Use an LLM to reason over the description + one or more datasets,
    then produce structured params with values filled from the correct
    DataFrame.  Each parameter spec returned by the LLM includes a
    ``data_source`` that identifies which CSV it comes from.
    """
    # Build per-dataset summaries
    dataset_summaries: dict[str, str] = {}
    for filename, df in datasets.items():
        dataset_summaries[filename] = _build_data_summary(df)

    prompt = _build_multi_extraction_prompt(description, dataset_summaries)

    response = get_response(prompt, model=model)
    raw = extract_json_from_end(response)

    if "parameters" not in raw:
        raise ValueError(f"LLM output missing 'parameters' key. Got: {str(raw)[:200]}")
    specs = raw["parameters"]
    if not isinstance(specs, list):
        raise ValueError(f"'parameters' must be a list. Got: {type(specs)}")

    params = {}
    for item in specs:
        if not isinstance(item, dict):
            continue

        symbol = item.get("symbol")
        definition = item.get("definition", "")
        ptype = item.get("type", "float")
        shape_str = item.get("shape", "[]")
        data_source = item.get("data_source")
        data_column = item.get("data_column")

        if not symbol or data_column is None or data_source is None:
            continue

        # ── Resolve the source DataFrame ──
        ds = str(data_source).strip()
        if ds not in datasets:
            # Try case-insensitive match
            matched = None
            for fn in datasets:
                if fn.lower() == ds.lower():
                    matched = fn
                    break
            if matched:
                ds = matched
            else:
                print(
                    f"  [warn] Skipping param '{symbol}': "
                    f"unknown data_source '{data_source}'",
                    file=sys.stderr,
                )
                continue

        df = datasets[ds]
        n_rows = len(df)

        # Clean symbol
        symbol = re.sub(r"[^\w]", "", str(symbol))
        if not symbol:
            continue
        if symbol[0].islower():
            symbol = symbol[0].upper() + symbol[1:]

        ptype = "integer" if str(ptype).lower() in ("int", "integer") else "float"
        shape = _shape_string_to_list(
            shape_str if isinstance(shape_str, str) else str(shape_str),
            n_rows,
        )

        # Resolve derived dimensions
        dc = str(data_column).strip()
        if dc == DERIVED_N_ROWS:
            value = n_rows
            shape = []
            ptype = "integer"
        elif dc.startswith(DERIVED_N_DISTINCT_PREFIX):
            col_name = dc[len(DERIVED_N_DISTINCT_PREFIX):].strip()
            col_resolved = _resolve_column(df, col_name)
            value = int(df[col_resolved].nunique())
            shape = []
            ptype = "integer"
        else:
            try:
                value = _get_value(df, data_column, shape)
            except Exception as e:
                print(f"  [warn] Skipping param '{symbol}': {e}", file=sys.stderr)
                continue

            value = _ensure_numeric(value, ptype)
            if isinstance(value, list) and value and isinstance(value[0], int):
                ptype = "integer"

        params[symbol] = {
            "shape": shape,
            "definition": definition or f"Parameter {symbol}",
            "type": ptype,
            "value": value,
        }

    return params


# ---------------------------------------------------------------------------
# Description-only extraction (no CSV)
# ---------------------------------------------------------------------------


def _build_desc_only_prompt(description: str) -> str:
    """Prompt that extracts parameters directly from a problem description."""
    return f"""You are an optimization expert. A client has described their business problem in natural language. There is no dataset — all numeric data is embedded in the description itself.

Your job: identify every numeric quantity that would appear as a parameter in the mathematical formulation. Parameters are constants/given data: costs, profits, capacities, demands, limits, rates, counts, etc.

Client description:
-----
{description}
-----

Output a single JSON object with one key "parameters" whose value is an array of parameter specs. Each spec must have:
- "symbol": camelCase identifier (e.g. ProfitA, TotalLabor, WarehouseCapacity)
- "definition": one short sentence describing the parameter
- "type": "float" or "integer"
- "value": the numeric value from the description (scalar number, or list for vectors)

Rules:
- Extract EVERY numeric quantity mentioned that would appear in the math.
- Use clear, descriptive symbol names.
- "type" should be "integer" if the value is a whole number that represents a count or indivisible quantity, otherwise "float".
- For scalar parameters, "value" is a single number.
- Do NOT invent values not present in the description.

Example for "Product A yields $5 profit, B yields $4, 100 hours of labor available":
{{"parameters": [
  {{"symbol": "ProfitA", "definition": "Profit per unit of product A", "type": "float", "value": 5}},
  {{"symbol": "ProfitB", "definition": "Profit per unit of product B", "type": "float", "value": 4}},
  {{"symbol": "TotalLabor", "definition": "Total available labor hours", "type": "float", "value": 100}}
]}}

Output only the JSON object, no other text."""


def _desc_only_extract(description: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Extract parameters directly from a problem description (no CSV).
    The LLM identifies numeric quantities and structures them as params.
    """
    prompt = _build_desc_only_prompt(description)
    response = get_response(prompt, model=model)
    raw = extract_json_from_end(response)

    if "parameters" not in raw:
        raise ValueError(f"LLM output missing 'parameters' key. Got: {str(raw)[:200]}")
    specs = raw["parameters"]
    if not isinstance(specs, list):
        raise ValueError(f"'parameters' must be a list. Got: {type(specs)}")

    params = {}
    for item in specs:
        if not isinstance(item, dict):
            continue

        symbol = item.get("symbol")
        definition = item.get("definition", "")
        ptype = item.get("type", "float")
        value = item.get("value")

        if not symbol or value is None:
            continue

        # Clean symbol
        symbol = re.sub(r"[^\w]", "", str(symbol))
        if not symbol:
            continue
        if symbol[0].islower():
            symbol = symbol[0].upper() + symbol[1:]

        ptype = "integer" if str(ptype).lower() in ("int", "integer") else "float"

        # Determine shape from value
        if isinstance(value, list):
            shape = [len(value)]
            value = _to_json_serializable(value)
        else:
            shape = []
            value = _to_json_serializable(value)

        params[symbol] = {
            "shape": shape,
            "definition": definition or f"Parameter {symbol}",
            "type": ptype,
            "value": value,
        }

    return params


# ---------------------------------------------------------------------------
# Supplement extraction (text params that CSV missed)
# ---------------------------------------------------------------------------


def _build_supplement_prompt(description: str, existing_params: list[str]) -> str:
    """
    Prompt that extracts ONLY the numeric constants from the description that
    are NOT already covered by CSV-sourced parameters.
    """
    existing_list = "\n".join(f"  - {p}" for p in existing_params)
    return f"""You are an optimization expert. A client described a business problem, and a dataset has already been used to extract the following parameters:

Already extracted from dataset:
{existing_list}

Client description:
-----
{description}
-----

Your job: find any ADDITIONAL numeric constants or quantities mentioned in the description that are NOT already covered by the parameters above. These are typically scalar values like costs, rates, budgets, capacities, limits, percentages, or counts that appear in the prose but not in the data.

Rules:
- ONLY extract parameters whose values appear explicitly in the description text.
- Do NOT re-extract anything already covered above (even under a different name).
- Do NOT invent values. If no additional parameters exist, return {{"parameters": []}}.
- Use clear, descriptive camelCase symbol names.
- "type" should be "integer" for whole-number counts, "float" otherwise.

Output a single JSON object with one key "parameters" whose value is an array. Each spec:
- "symbol": camelCase identifier
- "definition": one short sentence
- "type": "float" or "integer"
- "value": the numeric value from the description

Output only the JSON object, no other text."""


def _supplement_extract(
    description: str,
    existing_params: list[str],
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Extract additional parameters from the description that the CSV extraction
    missed.  Returns a dict of param_name -> param_spec (same format as other
    extractors).  Returns empty dict if nothing extra is found.
    """
    prompt = _build_supplement_prompt(description, existing_params)
    try:
        response = get_response(prompt, model=model)
        raw = extract_json_from_end(response)
    except Exception as e:
        print(f"  [warn] Supplement extraction failed: {e}", file=sys.stderr)
        return {}

    if "parameters" not in raw:
        return {}
    specs = raw["parameters"]
    if not isinstance(specs, list):
        return {}

    params = {}
    for item in specs:
        if not isinstance(item, dict):
            continue

        symbol = item.get("symbol")
        definition = item.get("definition", "")
        ptype = item.get("type", "float")
        value = item.get("value")

        if not symbol or value is None:
            continue

        # Clean symbol
        symbol = re.sub(r"[^\w]", "", str(symbol))
        if not symbol:
            continue
        if symbol[0].islower():
            symbol = symbol[0].upper() + symbol[1:]

        ptype = "integer" if str(ptype).lower() in ("int", "integer") else "float"

        # Determine shape from value
        if isinstance(value, list):
            shape = [len(value)]
            value = _to_json_serializable(value)
        else:
            shape = []
            value = _to_json_serializable(value)

        params[symbol] = {
            "shape": shape,
            "definition": definition or f"Parameter {symbol}",
            "type": ptype,
            "value": value,
        }

    return params


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    problem_dir: str = "current_query",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Convert raw_input/ into model_input/.

    Two modes (chosen automatically):
        - CSV+Text mode: raw_desc.txt + one or more *.csv files in raw_input/
          -> LLM maps columns across ALL CSVs to parameters (guided by the
          problem description), then a second pass extracts additional numeric
          constants from the description that are NOT in the CSVs.  Everything
          is merged into a single params.json.
        - Text mode: only raw_desc.txt exists -> LLM extracts params from
          the description.

    Writes:
        {problem_dir}/model_input/desc.txt
        {problem_dir}/model_input/params.json

    Returns:
        dict with keys: description, params
    """
    raw_dir = os.path.join(problem_dir, RAW_INPUT_DIR)
    model_dir = os.path.join(problem_dir, MODEL_INPUT_DIR)

    # ---- Validate inputs ----
    desc_path = os.path.join(raw_dir, RAW_DESC_FILE)
    if not os.path.isfile(desc_path):
        raise FileNotFoundError(
            f"Missing {desc_path}\n"
            f"Place your problem description in {raw_dir}/{RAW_DESC_FILE}"
        )

    # Discover all CSVs in raw_input/
    csv_paths = sorted(glob_mod.glob(os.path.join(raw_dir, "*.csv")))
    has_csv = len(csv_paths) > 0

    # ---- Read description ----
    with open(desc_path) as f:
        description = f.read().strip()
    if not description:
        raise ValueError(f"{desc_path} is empty.")

    print(f"\n{'=' * 60}")
    print("raw_to_model")
    print(f"{'=' * 60}")
    print(f"Description: {description[:150]}{'...' if len(description) > 150 else ''}")

    if has_csv:
        # ---- CSV+Text mode: description + one or more datasets ----
        datasets: dict[str, pd.DataFrame] = {}
        for csv_path in csv_paths:
            filename = os.path.basename(csv_path)
            df = pd.read_csv(csv_path)
            datasets[filename] = df
            print(f"Dataset '{filename}': {len(df)} rows, {len(df.columns)} columns")
            print(f"  Columns: {list(df.columns)}")

        print()
        print(f"Extracting parameters from {len(datasets)} dataset(s) (expert mode)...")
        try:
            params = _multi_expert_extract(description, datasets, model=model)
            if not params:
                raise ValueError("LLM returned zero parameters")
            print(f"  Dataset extraction: {len(params)} parameters.")
        except Exception as e:
            print(f"[warn] Multi-dataset extraction failed: {e}", file=sys.stderr)
            print("Falling back to simple mode (one param per column).", file=sys.stderr)
            params = _multi_simple_extract(datasets)

        # ---- Supplement: extract text-only params the CSVs missed ----
        print("Extracting additional parameters from description text...")
        supplement = _supplement_extract(
            description, list(params.keys()), model=model
        )
        if supplement:
            # Merge: dataset params take priority, supplement fills gaps
            added = []
            for sym, spec in supplement.items():
                if sym not in params:
                    params[sym] = spec
                    added.append(sym)
            if added:
                print(f"  Text supplement: +{len(added)} parameters: {added}")
            else:
                print("  Text supplement: no new parameters (all covered by datasets).")
        else:
            print("  Text supplement: no additional parameters found.")
    else:
        # ---- Text mode: description only ----
        print("No CSVs found. Extracting parameters directly from description...")
        print()
        params = _desc_only_extract(description, model=model)
        if params:
            print(f"LLM extracted {len(params)} parameters from description.")
        else:
            raise RuntimeError(
                "LLM could not extract any parameters from the description. "
                "Try providing one or more .csv files in raw_input/."
            )

    if not params:
        raise RuntimeError("No parameters could be extracted.")

    # ---- Write model inputs ----
    os.makedirs(model_dir, exist_ok=True)

    desc_out = os.path.join(model_dir, "desc.txt")
    with open(desc_out, "w") as f:
        f.write(description)

    params_out = os.path.join(model_dir, "params.json")
    with open(params_out, "w") as f:
        json.dump(params, f, indent=4)

    print(f"\nWrote model inputs:")
    print(f"  {desc_out}")
    print(f"  {params_out} ({len(params)} parameters)")
    print(f"\nParameters: {list(params.keys())}")
    print()

    return {"description": description, "params": params}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert raw_input/ (desc + one or more CSVs) into model_input/ (desc.txt + params.json)"
    )
    parser.add_argument(
        "--dir", type=str, default="current_query",
        help="Problem directory (default: current_query)",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"LLM model for parameter extraction (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    run_pipeline(problem_dir=args.dir, model=args.model)
