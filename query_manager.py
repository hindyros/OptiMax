"""
Manages the current_query/ workspace: archives previous results before each
new pipeline run so nothing is lost, then clears the workspace for fresh input.
"""

import os
import shutil
from datetime import datetime

QUERY_DIR = "current_query"
HISTORY_DIR = "query_history"
MAX_ARCHIVES = 20  # keep at most this many past runs; set to None for unlimited


def _has_content(directory):
    """Check if a directory exists and contains any files (recursively)."""
    if not os.path.isdir(directory):
        return False
    for _, _, files in os.walk(directory):
        if files:
            return True
    return False


def archive_current_query(query_dir=QUERY_DIR, history_dir=HISTORY_DIR):
    """
    Move the contents of query_dir into a timestamped subfolder under
    history_dir.  Returns the archive path, or None if there was nothing
    to archive.
    """
    if not _has_content(query_dir):
        return None

    os.makedirs(history_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = os.path.join(history_dir, timestamp)

    # Handle the (unlikely) case of duplicate timestamps
    counter = 1
    base = archive_path
    while os.path.exists(archive_path):
        archive_path = f"{base}_{counter}"
        counter += 1

    shutil.copytree(query_dir, archive_path)
    print(f"[query_manager] Archived previous query to {archive_path}")
    return archive_path


def clear_current_query(query_dir=QUERY_DIR):
    """
    Remove all files and subdirectories inside query_dir, but keep the
    directory itself so the workspace always exists.
    """
    if not os.path.isdir(query_dir):
        os.makedirs(query_dir, exist_ok=True)
        return

    for entry in os.listdir(query_dir):
        entry_path = os.path.join(query_dir, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
        else:
            os.remove(entry_path)

    print(f"[query_manager] Cleared {query_dir}/")


def enforce_archive_limit(history_dir=HISTORY_DIR, max_archives=MAX_ARCHIVES):
    """
    If more than max_archives folders exist in history_dir, delete the
    oldest ones (sorted by name, which is a timestamp).
    """
    if max_archives is None:
        return
    if not os.path.isdir(history_dir):
        return

    archives = sorted(
        [d for d in os.listdir(history_dir)
         if os.path.isdir(os.path.join(history_dir, d))]
    )

    while len(archives) > max_archives:
        oldest = archives.pop(0)
        oldest_path = os.path.join(history_dir, oldest)
        shutil.rmtree(oldest_path)
        print(f"[query_manager] Removed old archive {oldest_path}")


def prepare_workspace(query_dir=QUERY_DIR, history_dir=HISTORY_DIR,
                      archive=True, max_archives=MAX_ARCHIVES):
    """
    Top-level function: archive the previous query (if any), clear the
    workspace, and enforce the archive cap.

    Call this at the start of every new pipeline run.

    Args:
        query_dir:    Path to the active workspace (default: current_query)
        history_dir:  Path to the archive folder (default: query_history)
        archive:      If False, skip archiving and just clear.
        max_archives: Max number of archives to retain.
    """
    if archive:
        archive_current_query(query_dir, history_dir)
        enforce_archive_limit(history_dir, max_archives)

    clear_current_query(query_dir)
