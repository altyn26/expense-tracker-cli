"""
models.py
=========
Defines the core data structures: Expense and Category.

These classes do NOT talk to the database directly. They are simple,
"dumb" containers that represent a single row of data as a Python object.
Keeping them dumb (no SQL inside) is a deliberate design choice called
separating "data" from "data access."

Django connection:
-------------------
This file is a direct preview of Django's models.py. In Django you'd write:

    class Expense(models.Model):
        amount = models.DecimalField(max_digits=10, decimal_places=2)
        category = models.ForeignKey(Category, on_delete=models.RESTRICT)
        description = models.TextField(blank=True)
        date = models.DateField()

Notice the shape is almost identical to what we build below by hand.
Django's models.Model base class gives you database save/query methods
for free — here we build ExpenseManager/DatabaseManager to do that job
manually so you understand what Django is doing under the hood.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    """
    Represents a single expense category (e.g. "Food", "Rent").

    We use @dataclass instead of writing __init__ by hand. The dataclass
    decorator auto-generates __init__, __repr__, and __eq__ based on the
    type-hinted fields below — less boilerplate, same result.

    Attributes:
        id: Database primary key. None until the category has been saved.
        name: The category's display name. Must be unique (enforced by
              the database schema in database.py).
    """
    id: Optional[int]
    name: str

    def __str__(self) -> str:
        """
        Controls what print(category) or f"{category}" displays.
        We override this so categories show up as their name, not as
        "Category(id=1, name='Food')", everywhere they're printed in
        the CLI (menus, tables, reports).
        """
        return self.name


@dataclass
class Expense:
    """
    Represents a single expense entry.

    Attributes:
        id: Database primary key. None until the expense has been saved.
        amount: The expense amount in currency units (always positive —
                enforced in services.py, not here, since validation is a
                business-logic concern, not a data-shape concern).
        category_id: Foreign key pointing to a Category's id.
        description: Free-text note about the expense (optional).
        date: ISO-format date string "YYYY-MM-DD".
        category_name: NOT stored in the expenses table itself — this is
                populated only when we JOIN with the categories table, so
                we can display "Food" instead of just "3" in reports.
                It defaults to None and is filled in by DatabaseManager
                query results when relevant.
    """
    id: Optional[int]
    amount: float
    category_id: int
    date: str
    description: str = ""
    category_name: Optional[str] = None

    def __str__(self) -> str:
        """
        Human-readable one-line summary, used throughout the CLI when
        listing expenses.

        Example: "[12] 2026-07-05 | Food       | 450.00 | Lunch with friends"

        :<10 means "left-align in a field 10 characters wide" — this is
        what keeps table-style CLI output visually aligned in columns.
        """
        category_display = self.category_name or f"Category#{self.category_id}"
        return (
            f"[{self.id}] {self.date} | "
            f"{category_display:<12} | "
            f"{self.amount:>10.2f} | "
            f"{self.description}"
        )
