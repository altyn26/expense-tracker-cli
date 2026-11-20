# AGENTS.md

Instructions for AI coding agents working in this repository.
Read this file fully before making any change.

## Purpose
`expense-tracker-cli` is a small Python command-line app for recording
expenses, budgets and categories in a local SQLite database. It also
produces reports, CSV exports and matplotlib charts.
This repository is used for a university software-engineering assignment
(audit + small, reviewed improvements). It is NOT a production system.

## Architecture (layers, top to bottom)
- `main.py`        CLI entry point: argparse commands + interactive menu.
- `services.py`    Business rules: `CategoryManager`, `ExpenseManager`, `BudgetManager`.
- `utils.py`       Input validation (`validate_amount`, `validate_date`, ...) and `ValidationError`.
- `database.py`    `DatabaseManager`: SQLite access (accepts `db_path`).
- `models.py`      Data classes `Category`, `Expense`.
- `reports.py`     Reports and CSV export.
- `visualization.py` Charts (matplotlib, imported at module level by `main.py`).
- `config.py`      Constants (`DATABASE_PATH`, `DATE_FORMAT`, amount limits).
- `seed_sample_data.py` Demo data script (may write to the default database: verify before running).

Dependency direction: `main` -> `services` -> `database`. Keep business
rules in `services.py` / `utils.py`, not in `main.py`.

## Setup (Linux / Codespaces)
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```
On Windows Git Bash activate with `source .venv/Scripts/activate`.

## Safe commands (allowed without asking)
- `git status`, `git diff`, `git log`, `git branch --show-current`
- `python main.py --help`
- `python -m compileall -q .`  (syntax check, writes only `__pycache__`)
- `python -m pytest -v`  (only after tests exist and pytest is installed; see Tests)
- Read-only inspection: `ls`, `cat`, `grep`, `git grep`, `sed -n`

## Ask a human first
- Any command that writes to `expenses.db` (running CLI commands such as
  `add`, `update`, `delete`, `budget`, `menu`, or `seed_sample_data.py`).
  Note: creating `DatabaseManager` runs `CREATE TABLE IF NOT EXISTS` and
  seeds default categories, so even simple runs can modify the file.
- Adding, removing or upgrading dependencies in `requirements.txt`.
- Creating or deleting files outside the task scope.

## Forbidden actions
- Never read, create, print or commit secrets, tokens, passwords or `.env` files.
- Never deploy, publish or push to any production target.
- Never run destructive commands: `rm -rf`, `git reset --hard`,
  `git push --force`, `git clean -fdx`, dropping tables, deleting the database.
- Never push to or open pull requests against the upstream repository
  (`Hamzaiftikhar01/expense-tracker-cli`). Work only on branch `a05-audit`
  of the fork `altyn26/expense-tracker-cli`.
- Never modify the tag `baseline-a05` or rewrite git history.
- Never change dependencies without explicit human approval.
- Never invent test results. If a check was not run, say it was not run.

## Coding conventions
- Python 3, type hints on function signatures (the codebase already uses them).
- SQL: parameterized queries only (`?` placeholders). Never build SQL values
  with f-strings. Dynamic identifiers (e.g. sort column) must go through an
  allow-list like `ExpenseManager._sort_column`.
- Validate user input in `utils.py` / `services.py` and raise `ValidationError`
  (or `DuplicateCategoryError`) with a clear message.
- Keep changes small and focused: one purpose per change, minimal diff.

## Tests
- Status at baseline: there are NO automated tests and pytest is NOT listed in
  `requirements.txt`. No lint, type-check or build configuration exists.
- New tests go in `tests/`, named `test_*.py`, run with `python -m pytest -v`.
- Tests MUST use a temporary database: `DatabaseManager(db_path=tmp_path / "test.db")`.
  Tests must never touch `expenses.db`.
- Do not import `visualization` / matplotlib in tests of services or utils.

## Acceptance criteria that must remain true
1. `validate_amount` rejects non-numeric input and values below 0.01 or above 10,000,000 with `ValidationError`.
2. `validate_date` rejects empty strings, wrong formats and impossible dates (e.g. `2026-02-30`).
3. `CategoryManager.create_category` raises `DuplicateCategoryError` for an existing name.
4. `ExpenseManager.get_all_expenses` rejects an unknown `sort_by` with `ValidationError`.
5. An expense saved with `add_expense` is returned by `get_expense_by_id` with the same amount, date and description.

## Review gates
- A human reviews every diff before it is committed.
- Run the safe checks before and after each change and report exact
  commands and real results (including failures).
- After any run that changes `expenses.db`, restore it: `git checkout -- expenses.db`
  (until the database is removed from version control).
- Stop and ask when the task is ambiguous or needs a forbidden action.
