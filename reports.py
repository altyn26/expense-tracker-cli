"""
reports.py
==========
Contains ReportGenerator (computes statistics/summaries) and CSVExporter
(writes expense data to CSV files).

Separating "computing a report" from "displaying a report" (done in
main.py) and from "exporting a report" (CSVExporter) keeps each class
focused on exactly one job — a principle called the Single Responsibility
Principle (SRP). It's one of the most reused ideas in professional
software design, including throughout Django's own codebase.
"""

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import EXPORTS_DIR
from models import Expense
from services import ExpenseManager


class ReportGenerator:
    """
    Computes statistics and summaries over a list of expenses.

    Every method here takes a pre-fetched list[Expense] rather than
    querying the database itself. This makes ReportGenerator easy to
    test (you can pass in a hand-built list of fake Expense objects) and
    keeps database access confined to ExpenseManager/DatabaseManager.
    """

    def __init__(self, expense_manager: ExpenseManager) -> None:
        self.expense_manager = expense_manager

    def total_expenses(self, expenses: list[Expense]) -> float:
        """Sum of all expense amounts. Returns 0.0 for an empty list."""
        return round(sum(expense.amount for expense in expenses), 2)

    def category_breakdown(self, expenses: list[Expense]) -> dict[str, float]:
        """
        Return {category_name: total_spent} for the given expenses.

        We use a plain dict + manual accumulation rather than a
        third-party library, keeping this dependency-free and easy to
        understand line by line.
        """
        breakdown: dict[str, float] = {}
        for expense in expenses:
            name = expense.category_name or f"Category#{expense.category_id}"
            breakdown[name] = breakdown.get(name, 0) + expense.amount
        return {name: round(total, 2) for name, total in breakdown.items()}

    def highest_expense(self, expenses: list[Expense]) -> Optional[Expense]:
        """Return the single largest expense, or None if the list is empty."""
        if not expenses:
            return None
        return max(expenses, key=lambda e: e.amount)

    def lowest_expense(self, expenses: list[Expense]) -> Optional[Expense]:
        """Return the single smallest expense, or None if the list is empty."""
        if not expenses:
            return None
        return min(expenses, key=lambda e: e.amount)

    def average_expense(self, expenses: list[Expense]) -> float:
        """Mean of all expense amounts. Returns 0.0 for an empty list to
        avoid a ZeroDivisionError — a classic beginner crash."""
        if not expenses:
            return 0.0
        return round(sum(e.amount for e in expenses) / len(expenses), 2)

    def most_used_category(self, expenses: list[Expense]) -> Optional[str]:
        """
        Return the category name that appears most FREQUENTLY (by count
        of transactions, not by total amount spent — that's a different
        question, answered by category_breakdown() instead).

        collections.Counter is the standard-library tool purpose-built
        for "count occurrences of each item" — cleaner than a manual
        dictionary-increment loop.
        """
        if not expenses:
            return None
        names = [e.category_name or f"Category#{e.category_id}" for e in expenses]
        return Counter(names).most_common(1)[0][0]

    def monthly_report(self, month: str) -> dict:
        """Build a complete statistics dictionary for one month (YYYY-MM)."""
        expenses = self.expense_manager.filter_by_month(month)
        return self._build_report_dict(f"Monthly Report ({month})", expenses)

    def weekly_report(self, start_date: str, end_date: str) -> dict:
        """Build a complete statistics dictionary for a 7-day (or any)
        date range, reusing filter_by_date_range under the hood."""
        expenses = self.expense_manager.filter_by_date_range(start_date, end_date)
        return self._build_report_dict(
            f"Weekly Report ({start_date} to {end_date})", expenses
        )

    def yearly_report(self, year: str) -> dict:
        """Build a complete statistics dictionary for a whole year (YYYY)."""
        expenses = self.expense_manager.filter_by_date_range(f"{year}-01-01", f"{year}-12-31")
        return self._build_report_dict(f"Yearly Report ({year})", expenses)

    def _build_report_dict(self, title: str, expenses: list[Expense]) -> dict:
        """
        Shared logic for assembling the final report dictionary, used by
        monthly/weekly/yearly report methods to avoid duplicating this
        five-line assembly three times (DRY principle again).
        """
        highest = self.highest_expense(expenses)
        lowest = self.lowest_expense(expenses)
        return {
            "title": title,
            "total": self.total_expenses(expenses),
            "count": len(expenses),
            "average": self.average_expense(expenses),
            "highest": highest,
            "lowest": lowest,
            "most_used_category": self.most_used_category(expenses),
            "category_breakdown": self.category_breakdown(expenses),
            "expenses": expenses,
        }


class CSVExporter:
    """
    Handles writing expense data out to CSV files inside the exports/
    folder, using Python's built-in `csv` module (no pandas dependency
    needed for a task this simple).
    """

    def __init__(self, exports_dir: Path = EXPORTS_DIR) -> None:
        self.exports_dir = exports_dir

    def export_expenses(self, expenses: list[Expense], filename: Optional[str] = None) -> Path:
        """
        Write a list of Expense objects to a CSV file.

        Returns the full Path to the created file so callers (main.py)
        can print it back to the user immediately.

        We generate a timestamped default filename if none is given, so
        repeated exports never silently overwrite each other.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"expenses_{timestamp}.csv"

        filepath = self.exports_dir / filename

        with open(filepath, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["ID", "Date", "Category", "Amount", "Description"])
            for expense in expenses:
                writer.writerow(
                    [
                        expense.id,
                        expense.date,
                        expense.category_name or expense.category_id,
                        f"{expense.amount:.2f}",
                        expense.description,
                    ]
                )
        return filepath

    def export_report(self, report: dict, filename: Optional[str] = None) -> Path:
        """
        Write a full report dictionary (from ReportGenerator) to CSV —
        includes both the summary statistics AND the raw expense rows,
        so the exported file is useful on its own without the CLI.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.csv"

        filepath = self.exports_dir / filename

        with open(filepath, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Report", report["title"]])
            writer.writerow(["Total", f"{report['total']:.2f}"])
            writer.writerow(["Count", report["count"]])
            writer.writerow(["Average", f"{report['average']:.2f}"])
            writer.writerow(
                ["Highest", str(report["highest"]) if report["highest"] else "N/A"]
            )
            writer.writerow(
                ["Lowest", str(report["lowest"]) if report["lowest"] else "N/A"]
            )
            writer.writerow(["Most Used Category", report["most_used_category"] or "N/A"])
            writer.writerow([])
            writer.writerow(["Category", "Total Spent"])
            for category, total in report["category_breakdown"].items():
                writer.writerow([category, f"{total:.2f}"])
            writer.writerow([])
            writer.writerow(["ID", "Date", "Category", "Amount", "Description"])
            for expense in report["expenses"]:
                writer.writerow(
                    [
                        expense.id,
                        expense.date,
                        expense.category_name or expense.category_id,
                        f"{expense.amount:.2f}",
                        expense.description,
                    ]
                )
        return filepath
