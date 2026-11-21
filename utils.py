"""
utils.py
========
Small, reusable helper functions used across the project: input validation,
date parsing, and console-formatting helpers.

Why a separate utils.py?
--------------------------
These functions don't belong to any single class — they're pure functions
(same input always produces the same output, no side effects) used by
multiple modules (services.py, main.py). Grouping them here avoids
duplicating validation logic in five different places.
"""
import math

from datetime import datetime
from typing import Optional

from config import DATE_FORMAT, MAX_EXPENSE_AMOUNT, MIN_EXPENSE_AMOUNT


class ValidationError(Exception):
    """
    Custom exception for invalid user input.

    Why create our own exception class instead of raising a generic
    ValueError?
    --------------------------------------------------------------
    A custom exception type lets calling code catch VALIDATION problems
    specifically, separately from other kinds of errors (like database
    errors). In main.py we can write:

        try:
            ...
        except ValidationError as e:
            print(f"Invalid input: {e}")
        except DatabaseError as e:
            print(f"Database problem: {e}")

    This is the same pattern Django uses extensively (e.g.
    django.core.exceptions.ValidationError) to distinguish "the user typed
    something wrong" from "something broke in the system."
    """
    pass


def validate_amount(raw_amount: str) -> float:
    """
    Convert a raw string input into a validated float amount.

    Raises:
        ValidationError: if the input isn't a valid number, or is outside
        the allowed range defined in config.py.

    Beginner mistake this avoids:
    --------------------------------
    A common bug is doing `float(user_input)` directly and letting the
    program crash with an unhandled ValueError if the user types "abc".
    Here we catch that explicitly and re-raise a clear, custom error
    message instead of an ugly Python traceback.
    """
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        raise ValidationError(f"'{raw_amount}' is not a valid number.")

    if math.isnan(amount):
        raise ValidationError(f"'{raw_amount}' is not a valid number.")
    if amount < MIN_EXPENSE_AMOUNT:
        raise ValidationError(
            f"Amount must be at least {MIN_EXPENSE_AMOUNT}. Negative or "
            f"zero expenses are not allowed."
        )
    if amount > MAX_EXPENSE_AMOUNT:
        raise ValidationError(
            f"Amount exceeds the maximum allowed value of {MAX_EXPENSE_AMOUNT}."
        )
    return amount


def validate_date(raw_date: str) -> str:
    """
    Validate that a date string matches DATE_FORMAT ("YYYY-MM-DD") and
    represents a real calendar date (rejects things like "2026-02-30").

    Returns the same string back if valid, so this function can be used
    as a simple pass-through validator: `date = validate_date(user_input)`.

    strptime does the heavy lifting: it will raise a ValueError on its own
    for genuinely invalid dates (like day 32, or month 13), which we catch
    and convert into our own ValidationError.
    """
    if not raw_date or not raw_date.strip():
        raise ValidationError("Date cannot be empty.")

    try:
        datetime.strptime(raw_date.strip(), DATE_FORMAT)
    except ValueError:
        raise ValidationError(
            f"'{raw_date}' is not a valid date. Use format YYYY-MM-DD, "
            f"e.g. 2026-07-05."
        )
    return raw_date.strip()


def validate_non_empty(value: str, field_name: str = "Field") -> str:
    """
    Ensure a text field (like a category name) isn't blank or just
    whitespace. Returns the trimmed string.
    """
    if value is None or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty.")
    return value.strip()


def parse_month(raw_month: str) -> str:
    """
    Validate and normalize a "YYYY-MM" month string (used for budgets and
    monthly reports).

    We reuse datetime.strptime with a "%Y-%m" pattern to confirm the month
    portion is a real month (01-12) and the year is numeric.
    """
    if not raw_month or not raw_month.strip():
        raise ValidationError("Month cannot be empty.")
    try:
        datetime.strptime(raw_month.strip(), "%Y-%m")
    except ValueError:
        raise ValidationError(
            f"'{raw_month}' is not a valid month. Use format YYYY-MM, "
            f"e.g. 2026-07."
        )
    return raw_month.strip()


def current_month() -> str:
    """Return today's month as 'YYYY-MM' — used as a default when the
    user doesn't specify a month explicitly."""
    return datetime.now().strftime("%Y-%m")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """
    Print a simple, clean, aligned text table to the console — no external
    dependencies needed (no need for a library like `tabulate`).

    How it works:
    --------------
    1. For each column, find the widest value among the header and all
       rows in that column.
    2. Use that width to left-pad/left-align every cell so columns line up.

    This kind of "compute column widths dynamically" logic is a classic
    beginner-to-intermediate exercise, and it's genuinely useful: it means
    the table always looks correct no matter how long the data is.
    """
    if not rows:
        print("(no data to display)")
        return

    col_widths = [
        max(len(str(headers[i])), max(len(str(row[i])) for row in rows))
        for i in range(len(headers))
    ]

    header_line = " | ".join(
        str(headers[i]).ljust(col_widths[i]) for i in range(len(headers))
    )
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))))
