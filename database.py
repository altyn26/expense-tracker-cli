"""
database.py
============
Handles ALL direct communication with the SQLite database.

Design principle: Separation of Concerns
------------------------------------------
No other file in this project is allowed to write raw SQL. Every other
module (services.py, reports.py, etc.) asks DatabaseManager to do it for
them. This means:

1. If we ever switch from SQLite to PostgreSQL/MySQL, we only rewrite
   THIS file — the rest of the app doesn't change.
2. SQL bugs (typos in queries, injection risks) are isolated to one place,
   making the app easier to test and audit.

Django connection:
-------------------
This is exactly the role Django's ORM (Object-Relational Mapper) plays.
In Django you almost never write raw SQL — you call `Model.objects.filter(...)`
and Django translates that into SQL behind the scenes. DatabaseManager here
is a hand-rolled, simplified version of that idea: a single gatekeeper
between your Python objects and the database.
"""

import sqlite3
from pathlib import Path
from typing import Any, Optional

from config import DATABASE_PATH, DEFAULT_CATEGORIES


class DatabaseManager:
    """
    Owns the SQLite connection and exposes safe, reusable methods for
    running queries. Every other module depends on an instance of this
    class instead of importing sqlite3 directly.

    Attributes:
        db_path (Path): Filesystem path to the .db file.
        connection (sqlite3.Connection): The active database connection.
    """

    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        """
        Initialize the DatabaseManager and immediately open a connection.

        Why open the connection in __init__ instead of lazily?
        ----------------------------------------------------------
        For a small CLI tool that lives for a single command invocation,
        keeping one connection open for the lifetime of the object is
        simpler and avoids "connection not open yet" bugs. In a long-lived
        server (like Django), connection handling is far more complex —
        but that complexity is exactly what Django's ORM hides from you.

        `check_same_thread=False` allows the connection to be used safely
        in this single-threaded CLI without sqlite3 raising thread-safety
        errors if we ever pass the connection between helper functions.
        """
        self.db_path = db_path
        self.connection: sqlite3.Connection = sqlite3.connect(
            str(self.db_path), check_same_thread=False
        )
        # row_factory lets us access columns by NAME (row["amount"]) instead
        # of only by index (row[2]). This makes downstream code far more
        # readable and less fragile if column order ever changes.
        self.connection.row_factory = sqlite3.Row

        # Enforce foreign key constraints. SQLite disables this by default
        # for backward-compatibility reasons — you must opt in explicitly.
        self.connection.execute("PRAGMA foreign_keys = ON;")

        self.create_tables()
        self._seed_default_categories()

    # ------------------------------------------------------------------
    # SCHEMA CREATION
    # ------------------------------------------------------------------
    def create_tables(self) -> None:
        """
        Create the categories, expenses, and budgets tables if they do
        not already exist.

        `CREATE TABLE IF NOT EXISTS` makes this method safe to call every
        single time the app starts — it will never wipe existing data.
        """
        categories_table = """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """

        # category_id is a FOREIGN KEY referencing categories(id).
        # ON DELETE RESTRICT means: you cannot delete a category that still
        # has expenses pointing to it. This prevents "orphaned" expenses
        # with a category_id that no longer exists anywhere — a very common
        # data-integrity bug in beginner database designs.
        expenses_table = """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
                ON DELETE RESTRICT
        );
        """

        # month is stored as "YYYY-MM" (e.g. "2026-07") and must be unique —
        # you can only have ONE budget per calendar month.
        budgets_table = """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL
        );
        """

        with self.connection:
            self.connection.execute(categories_table)
            self.connection.execute(expenses_table)
            self.connection.execute(budgets_table)

    def _seed_default_categories(self) -> None:
        """
        Insert the default category list from config.py, but only the
        ones that don't already exist.

        The leading underscore in `_seed_default_categories` is a Python
        convention meaning "internal use only — don't call this from
        outside the class." It's not enforced by the language, just a
        signal to other developers (and to future-you).

        `INSERT OR IGNORE` tells SQLite: try to insert this row, but if it
        violates the UNIQUE constraint on `name`, silently skip it instead
        of raising an error. This makes seeding idempotent (safe to run
        repeatedly with no side effects after the first run).
        """
        with self.connection:
            for category_name in DEFAULT_CATEGORIES:
                self.connection.execute(
                    "INSERT OR IGNORE INTO categories (name) VALUES (?);",
                    (category_name,),
                )

    # ------------------------------------------------------------------
    # GENERIC QUERY HELPERS
    # ------------------------------------------------------------------
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Run an INSERT, UPDATE, or DELETE statement and commit it.

        Parameters:
            query: SQL string with `?` placeholders.
            params: Values to safely substitute into the placeholders.

        SECURITY NOTE — SQL Injection:
        --------------------------------
        We NEVER use Python f-strings or .format() to build SQL, e.g.:
            f"DELETE FROM expenses WHERE id = {user_input}"   # DANGEROUS
        A malicious or malformed user_input could alter the query's
        meaning entirely. Instead we always use parameterized queries
        with `?` placeholders, letting sqlite3 escape values safely:
            "DELETE FROM expenses WHERE id = ?", (user_input,)
        This single habit prevents an entire category of security bugs,
        and it is exactly what Django's ORM does for you automatically
        under the hood.

        The `with self.connection:` context manager automatically commits
        on success or rolls back the ENTIRE transaction on any exception —
        so a crash mid-write can never leave the database half-updated.
        """
        with self.connection:
            cursor = self.connection.execute(query, params)
        return cursor

    def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT statement and return every matching row."""
        cursor = self.connection.execute(query, params)
        return cursor.fetchall()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Run a SELECT statement and return only the first matching row
        (or None if nothing matches)."""
        cursor = self.connection.execute(query, params)
        return cursor.fetchone()

    # ------------------------------------------------------------------
    # LIFECYCLE
    # ------------------------------------------------------------------
    def close(self) -> None:
        """
        Close the database connection cleanly.

        Always call this before the program exits. Leaving connections
        open isn't usually catastrophic for SQLite in a short-lived CLI
        script, but it's a professional habit that matters enormously in
        larger systems (unclosed connections cause resource leaks and,
        in multi-user databases, can hold locks that block other users).
        """
        self.connection.close()

    def __enter__(self) -> "DatabaseManager":
        """
        Enables using DatabaseManager as a context manager:

            with DatabaseManager() as db:
                db.fetch_all(...)

        This guarantees close() is always called, even if an exception
        happens inside the `with` block.
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Called automatically when the `with` block ends (successfully
        or via an exception). Ensures the connection is always closed."""
        self.close()
