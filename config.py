"""
config.py
=========
Central configuration file for the Expense Tracker application.

Why this file exists:
----------------------
Instead of scattering "magic strings" and "magic numbers" (like file paths,
folder names, or date formats) across every module, we define them ONCE here
and import them everywhere else. This is a core software engineering
principle called "Single Source of Truth."

If you ever need to rename the database file, or change the date format,
you change it in exactly ONE place instead of hunting through 8 files.

Django connection:
-------------------
This file is the direct ancestor of Django's `settings.py`. In Django,
EVERY project has a settings.py file that defines database paths, installed
apps, timezones, and constants — exactly what we're doing here, just smaller.
Getting comfortable with "config lives in its own file" now will make
settings.py feel familiar later.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# BASE DIRECTORY
# ---------------------------------------------------------------------------
# Path(__file__) gives us the path to THIS file (config.py).
# .resolve() converts it to an absolute path (no matter where the script is
# run from — very important for CLI tools that can be launched from anywhere).
# .parent gives us the folder that contains this file, i.e. the project root.
#
# Beginner mistake this avoids:
# Many beginners hardcode paths like "C:/Users/Hamza/expense_tracker/data".
# That breaks the moment the project is moved to another computer (or another
# recruiter's laptop!). Using pathlib.Path with __file__ makes the project
# fully portable.
BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# FOLDER PATHS
# ---------------------------------------------------------------------------
# We use the "/" operator here because pathlib overloads it to join paths
# in an OS-safe way. On Windows this produces backslashes, on Linux/Mac
# forward slashes — automatically. You never manually type "\\" or "/".
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
CHARTS_DIR = BASE_DIR / "charts"

# ---------------------------------------------------------------------------
# DATABASE PATH
# ---------------------------------------------------------------------------
# The SQLite database is a single file. We keep it at the project root so
# it's easy to find, back up, or delete during testing.
DATABASE_PATH = BASE_DIR / "expenses.db"

# ---------------------------------------------------------------------------
# DATE FORMAT
# ---------------------------------------------------------------------------
# SQLite has no native "date" type — it stores dates as TEXT. We must pick
# ONE consistent format for the entire app so that sorting and filtering by
# date works correctly (ISO format sorts correctly as plain strings).
# Example: "2026-07-05"
DATE_FORMAT = "%Y-%m-%d"

# ---------------------------------------------------------------------------
# APP METADATA
# ---------------------------------------------------------------------------
APP_NAME = "Expense Tracker CLI"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# DEFAULT CATEGORIES
# ---------------------------------------------------------------------------
# These are seeded into the database the first time it's created, so the
# app is immediately usable without forcing the user to set up categories
# before adding their first expense.
DEFAULT_CATEGORIES = [
    "Food",
    "Transport",
    "Rent",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Health",
    "Education",
    "Other",
]

# ---------------------------------------------------------------------------
# VALIDATION LIMITS
# ---------------------------------------------------------------------------
# Centralizing these means if you ever decide "actually, expenses over
# 1,000,000 should be flagged," you edit this constant, not scattered
# if-statements across services.py.
MIN_EXPENSE_AMOUNT = 0.01
MAX_EXPENSE_AMOUNT = 10_000_000.00

# ---------------------------------------------------------------------------
# BUDGET WARNING THRESHOLD
# ---------------------------------------------------------------------------
# When spending crosses this percentage of the monthly budget, the app
# will display a warning to the user.
BUDGET_WARNING_THRESHOLD = 80  # percent


def ensure_directories_exist() -> None:
    """
    Create the data/, exports/, and charts/ folders if they don't exist yet.

    Why a function instead of just running the code at import time?
    ------------------------------------------------------------------
    Technically we COULD call DATA_DIR.mkdir(...) directly in this file.
    But putting it in a function and calling it explicitly from main.py
    keeps this config file "side-effect free" — importing a config module
    should never silently create folders or files. This is a subtle but
    important habit: config/settings modules should describe values, not
    perform actions. Actions belong in functions that are called
    deliberately by the entry point (main.py).

    `parents=True`  -> also create any missing parent folders.
    `exist_ok=True` -> do NOT raise an error if the folder already exists.
    """
    for folder in (DATA_DIR, EXPORTS_DIR, CHARTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)
