"""
services.py
===========
The "business logic" layer of the application.

This is the most important architectural idea in the whole project:

    main.py (CLI)  -->  services.py (business rules)  -->  database.py (SQL)

main.py never talks to the database directly. It calls methods like
`expense_manager.add_expense(...)`, and THIS file decides how to validate,
process, and store that data. This is called a "service layer" pattern,
and it's exactly what Django encourages too (keeping logic out of your
views and models, in dedicated service functions/classes) as an app grows
past toy-project size.
"""

from datetime import datetime
from typing import Optional

from config import BUDGET_WARNING_THRESHOLD
from database import DatabaseManager
from models import Category, Expense
from utils import ValidationError, validate_amount, validate_date, validate_non_empty


class DuplicateCategoryError(Exception):
    """Raised when trying to create a category that already exists."""
    pass


class CategoryManager:
    """
    Handles all business logic for categories: create, edit, delete, list.

    Notice this class holds a reference to a DatabaseManager instance
    rather than creating its own. This is called "dependency injection" —
    the DatabaseManager is passed in from outside (main.py) instead of
    being created here. Benefits:
      1. Every manager class shares the SAME connection, avoiding SQLite
         locking issues from multiple open connections.
      2. In tests, you could inject a fake/mock DatabaseManager instead of
         a real one — impossible if this class created its own connection.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_category(self, name: str) -> Category:
        """
        Create a new category after validating and checking for duplicates.

        Raises:
            ValidationError: if the name is empty.
            DuplicateCategoryError: if a category with this name (case-
            insensitive) already exists.
        """
        clean_name = validate_non_empty(name, "Category name")

        existing = self.db.fetch_one(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?);",
            (clean_name,),
        )
        if existing is not None:
            raise DuplicateCategoryError(f"Category '{clean_name}' already exists.")

        cursor = self.db.execute(
            "INSERT INTO categories (name) VALUES (?);", (clean_name,)
        )
        return Category(id=cursor.lastrowid, name=clean_name)

    def edit_category(self, category_id: int, new_name: str) -> Category:
        """Rename an existing category, enforcing the same duplicate check."""
        clean_name = validate_non_empty(new_name, "Category name")

        existing = self.db.fetch_one(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?) AND id != ?;",
            (clean_name, category_id),
        )
        if existing is not None:
            raise DuplicateCategoryError(f"Category '{clean_name}' already exists.")

        self.db.execute(
            "UPDATE categories SET name = ? WHERE id = ?;", (clean_name, category_id)
        )
        return Category(id=category_id, name=clean_name)

    def delete_category(self, category_id: int) -> None:
        """
        Delete a category.

        Because the `expenses` table was created with
        `FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT`,
        SQLite itself will raise an sqlite3.IntegrityError if any expenses
        still reference this category. We catch that here and convert it
        into a clear, human-readable message instead of letting a raw
        database error escape to the user.
        """
        import sqlite3

        try:
            self.db.execute("DELETE FROM categories WHERE id = ?;", (category_id,))
        except sqlite3.IntegrityError:
            raise ValidationError(
                "Cannot delete this category — it still has expenses linked "
                "to it. Delete or reassign those expenses first."
            )

    def get_all_categories(self) -> list[Category]:
        """Return every category, alphabetically sorted."""
        rows = self.db.fetch_all("SELECT id, name FROM categories ORDER BY name;")
        return [Category(id=row["id"], name=row["name"]) for row in rows]

    def get_category_by_name(self, name: str) -> Optional[Category]:
        """Look up a category by name (case-insensitive). Returns None if
        not found — used to convert user-typed category names into IDs."""
        row = self.db.fetch_one(
            "SELECT id, name FROM categories WHERE LOWER(name) = LOWER(?);", (name,)
        )
        if row is None:
            return None
        return Category(id=row["id"], name=row["name"])


class ExpenseManager:
    """
    Handles all business logic for expenses: add, update, delete, and every
    flavor of search/filter/sort the CLI exposes.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def add_expense(
        self, amount: str, category_id: int, date: str, description: str = ""
    ) -> Expense:
        """
        Validate and insert a new expense.

        Notice validation happens HERE, in the service layer, not in
        models.py. models.py just describes the shape of data; services.py
        enforces the RULES about that data. Keeping these separate is what
        lets you change validation rules later without touching the data
        model itself.
        """
        clean_amount = validate_amount(amount)
        clean_date = validate_date(date)

        cursor = self.db.execute(
            """
            INSERT INTO expenses (amount, category_id, description, date)
            VALUES (?, ?, ?, ?);
            """,
            (clean_amount, category_id, description.strip(), clean_date),
        )
        # Re-fetch the row via the JOIN query rather than constructing the
        # Expense by hand — this guarantees category_name is populated
        # correctly (e.g. for the confirmation message in main.py) instead
        # of falling back to "Category#<id>". Re-fetching after a write is
        # a small extra query, but for a CLI tool clarity wins over the
        # micro-optimization of skipping it.
        return self.get_expense_by_id(cursor.lastrowid)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update_expense(
        self,
        expense_id: int,
        amount: Optional[str] = None,
        category_id: Optional[int] = None,
        date: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Update only the fields the caller actually provides (partial
        update). Fields left as None are left untouched in the database.

        This pattern — building the SET clause dynamically based on which
        arguments were passed — mirrors what an ORM's `.update(**kwargs)`
        does internally, and previews Django's partial-update pattern used
        in forms and DRF's PATCH requests.
        """
        existing = self.get_expense_by_id(expense_id)
        if existing is None:
            raise ValidationError(f"No expense found with id {expense_id}.")

        fields_to_update = {}
        if amount is not None:
            fields_to_update["amount"] = validate_amount(amount)
        if category_id is not None:
            fields_to_update["category_id"] = category_id
        if date is not None:
            fields_to_update["date"] = validate_date(date)
        if description is not None:
            fields_to_update["description"] = description.strip()

        if not fields_to_update:
            return  # Nothing to update — avoid an empty, invalid SQL statement.

        set_clause = ", ".join(f"{field} = ?" for field in fields_to_update)
        values = list(fields_to_update.values()) + [expense_id]

        self.db.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?;", tuple(values)
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def delete_expense(self, expense_id: int) -> None:
        """Delete a single expense by id."""
        existing = self.get_expense_by_id(expense_id)
        if existing is None:
            raise ValidationError(f"No expense found with id {expense_id}.")
        self.db.execute("DELETE FROM expenses WHERE id = ?;", (expense_id,))

    # ------------------------------------------------------------------
    # READ / SEARCH / FILTER / SORT
    # ------------------------------------------------------------------
    def get_expense_by_id(self, expense_id: int) -> Optional[Expense]:
        """Fetch a single expense, joined with its category name."""
        row = self.db.fetch_one(self._base_select_query() + " WHERE e.id = ?;", (expense_id,))
        return self._row_to_expense(row) if row else None

    def get_all_expenses(self, sort_by: str = "date", descending: bool = True) -> list[Expense]:
        """
        Return every expense, joined with category names, sorted by the
        requested field.

        `sort_by` is validated against an allow-list (see _sort_column)
        rather than being inserted directly into the SQL string. This
        prevents SQL injection through the sort parameter — a subtle risk
        beginners often miss because "it's just a column name, not user
        data," but if it ever comes from CLI input, it IS user data.
        """
        column = self._sort_column(sort_by)
        direction = "DESC" if descending else "ASC"
        query = f"{self._base_select_query()} ORDER BY {column} {direction};"
        rows = self.db.fetch_all(query)
        return [self._row_to_expense(row) for row in rows]

    def search_expenses(self, keyword: str) -> list[Expense]:
        """Case-insensitive search of the description field."""
        query = f"{self._base_select_query()} WHERE e.description LIKE ? ORDER BY e.date DESC;"
        rows = self.db.fetch_all(query, (f"%{keyword}%",))
        return [self._row_to_expense(row) for row in rows]

    def filter_by_category(self, category_id: int) -> list[Expense]:
        query = f"{self._base_select_query()} WHERE e.category_id = ? ORDER BY e.date DESC;"
        rows = self.db.fetch_all(query, (category_id,))
        return [self._row_to_expense(row) for row in rows]

    def filter_by_month(self, month: str) -> list[Expense]:
        """month is a 'YYYY-MM' string. We use SQLite's strftime to extract
        the year-month portion of the stored date for comparison."""
        query = (
            f"{self._base_select_query()} "
            "WHERE strftime('%Y-%m', e.date) = ? ORDER BY e.date DESC;"
        )
        rows = self.db.fetch_all(query, (month,))
        return [self._row_to_expense(row) for row in rows]

    def filter_by_date_range(self, start_date: str, end_date: str) -> list[Expense]:
        query = f"{self._base_select_query()} WHERE e.date BETWEEN ? AND ? ORDER BY e.date DESC;"
        rows = self.db.fetch_all(query, (start_date, end_date))
        return [self._row_to_expense(row) for row in rows]

    def filter_by_amount_range(self, min_amount: float, max_amount: float) -> list[Expense]:
        query = (
            f"{self._base_select_query()} "
            "WHERE e.amount BETWEEN ? AND ? ORDER BY e.amount DESC;"
        )
        rows = self.db.fetch_all(query, (min_amount, max_amount))
        return [self._row_to_expense(row) for row in rows]

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------
    @staticmethod
    def _base_select_query() -> str:
        """
        Shared SELECT...JOIN fragment used by every read method above.

        Defining this once avoids repeating the same JOIN in eight
        different methods (the "Don't Repeat Yourself" / DRY principle).
        We JOIN categories so every Expense object comes back already
        knowing its category's NAME, not just its numeric id.
        """
        return """
            SELECT e.id, e.amount, e.category_id, e.description, e.date,
                   c.name AS category_name
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
        """

    @staticmethod
    def _sort_column(sort_by: str) -> str:
        """
        Translate a user-facing sort key into a safe, allow-listed SQL
        column expression. Anything not in this dictionary raises an
        error rather than being inserted into the query string directly.
        """
        allowed = {
            "date": "e.date",
            "amount": "e.amount",
            "category": "c.name",
        }
        if sort_by not in allowed:
            raise ValidationError(
                f"Cannot sort by '{sort_by}'. Choose from: {', '.join(allowed)}."
            )
        return allowed[sort_by]

    @staticmethod
    def _row_to_expense(row) -> Expense:
        """Convert a raw sqlite3.Row (from a JOIN query) into an Expense object."""
        return Expense(
            id=row["id"],
            amount=row["amount"],
            category_id=row["category_id"],
            date=row["date"],
            description=row["description"] or "",
            category_name=row["category_name"],
        )


class BudgetManager:
    """
    Handles setting and checking monthly budgets.
    """

    def __init__(self, db: DatabaseManager, expense_manager: ExpenseManager) -> None:
        self.db = db
        self.expense_manager = expense_manager

    def set_budget(self, month: str, amount: str) -> None:
        """
        Set (or overwrite) the budget for a given month.

        `INSERT ... ON CONFLICT(month) DO UPDATE` is SQLite's "upsert"
        syntax: insert a new row, but if the UNIQUE `month` constraint
        would be violated, update the existing row instead. This avoids
        the beginner pattern of "SELECT to check if it exists, then
        decide whether to INSERT or UPDATE" — one atomic statement does
        both safely.
        """
        clean_amount = validate_amount(amount)
        self.db.execute(
            """
            INSERT INTO budgets (month, amount) VALUES (?, ?)
            ON CONFLICT(month) DO UPDATE SET amount = excluded.amount;
            """,
            (month, clean_amount),
        )

    def get_budget(self, month: str) -> Optional[float]:
        """Return the budget amount for a month, or None if not set."""
        row = self.db.fetch_one("SELECT amount FROM budgets WHERE month = ?;", (month,))
        return row["amount"] if row else None

    def get_budget_status(self, month: str) -> dict:
        """
        Compute a full budget status snapshot for a month:
            - budget amount
            - total spent
            - remaining amount
            - percentage used
            - whether the warning threshold has been crossed

        Returning a dictionary here (rather than several separate method
        calls) keeps this one "unit of information" atomic and easy for
        main.py to display in a single formatted block.
        """
        budget = self.get_budget(month)
        expenses = self.expense_manager.filter_by_month(month)
        total_spent = sum(expense.amount for expense in expenses)

        if budget is None:
            return {
                "month": month,
                "budget": None,
                "spent": total_spent,
                "remaining": None,
                "percent_used": None,
                "over_budget": False,
                "warning": False,
            }

        remaining = budget - total_spent
        percent_used = (total_spent / budget * 100) if budget > 0 else 0

        return {
            "month": month,
            "budget": budget,
            "spent": total_spent,
            "remaining": remaining,
            "percent_used": round(percent_used, 2),
            "over_budget": total_spent > budget,
            "warning": percent_used >= BUDGET_WARNING_THRESHOLD,
        }
