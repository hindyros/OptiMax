#!/usr/bin/env python3
"""
Optima — end-to-end optimization pipeline.

Place your input files in data_upload/:
    - A .txt file with the problem description (required)
    - A .csv file with parameter data       (optional)

Then run:
    python main.py

The script will:
    1. Clear the workspace (archive previous results)
    2. Copy uploaded files into current_query/raw_input/
    3. Convert raw inputs to structured model inputs (raw_to_model)
    4. Run OptiMUS and OptiMind solvers in parallel
    5. Judge and compare both solutions
    6. Generate a professional consultant report (report.md + enriched verdict.json)

You can also point directly at files instead of using data_upload/:
    python main.py --desc path/to/problem.txt
    python main.py --desc path/to/problem.txt --data path/to/params.csv
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Pipeline imports ──
from query_manager import prepare_workspace
from raw_to_model import run_pipeline as raw_to_model
from optimus import run_pipeline as run_optimus
from optimind import run_pipeline as run_optimind
from judge import compare_solutions
from consultant import generate_report

# ── Constants ──
QUERY_DIR = "current_query"
UPLOAD_DIR = "data_upload"

# ── ANSI colours for terminal output ──
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _banner(title: str) -> None:
    width = 60
    print(f"\n{_CYAN}{'═' * width}")
    print(f"  {_BOLD}{title}{_RESET}{_CYAN}")
    print(f"{'═' * width}{_RESET}\n")


def _step(n: int, total: int, label: str) -> None:
    print(f"{_BOLD}[{n}/{total}]{_RESET} {label}")


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✓ {msg}{_RESET}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠ {msg}{_RESET}")


def _fail(msg: str) -> None:
    print(f"  {_RED}✗ {msg}{_RESET}")


# ═══════════════════════════════════════════════════════════════════════════
# File discovery
# ═══════════════════════════════════════════════════════════════════════════


def _find_upload_files(upload_dir: str) -> tuple[str, str | None]:
    """
    Locate the required .txt and optional .csv in the upload directory.

    Returns (txt_path, csv_path_or_None).
    Exits with a clear error if inputs are invalid.
    """
    if not os.path.isdir(upload_dir):
        _fail(f"Upload directory not found: {upload_dir}/")
        print(f"  Create it and place your .txt file inside.")
        sys.exit(1)

    txt_files = sorted(glob.glob(os.path.join(upload_dir, "*.txt")))
    csv_files = sorted(glob.glob(os.path.join(upload_dir, "*.csv")))

    if not txt_files:
        _fail(f"No .txt file found in {upload_dir}/")
        print(f"  Place your problem description as a .txt file in {upload_dir}/")
        sys.exit(1)

    if len(txt_files) > 1:
        _fail(f"Multiple .txt files found in {upload_dir}/:")
        for f in txt_files:
            print(f"    - {f}")
        print(f"  Keep only one .txt file (the problem description).")
        sys.exit(1)

    if len(csv_files) > 1:
        _fail(f"Multiple .csv files found in {upload_dir}/:")
        for f in csv_files:
            print(f"    - {f}")
        print(f"  Keep at most one .csv file (the parameter data).")
        sys.exit(1)

    return txt_files[0], csv_files[0] if csv_files else None


def _copy_to_raw_input(
    txt_path: str,
    csv_path: str | None,
    query_dir: str,
) -> None:
    """Copy user files into current_query/raw_input/, renaming to expected names."""
    raw_dir = os.path.join(query_dir, "raw_input")
    os.makedirs(raw_dir, exist_ok=True)

    dest_txt = os.path.join(raw_dir, "raw_desc.txt")
    shutil.copy2(txt_path, dest_txt)
    _ok(f"{os.path.basename(txt_path)}  →  raw_input/raw_desc.txt")

    if csv_path:
        dest_csv = os.path.join(raw_dir, "raw_params.csv")
        shutil.copy2(csv_path, dest_csv)
        _ok(f"{os.path.basename(csv_path)}  →  raw_input/raw_params.csv")
    else:
        print(f"  (no CSV — text-only mode)")


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════════


def run(
    desc_path: str | None = None,
    data_path: str | None = None,
    upload_dir: str = UPLOAD_DIR,
    query_dir: str = QUERY_DIR,
    no_archive: bool = False,
) -> dict | None:
    """
    Run the full Optima pipeline end-to-end.

    Args:
        desc_path:  Explicit path to a .txt description file.
                    If None, discovers from upload_dir.
        data_path:  Explicit path to a .csv data file (optional).
        upload_dir: Directory to scan for uploaded files.
        query_dir:  Working directory for the pipeline.
        no_archive: If True, skip archiving previous results.

    Returns:
        The verdict dict from judge.compare_solutions(), or None if
        both solvers failed and no verdict could be produced.
    """
    total_steps = 6
    t0 = time.time()

    _banner("Optima Pipeline")

    # ── Resolve input files ──
    if desc_path:
        # Explicit paths provided via CLI
        if not os.path.isfile(desc_path):
            _fail(f"Description file not found: {desc_path}")
            sys.exit(1)
        txt_path = desc_path
        csv_path = data_path
        if csv_path and not os.path.isfile(csv_path):
            _fail(f"Data file not found: {csv_path}")
            sys.exit(1)
    else:
        # Discover from data_upload/
        txt_path, csv_path = _find_upload_files(upload_dir)

    print(f"  Description: {txt_path}")
    print(f"  Data:        {csv_path or '(none)'}")
    print()

    # ── Step 1: Clear workspace ──
    _step(1, total_steps, "Clearing workspace")
    prepare_workspace(query_dir=query_dir, archive=not no_archive)
    _ok("Workspace ready")

    # ── Step 2: Copy files to raw_input/ ──
    _step(2, total_steps, "Copying inputs to raw_input/")
    _copy_to_raw_input(txt_path, csv_path, query_dir)

    # ── Step 3: Convert raw → model inputs ──
    _step(3, total_steps, "Converting raw inputs to model inputs (raw_to_model)")
    try:
        raw_to_model(problem_dir=query_dir)
        _ok("Model inputs generated")
    except Exception as exc:
        _fail(f"raw_to_model failed: {exc}")
        traceback.print_exc()
        print(f"\n{_RED}Cannot continue without model inputs. Aborting.{_RESET}")
        sys.exit(1)

    # ── Step 4: Run OptiMUS + OptiMind in parallel ──
    _step(4, total_steps, "Running OptiMUS and OptiMind solvers in parallel")
    optimus_ok = False
    optimind_ok = False

    def _run_optimus():
        return ("optimus", run_optimus(problem_dir=query_dir))

    def _run_optimind():
        return ("optimind", run_optimind(problem_dir=query_dir))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_run_optimus): "optimus",
            executor.submit(_run_optimind): "optimind",
        }
        for future in as_completed(futures):
            solver_name = futures[future]
            try:
                name, result = future.result()
                if name == "optimus":
                    optimus_ok = True
                    _ok("OptiMUS finished")
                else:
                    optimind_ok = result.get("success", False)
                    if optimind_ok:
                        _ok("OptiMind finished")
                    else:
                        _warn("OptiMind ran but did not produce a successful solution")
            except Exception as exc:
                _warn(f"{solver_name} failed: {exc}")
                traceback.print_exc()

    if not optimus_ok and not optimind_ok:
        _warn("Both solvers failed — judge will attempt to evaluate partial output")

    # ── Step 5: Judge ──
    _step(5, total_steps, "Judging solutions")
    verdict = None
    try:
        verdict = compare_solutions(problem_dir=query_dir)
        _ok("Verdict generated")
    except RuntimeError as exc:
        _fail(f"Judge error: {exc}")
    except Exception as exc:
        _fail(f"Judge failed unexpectedly: {exc}")
        traceback.print_exc()

    # ── Step 6: Consultant report ──
    report = None
    if verdict:
        _step(6, total_steps, "Generating consultant report")
        try:
            report = generate_report(problem_dir=query_dir)
            _ok("Report generated")
        except Exception as exc:
            _warn(f"Consultant failed: {exc}")
            traceback.print_exc()

    # ── Summary ──
    elapsed = time.time() - t0
    _banner("Results")

    if verdict:
        winner = verdict["winner"].upper()
        obj = verdict.get("objective_value")
        direction = verdict.get("direction", "unknown")

        opt_status = verdict["solvers"]["optimus"]["status"]
        opt_obj = verdict["solvers"]["optimus"]["objective_value"]
        mind_status = verdict["solvers"]["optimind"]["status"]
        mind_obj = verdict["solvers"]["optimind"]["objective_value"]

        print(f"  {_BOLD}Winner:{_RESET}     {_GREEN}{winner}{_RESET}")
        print(f"  {_BOLD}Objective:{_RESET}  {obj}")
        print(f"  {_BOLD}Direction:{_RESET}  {direction}")
        print()
        print(f"  OptiMUS:   {opt_status}  (obj = {opt_obj})")
        print(f"  OptiMind:  {mind_status}  (obj = {mind_obj})")
        print()
        print(f"  {_BOLD}Reasoning:{_RESET}  {verdict.get('reasoning', 'N/A')}")
        print()
        print(f"  Output files:")
        print(f"    {query_dir}/final_output/verdict.json")
        print(f"    {query_dir}/final_output/report.md")
    else:
        _fail("No verdict could be produced.")
        print(f"  Check solver output in {query_dir}/optimus_output/ and {query_dir}/optimind_output/")

    print(f"\n  Elapsed: {elapsed:.1f}s")
    print()

    return verdict


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Optima — end-to-end optimization pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Default behaviour: reads a .txt (required) and .csv (optional)\n"
            "from data_upload/, runs the full pipeline, and writes results to\n"
            "current_query/final_output/.\n"
            "\n"
            "Examples:\n"
            "  python main.py                                    # use data_upload/\n"
            "  python main.py --desc problem.txt                 # explicit desc\n"
            "  python main.py --desc problem.txt --data data.csv # desc + data\n"
        ),
    )
    parser.add_argument(
        "--desc", type=str, default=None,
        help="Path to the problem description .txt file (overrides data_upload/)",
    )
    parser.add_argument(
        "--data", type=str, default=None,
        help="Path to the parameter data .csv file (optional, overrides data_upload/)",
    )
    parser.add_argument(
        "--dir", type=str, default=QUERY_DIR,
        help=f"Working directory (default: {QUERY_DIR})",
    )
    parser.add_argument(
        "--no-archive", action="store_true",
        help="Skip archiving previous results before clearing",
    )
    args = parser.parse_args()

    if args.data and not args.desc:
        parser.error("--data requires --desc (cannot provide CSV without a description)")

    verdict = run(
        desc_path=args.desc,
        data_path=args.data,
        query_dir=args.dir,
        no_archive=args.no_archive,
    )

    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    main()
