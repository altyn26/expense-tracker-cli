"""
visualization.py
=================
ChartGenerator: turns expense data into saved chart image files using
matplotlib, our only third-party dependency.

Why matplotlib and not something fancier?
--------------------------------------------
matplotlib is the most widely used, most universally installed Python
plotting library. It has zero web-framework dependencies, works entirely
offline, and produces static image files — perfect for a CLI tool that
needs to save charts to disk rather than display them in a browser.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
# "Agg" is a non-interactive backend that renders directly to image files
# instead of trying to open a GUI window. This is ESSENTIAL for a CLI tool
# running in a terminal (or server) with no display available — without
# this line, matplotlib may crash with "no display found" errors.
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from config import CHARTS_DIR
from models import Expense
from services import ExpenseManager


class ChartGenerator:
    """
    Generates and saves matplotlib charts as PNG files inside charts/.

    Every method follows the same shape:
        1. Prepare the data (aggregate expenses into x/y values).
        2. Build the plot with matplotlib.
        3. Save it to disk with plt.savefig().
        4. Close the figure with plt.close() to free memory.

    Step 4 matters more than beginners expect: if you generate many
    charts in a loop without closing each figure, matplotlib keeps all of
    them in memory, which can slow down or crash a long-running script.
    """

    def __init__(self, charts_dir: Path = CHARTS_DIR) -> None:
        self.charts_dir = charts_dir

    def _timestamped_filename(self, prefix: str) -> Path:
        """Shared helper to build a unique output filename, avoiding
        overwriting a previous chart of the same type."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.charts_dir / f"{prefix}_{timestamp}.png"

    def bar_chart(self, category_totals: dict[str, float], title: str = "Spending by Category") -> Path:
        """
        Create a bar chart: one bar per category, height = total spent.

        category_totals is expected in the shape returned by
        ReportGenerator.category_breakdown(): {"Food": 1200.0, "Rent": 500}
        """
        categories = list(category_totals.keys())
        totals = list(category_totals.values())

        plt.figure(figsize=(10, 6))
        plt.bar(categories, totals, color="#4C72B0")
        plt.title(title)
        plt.xlabel("Category")
        plt.ylabel("Amount Spent")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()  # prevents axis labels from being cut off

        filepath = self._timestamped_filename("bar_chart")
        plt.savefig(filepath)
        plt.close()
        return filepath

    def pie_chart(self, category_totals: dict[str, float], title: str = "Spending Distribution") -> Path:
        """
        Create a pie chart showing each category's share of total
        spending. autopct='%1.1f%%' displays each slice's percentage with
        one decimal place directly on the chart.
        """
        categories = list(category_totals.keys())
        totals = list(category_totals.values())

        plt.figure(figsize=(8, 8))
        plt.pie(totals, labels=categories, autopct="%1.1f%%", startangle=90)
        plt.title(title)
        plt.axis("equal")  # ensures the pie is drawn as a circle, not an oval
        plt.tight_layout()

        filepath = self._timestamped_filename("pie_chart")
        plt.savefig(filepath)
        plt.close()
        return filepath

    def monthly_trend_line_chart(
        self, monthly_totals: dict[str, float], title: str = "Monthly Spending Trend"
    ) -> Path:
        """
        Create a line chart showing spending over multiple months.

        monthly_totals should be shaped like:
            {"2026-01": 3400.0, "2026-02": 2900.0, "2026-03": 4100.0}
        We sort by month key first so the line reads chronologically left
        to right, even if the caller built the dictionary out of order.
        """
        sorted_months = sorted(monthly_totals.keys())
        totals = [monthly_totals[month] for month in sorted_months]

        plt.figure(figsize=(10, 6))
        plt.plot(sorted_months, totals, marker="o", color="#DD8452", linewidth=2)
        plt.title(title)
        plt.xlabel("Month")
        plt.ylabel("Total Spent")
        plt.xticks(rotation=45, ha="right")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()

        filepath = self._timestamped_filename("monthly_trend")
        plt.savefig(filepath)
        plt.close()
        return filepath

    def category_comparison_chart(
        self, current_totals: dict[str, float], previous_totals: dict[str, float],
        title: str = "Category Comparison: This Month vs Last Month"
    ) -> Path:
        """
        Create a grouped (side-by-side) bar chart comparing spending per
        category across two periods — useful for spotting which
        categories increased or decreased month-over-month.

        This demonstrates a slightly more advanced matplotlib technique:
        manually positioning two sets of bars next to each other using
        an offset, since matplotlib doesn't do "grouped bars" natively.
        """
        # Union of category names across both periods, sorted for a
        # consistent, predictable chart layout.
        all_categories = sorted(set(current_totals) | set(previous_totals))
        current_values = [current_totals.get(cat, 0) for cat in all_categories]
        previous_values = [previous_totals.get(cat, 0) for cat in all_categories]

        x_positions = range(len(all_categories))
        bar_width = 0.35

        plt.figure(figsize=(10, 6))
        plt.bar(
            [x - bar_width / 2 for x in x_positions],
            previous_values,
            width=bar_width,
            label="Previous Period",
            color="#8C8C8C",
        )
        plt.bar(
            [x + bar_width / 2 for x in x_positions],
            current_values,
            width=bar_width,
            label="Current Period",
            color="#4C72B0",
        )
        plt.xticks(list(x_positions), all_categories, rotation=45, ha="right")
        plt.title(title)
        plt.xlabel("Category")
        plt.ylabel("Amount Spent")
        plt.legend()
        plt.tight_layout()

        filepath = self._timestamped_filename("category_comparison")
        plt.savefig(filepath)
        plt.close()
        return filepath
