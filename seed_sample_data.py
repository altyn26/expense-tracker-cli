"""
seed_sample_data.py
====================
NOT part of the core application — a one-off helper script to populate
the database with realistic sample data, purely so the exported database,
CSV, charts, and terminal output examples in the README/portfolio look
like a real, lived-in project instead of an empty shell.

Run once with: python seed_sample_data.py
"""

from database import DatabaseManager
from services import BudgetManager, CategoryManager, ExpenseManager

db = DatabaseManager()
expense_manager = ExpenseManager(db)
category_manager = CategoryManager(db)
budget_manager = BudgetManager(db, expense_manager)

categories = {c.name: c.id for c in category_manager.get_all_categories()}

sample_expenses = [
    (450, "Food", "2026-05-03", "Groceries - Al-Fatah"),
    (1200, "Rent", "2026-05-01", "May house rent"),
    (200, "Transport", "2026-05-05", "Careem rides"),
    (80, "Entertainment", "2026-05-10", "Netflix subscription"),
    (350, "Food", "2026-05-15", "Dinner with friends"),
    (600, "Shopping", "2026-05-18", "New jacket"),
    (150, "Utilities", "2026-05-20", "Electricity bill"),
    (500, "Food", "2026-06-02", "Groceries"),
    (1200, "Rent", "2026-06-01", "June house rent"),
    (220, "Transport", "2026-06-06", "Fuel"),
    (90, "Entertainment", "2026-06-12", "Movie night"),
    (400, "Health", "2026-06-14", "Doctor visit + medicine"),
    (300, "Education", "2026-06-20", "Online course"),
    (700, "Food", "2026-07-01", "Groceries + Eid stock up"),
    (1200, "Rent", "2026-07-01", "July house rent"),
    (250, "Transport", "2026-07-03", "Fuel + rickshaw"),
    (120, "Entertainment", "2026-07-04", "Cinema with friends"),
    (180, "Utilities", "2026-07-05", "Internet bill"),
    (90, "Other", "2026-07-05", "Miscellaneous"),
]

for amount, category_name, date, description in sample_expenses:
    category_id = categories[category_name]
    expense_manager.add_expense(str(amount), category_id, date, description)

budget_manager.set_budget("2026-07", "3000")
budget_manager.set_budget("2026-06", "3200")
budget_manager.set_budget("2026-05", "3000")

print(f"Seeded {len(sample_expenses)} sample expenses and 3 monthly budgets.")
db.close()
