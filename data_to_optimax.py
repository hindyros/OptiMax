#!/usr/bin/env python3
"""
Convert a CSV/Excel data file + natural-language problem description into
OptiMUS input files: desc.txt, params.json.

Writes:
  - current_query/raw_input/   — natural-language description + raw data CSV(s)
  - current_query/model_input/ — desc.txt, params.json

Run this script first, then run OptiMUS with no extra args.

Two modes:
- Expert (default with LLM): An LLM reasons over the description and dataset
  to identify parameters, map columns to concepts, and fill shape/type/definition.
- Simple (--no-llm or --simple): One parameter per column with inferred shape/type.

Usage:
    python data_to_optimax.py --data my_data.csv --description "Maximize profit..."
    python data_to_optimax.py --data sheet.xlsx --description desc.txt
    python data_to_optimax.py --data inventory.csv stores.csv --description desc.txt
    # Then: python optimus.py
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd


# -----------------------------------------------------------------------------
# Expert parameter extraction: LLM reasons over description + data
# -----------------------------------------------------------------------------

# Special data_column values for derived parameters (no actual column)
DERIVED_N_ROWS = "__n_rows__"
DERIVED_N_DISTINCT_PREFIX = "__n_distinct__:"


def _dataset_name_from_path(path: str) -> str:
    """Return a short name for the dataset (filename without extension)."""
    return Path(path).stem or "data"


def _build_data_summary(df: pd.DataFrame, max_sample: int = 5) -> str:
    """Build a concise summary of the dataset for the LLM (real-life: what a client would share)."""
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
        # For columns that look like IDs, show distinct count so the LLM can suggest NumberOfProducts etc.
        try:
            n_distinct = df[col].nunique()
            if n_distinct <= n_rows and n_distinct < 1000:
                lines.append(f"  - \"{col}\": dtype={dtype}, distinct={n_distinct}, sample={sample_str}")
            else:
                lines.append(f"  - \"{col}\": dtype={dtype}, sample={sample_str}")
        except Exception:
            lines.append(f"  - \"{col}\": dtype={dtype}, sample={sample_str}")
    lines.extend([
        "",
        "Derived dimensions (use as data_column when you need a scalar size for the model, not a data column):",
        f"  - \"{DERIVED_N_ROWS}\" → total number of rows ({n_rows})",
    ])
    for col in df.columns:
        try:
            n_distinct = df[col].nunique()
            if 1 < n_distinct <= min(n_rows, 500):
                lines.append(f"  - \"{DERIVED_N_DISTINCT_PREFIX}{col}\" → number of distinct values in \"{col}\" ({n_distinct})")
        except Exception:
            pass
    return "\n".join(lines)


def _build_data_summary_multi(
    datasets: list[tuple[str, pd.DataFrame]],
    max_sample: int = 5,
) -> str:
    """Build a summary of multiple datasets for the LLM. Each dataset is named (e.g. by filename stem)."""
    parts = []
    for name, df in datasets:
        n_rows = len(df)
        lines = [
            f"Dataset \"{name}\": {n_rows} rows, {len(df.columns)} columns.",
            "  Columns (use exact names in data_column when referring to this dataset):",
        ]
        for col in df.columns:
            dtype = str(df[col].dtype)
            sample = df[col].dropna().head(max_sample).tolist()
            sample_str = json.dumps(sample) if sample else "[]"
            try:
                n_distinct = df[col].nunique()
                if n_distinct <= n_rows and n_distinct < 1000:
                    lines.append(f"    - \"{col}\": dtype={dtype}, distinct={n_distinct}, sample={sample_str}")
                else:
                    lines.append(f"    - \"{col}\": dtype={dtype}, sample={sample_str}")
            except Exception:
                lines.append(f"    - \"{col}\": dtype={dtype}, sample={sample_str}")
        lines.extend([
            "  Derived dimensions (use as data_column for this dataset only):",
            f"    - \"{DERIVED_N_ROWS}\" → number of rows in this dataset ({n_rows})",
        ])
        for col in df.columns:
            try:
                n_distinct = df[col].nunique()
                if 1 < n_distinct <= min(n_rows, 500):
                    lines.append(f"    - \"{DERIVED_N_DISTINCT_PREFIX}{col}\" → distinct values in \"{col}\" ({n_distinct})")
            except Exception:
                pass
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _expert_extract_params_prompt(
    description: str,
    data_summary: str,
    *,
    multi_dataset: bool = False,
) -> str:
    data_spec = (
        'For each parameter specify "data_source": the exact dataset name from the list above (e.g. "inventory", "stores"), and "data_column": column name or derived token for that dataset.'
        if multi_dataset
        else f'"data_column": either (a) exact column name from the list above, or (b) a derived token: "{DERIVED_N_ROWS}" for total rows, or "{DERIVED_N_DISTINCT_PREFIX}<ColumnName>" for number of distinct values (e.g. "{DERIVED_N_DISTINCT_PREFIX}Product ID").'
    )
    data_source_line = (
        '- "data_source": exact dataset name (required when multiple datasets are listed above)'
        if multi_dataset
        else ""
    )
    return f"""You are an optimization expert. A client has described their business problem and provided one or more datasets. Your job is to identify the PARAMETERS (given data) that will feed into the optimization model—the same way you would when a client sends you a brief and several spreadsheets.

Think like a consultant:
- Parameters are quantities that appear in the math: coefficients, right-hand sides, capacities, demands, costs, lead times. They must be numeric (or dates converted to numbers).
- ID columns (e.g. ProductId, StoreId) are usually for indexing and dimensions, not for use as numeric parameters in the objective. Prefer deriving dimension sizes (e.g. NumberOfProducts, NumberOfStores) using the derived dimension tokens, and use the actual data columns for StockLevels, ReorderPoint, Capacity, etc.
- When multiple datasets are provided, each parameter comes from exactly one dataset. Use "data_source" to indicate which dataset (by its name as shown below).
- Only include parameters that the formulation will use.

Client description:
-----
{description}
-----

Dataset(s) summary:
-----
{data_summary}
-----

Output a single JSON object with one key "parameters" whose value is an array of parameter specs. Each spec must have:
- "symbol": camelCase (e.g. NumberOfProducts, StockLevels, WarehouseCapacity)
- "definition": one short sentence for the parameter
- "type": "float" or "integer"
- "shape": "[]" for scalar, "[N]" for vector (N = rows in that dataset), "[N,M]" for matrix
- {data_spec}
{data_source_line}

Examples:
- Number of products from first dataset: {{"symbol": "NumberOfProducts", "definition": "Number of products", "type": "integer", "shape": "[]", "data_column": "{DERIVED_N_ROWS}"{', "data_source": "inventory"' if multi_dataset else ''}}}
- Stock level per product: {{"symbol": "StockLevels", "definition": "Current stock for each product", "type": "integer", "shape": "[N]", "data_column": "Stock Levels"{', "data_source": "inventory"' if multi_dataset else ''}}}
- Do not include ProductId/StoreId as numeric parameters unless the formulation truly needs them as numbers.

Output only the JSON object, no other text. Use exact dataset names and column names as shown above."""


def _shape_string_to_list(shape_str: str, n_rows: int) -> list:
    """Convert shape string like '[]', '[N]', '[N,M]' to list; N/n_rows substituted."""
    if not shape_str or shape_str.strip() in ("[]", "''"):
        return []
    s = shape_str.strip().replace(" ", "")
    if s == "[]":
        return []
    if s == "[N]" or s == "[n]":
        return [n_rows]
    # [N, M] or [n, m] or literal numbers
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        out = []
        for p in parts:
            if p.upper() == "N" or p == "n":
                out.append(n_rows)
            elif p.isdigit():
                out.append(int(p))
            else:
                out.append(n_rows)  # fallback for M if only one dimension known
        if len(out) == 1:
            return out
        if len(out) == 2:
            return [out[0], out[1]]
        return out
    return []


def _resolve_column(df: pd.DataFrame, name: str) -> str:
    """Resolve data_column name to actual DataFrame column (exact or case-insensitive)."""
    if name in df.columns:
        return name
    name_lower = str(name).strip().lower()
    for col in df.columns:
        if col.lower() == name_lower:
            return col
    raise ValueError(f"Column '{name}' not in DataFrame. Available: {list(df.columns)}")


def _to_json_serializable(val):
    """Coerce numpy/pandas scalars to native Python for JSON."""
    if isinstance(val, (list, tuple)):
        return [_to_json_serializable(x) for x in val]
    if hasattr(val, "item"):
        return val.item()
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return int(val) if val == int(val) else float(val)
    return val


def _ensure_numeric_param_value(value, param_type: str):
    """
    OptiMUS-generated code expects numeric params (Gurobi can't use strings in constraints).
    If value is or contains date-like strings, convert to ordinal days (integer) so the pipeline works.
    """
    if isinstance(value, list):
        if not value:
            return value
        first = value[0]
        if isinstance(first, str) and _looks_like_date(first):
            try:
                dates = pd.to_datetime(value)
                # Ordinal day (days since epoch) so it's numeric and sortable
                ordinals = (dates - pd.Timestamp("1970-01-01")).days.tolist()
                return ordinals
            except Exception:
                pass
        return value
    if isinstance(value, str) and _looks_like_date(value):
        try:
            return int((pd.to_datetime(value) - pd.Timestamp("1970-01-01")).days)
        except Exception:
            pass
    return value


def _looks_like_date(s: str) -> bool:
    """Heuristic: string looks like a date (e.g. 2024-01-15 or 01/15/2024)."""
    if not isinstance(s, str) or len(s) < 8:
        return False
    s = s.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return True
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", s):
        return True
    return False


def _get_value_from_dataframe(df: pd.DataFrame, data_column, shape: list):
    """Extract parameter value from DataFrame from data_column and shape."""
    if isinstance(data_column, list):
        cols = [_resolve_column(df, c) for c in data_column]
    else:
        cols = [_resolve_column(df, data_column)]
    for c in cols:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not in DataFrame. Available: {list(df.columns)}")
    n_rows = len(df)

    if len(shape) == 0:
        # Scalar: one value
        col = cols[0]
        ser = df[col].dropna()
        if len(ser) == 0:
            raise ValueError(f"Column '{col}' has no non-null values")
        val = ser.iloc[0]
        return _to_json_serializable(val)
    if len(shape) == 1:
        # Vector: one column as list
        col = cols[0]
        vals = df[col].dropna().tolist()
        n = shape[0]
        if n is not None and n != len(vals):
            vals = vals[:n]
        return _to_json_serializable(vals)
    if len(shape) == 2:
        # Matrix: list of lists (row-major)
        if len(cols) == 1:
            col = cols[0]
            vals = df[col].dropna().tolist()
            return _to_json_serializable(vals)
        arr = df[cols].values.tolist()
        return _to_json_serializable(arr)
    return None


def extract_params_expert(
    description: str,
    data: pd.DataFrame | list[tuple[str, pd.DataFrame]],
    model: str = "gpt-4o-mini",
) -> tuple[dict, str | None]:
    """
    Use an LLM to reason over the problem description and dataset(s), then produce
    OptiMUS params (symbol, definition, type, shape, value) with values filled from the data.

    data: Either a single DataFrame or a list of (dataset_name, DataFrame) for multiple inputs.
    """
    from optimus_pipeline.optimus_utils import get_response, extract_json_from_end

    if isinstance(data, pd.DataFrame):
        datasets = [("data", data)]
        data_summary = _build_data_summary(data)
        multi_dataset = False
    else:
        datasets = data
        if not datasets:
            raise ValueError("datasets list must not be empty")
        data_summary = _build_data_summary_multi(datasets)
        multi_dataset = len(datasets) > 1

    datasets_by_name = {name: df for name, df in datasets}
    first_name, first_df = datasets[0]
    default_df = first_df
    default_n_rows = len(default_df)

    prompt = _expert_extract_params_prompt(
        description, data_summary, multi_dataset=multi_dataset
    )
    response = get_response(prompt, model=model)

    raw = extract_json_from_end(response)
    if "parameters" not in raw:
        raise ValueError("LLM output missing 'parameters' key. Got: " + str(raw)[:200])
    specs = raw["parameters"]
    if not isinstance(specs, list):
        raise ValueError("'parameters' must be a list. Got: " + str(type(specs)))

    params = {}
    for item in specs:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        definition = item.get("definition", "")
        ptype = item.get("type", "float")
        shape_str = item.get("shape", "[]")
        data_column = item.get("data_column")
        data_source = item.get("data_source")

        if not symbol or data_column is None:
            continue
        symbol = re.sub(r"[^\w]", "", str(symbol))
        if not symbol:
            continue
        if symbol[0].islower():
            symbol = symbol[0].upper() + symbol[1:]
        ptype = "integer" if str(ptype).lower() in ("int", "integer") else "float"

        # Resolve which dataframe to use
        if multi_dataset and data_source is not None:
            data_source = str(data_source).strip()
            if data_source not in datasets_by_name:
                # Try case-insensitive match
                for name in datasets_by_name:
                    if name.lower() == data_source.lower():
                        data_source = name
                        break
                else:
                    raise ValueError(
                        f"Unknown data_source '{data_source}' for param '{symbol}'. "
                        f"Available: {list(datasets_by_name.keys())}"
                    )
            df = datasets_by_name[data_source]
        else:
            df = default_df
        n_rows = len(df)

        shape = _shape_string_to_list(
            shape_str if isinstance(shape_str, str) else str(shape_str),
            n_rows,
        )

        # Derived parameters (dimensions): no column, compute from dataframe
        dc = str(data_column).strip()
        if dc == DERIVED_N_ROWS:
            value = n_rows
            shape = []
            ptype = "integer"
        elif dc.startswith(DERIVED_N_DISTINCT_PREFIX):
            col_name = dc[len(DERIVED_N_DISTINCT_PREFIX) :].strip()
            col_resolved = _resolve_column(df, col_name)
            value = int(df[col_resolved].nunique())
            shape = []
            ptype = "integer"
        else:
            try:
                value = _get_value_from_dataframe(df, data_column, shape)
            except Exception as e:
                raise ValueError(
                    f"Failed to get value for param '{symbol}' from data_column={data_column}"
                    + (f" (data_source={data_source})" if multi_dataset else "")
                    + f": {e}"
                ) from e

            # Convert date-like strings to numeric (ordinal days) so Gurobi/code gen can use them
            value = _ensure_numeric_param_value(value, ptype)
            if isinstance(value, list) and value and isinstance(value[0], int):
                ptype = "integer"

        params[symbol] = {
            "shape": shape,
            "definition": definition or f"Parameter {symbol}",
            "type": ptype,
            "value": value,
        }
    return params


def _sanitize_name(name: str) -> str:
    """Turn a column name into a valid param identifier (no spaces, safe for JSON)."""
    s = re.sub(r"[^\w\s]", "", str(name))
    s = re.sub(r"\s+", "_", s.strip())
    return s or "param"


def _infer_shape_and_value(series: pd.Series):
    """Infer shape and JSON-serializable value from a pandas Series."""
    vals = series.dropna().tolist()
    n = len(vals)
    if n == 0:
        return [], None
    if n == 1:
        v = vals[0]
        if isinstance(v, (int, float)):
            return [], v
        return [1], [v]
    # Check if all scalars
    try:
        if all(isinstance(x, (int, float)) for x in vals):
            return [n], vals
    except (TypeError, ValueError):
        pass
    return [n], vals


def _param_type_from_series(series: pd.Series) -> str:
    """Return 'integer' or 'float' for OptiMUS param type."""
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    return "float"


def build_params_from_dataframe(df: pd.DataFrame) -> dict:
    """
    Build OptiMUS params.json structure from a DataFrame.
    Each column becomes one parameter; name is sanitized, shape/value inferred.
    """
    params = {}
    for col in df.columns:
        name = _sanitize_name(col)
        # Deduplicate names
        base = name
        c = 0
        while name in params:
            c += 1
            name = f"{base}_{c}"
        series = df[col]
        shape, value = _infer_shape_and_value(series)
        if value is None:
            continue
        param_type = _param_type_from_series(series)
        params[name] = {
            "shape": shape,
            "definition": f"From column: {col}",
            "type": param_type,
            "value": value,
        }
    return params


def build_params_from_dataframes(
    datasets: list[tuple[str, pd.DataFrame]],
) -> dict:
    """
    Build OptiMUS params from multiple DataFrames. Each column is prefixed by
    dataset name to avoid clashes (e.g. inventory_StockLevels, stores_Capacity).
    """
    params = {}
    for name, df in datasets:
        prefix = _sanitize_name(name)
        for col in df.columns:
            param_name = f"{prefix}_{_sanitize_name(col)}" if len(datasets) > 1 else _sanitize_name(col)
            c = 0
            base = param_name
            while param_name in params:
                c += 1
                param_name = f"{base}_{c}"
            series = df[col]
            shape, value = _infer_shape_and_value(series)
            if value is None:
                continue
            param_type = _param_type_from_series(series)
            params[param_name] = {
                "shape": shape,
                "definition": f"From {name}: {col}",
                "type": param_type,
                "value": value,
            }
    return params


def load_data(path: str) -> pd.DataFrame:
    """Load CSV or Excel file into a DataFrame."""
    path_lower = path.lower()
    if path_lower.endswith(".csv"):
        return pd.read_csv(path)
    if path_lower.endswith(".xlsx") or path_lower.endswith(".xls"):
        try:
            return pd.read_excel(path, engine="openpyxl")
        except ImportError:
            return pd.read_excel(path)
    raise ValueError(f"Unsupported file format. Use .csv or .xlsx: {path}")


def read_description(description: str) -> str:
    """If description is a path to a file, read it; otherwise return as-is."""
    if os.path.isfile(description):
        with open(description, "r") as f:
            return f.read().strip()
    return description.strip()


def infer_definitions_with_llm(description: str, params: dict, model: str = "gpt-4o-mini") -> dict:
    """Use an LLM to generate short definitions for each param based on the problem description."""
    try:
        from optimus_pipeline.optimus_utils import get_response
    except ImportError:
        return params

    param_names = list(params.keys())
    prompt = f"""You are helping prepare parameters for an optimization solver.

Problem description:
{description}

Parameter names (from data columns): {param_names}

For each parameter name, output a single short "definition" sentence (one line, no JSON).
Output format: one line per parameter, in order, in the form:
ParamName: definition sentence

Example:
ProfitA: Profit per unit of product A
TotalLabor: Total available labor hours
"""
    try:
        resp = get_response(prompt, model=model)
        for line in resp.strip().split("\n"):
            if ":" in line:
                key, _, defn = line.partition(":")
                key = _sanitize_name(key.strip())
                defn = defn.strip()
                if key in params and defn:
                    params[key]["definition"] = defn
    except Exception:
        pass
    return params


def write_raw_inputs(output_dir: str, description: str, data_paths: list[str]) -> None:
    """Write natural-language description and copy raw data CSV(s) into output_dir/raw_input/."""
    raw_dir = os.path.join(output_dir, "raw_input")
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "desc.txt"), "w") as f:
        f.write(description)
    for p in data_paths:
        dest = os.path.join(raw_dir, os.path.basename(p))
        if os.path.abspath(p) != os.path.abspath(dest):
            shutil.copy2(p, dest)


def write_optimus_inputs(
    output_dir: str,
    description: str,
    params: dict,
) -> None:
    """Write desc.txt and params.json into output_dir/model_input/."""
    model_dir = os.path.join(output_dir, "model_input")
    os.makedirs(model_dir, exist_ok=True)

    with open(os.path.join(model_dir, "desc.txt"), "w") as f:
        f.write(description)

    with open(os.path.join(model_dir, "params.json"), "w") as f:
        json.dump(params, f, indent=4)


def run(
    data_path: str | list[str],
    description_path: str,
    output_dir: str = "current_query",
    model: str = "gpt-4o-mini",
    use_expert: bool = True,
    no_llm: bool = False,
) -> dict:
    """
    Generate OptiMUS inputs from one or more data files and a problem description.
    Use this from Python (e.g. notebooks) instead of the CLI.

    Args:
        data_path: Path to one CSV/Excel file, or list of paths for multiple datasets.
        description_path: Path to .txt with problem description, or the description string.
        output_dir: Problem directory; writes raw_input/ and model_input/ under it (default: current_query).
        model: LLM model for extraction.
        use_expert: If True, use LLM to map columns to parameters; else one param per column.
        no_llm: If True, no API calls (one param per column).

    Returns:
        dict with keys description, params (the generated content).
    """
    data_paths = [data_path] if isinstance(data_path, str) else list(data_path)
    if not data_paths:
        raise ValueError("At least one data path is required.")

    for p in data_paths:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Data file not found: {p}")

    datasets = [(_dataset_name_from_path(p), load_data(p)) for p in data_paths]
    for (name, df), p in zip(datasets, data_paths):
        print(f"Loaded {len(df)} rows, {len(df.columns)} columns from {p} (dataset: {name})")

    description = read_description(description_path)
    if not description:
        raise ValueError("Empty description.")

    use_expert_mode = use_expert and not no_llm
    if use_expert_mode:
        print("Extracting parameters with expert (LLM) reasoning over description and dataset(s)...")
        try:
            if len(datasets) == 1:
                params = extract_params_expert(
                    description, datasets[0][1], model=model
                )
            else:
                params = extract_params_expert(
                    description, datasets, model=model
                )
        except Exception as e:
            print(f"Expert extraction failed: {e}", file=sys.stderr)
            print("Falling back to simple mode (one param per column).", file=sys.stderr)
            if len(datasets) == 1:
                params = build_params_from_dataframe(datasets[0][1])
            else:
                params = build_params_from_dataframes(datasets)
            if not no_llm:
                params = infer_definitions_with_llm(description, params, model=model)
    else:
        if len(datasets) == 1:
            params = build_params_from_dataframe(datasets[0][1])
        else:
            params = build_params_from_dataframes(datasets)
        if not params:
            raise ValueError("No parameters produced from data (empty or unparseable columns?).")
        if not no_llm:
            params = infer_definitions_with_llm(description, params, model=model)

    write_raw_inputs(output_dir, description, data_paths)
    write_optimus_inputs(output_dir, description, params)
    print(f"Wrote raw_input/ and model_input/ under {output_dir}/")
    print(f"  model_input/desc.txt, model_input/params.json ({len(params)} parameters)")
    print(f"\nNext: run OptiMUS with:")
    if output_dir == "current_query":
        print("  python optimus.py")
    else:
        print(f"  python optimus.py --dir {output_dir}")

    return {"description": description, "params": params}


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV/Excel + natural language description into OptiMUS input files."
    )
    parser.add_argument(
        "--data", "-d",
        nargs="+",
        required=True,
        metavar="FILE",
        help="Path(s) to CSV or Excel file(s). One or more (e.g. --data inventory.csv stores.csv)",
    )
    parser.add_argument(
        "--description", "-n",
        required=True,
        help="Natural language problem description, or path to a .txt file containing it",
    )
    parser.add_argument(
        "--output", "-o",
        default="current_query",
        help="Problem directory; writes raw_input/ and model_input/ under it (default: current_query)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Do not use LLM; one param per column with column-based definitions only",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple mode: one parameter per column (no expert reasoning). Use with --no-llm or to only add LLM definitions/labels",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model for parameter extraction and/or definition/label inference (default: gpt-4o-mini)",
    )
    args = parser.parse_args()

    use_expert = not args.no_llm and not args.simple
    data_paths = args.data[0] if len(args.data) == 1 else args.data
    run(
        data_path=data_paths,
        description_path=args.description,
        output_dir=args.output,
        model=args.model,
        use_expert=use_expert,
        no_llm=args.no_llm,
    )


if __name__ == "__main__":
    main()
