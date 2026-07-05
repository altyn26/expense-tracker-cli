# 💰 Expense Tracker CLI

A complete, real-world command-line Expense & Budget Tracker built in pure Python — designed as a portfolio project demonstrating clean architecture, OOP, SQLite database design, CSV reporting, and data visualization, while doubling as a stepping stone toward Django/DRF.

---

## 📖 Overview

This is not a toy script — it's a small, layered application built the way production software is structured:

```
CLI (main.py) → Service Layer (services.py) → Database Layer (database.py) → SQLite
```

Each layer has exactly one job, which keeps the codebase easy to extend, test, and eventually port into a Django project (models → Django models, services → Django services/views, CLI → Django views/DRF serializers).

---

## ✨ Features

**Expense Management**
- Add, update, delete, view expenses
- Search by keyword
- Filter by category, month, date range, or amount range
- Sort by date, amount, or category

**Category Management**
- Create, edit, delete, and list categories
- Duplicate-name prevention (case-insensitive)
- Safe deletion (blocked if expenses still reference the category)

**Budgeting**
- Set a monthly budget
- Check remaining budget and % used
- Automatic warning when a spending threshold is crossed

**Reports**
- Monthly / weekly / yearly reports
- Total, average, highest, lowest expense
- Category-wise breakdown
- Most-used category

**CSV Export**
- Export all expenses
- Export a filtered set
- Export a full monthly report

**Charts (matplotlib)**
- Bar chart — spending by category
- Pie chart — spending distribution
- Line chart — monthly spending trend
- Grouped bar chart — category comparison across two periods

**Robust validation & error handling**
- Rejects negative/zero amounts, invalid dates, empty inputs, duplicate categories, unknown commands, and database integrity violations — all with clear, human-readable messages (no raw tracebacks).

---

## 🗂 Folder Structure

```
expense_tracker/
│
├── main.py              # CLI entry point + argparse commands + interactive menu
├── database.py           # DatabaseManager — all raw SQLite access
├── models.py              # Expense & Category data classes
├── services.py            # ExpenseManager, CategoryManager, BudgetManager (business logic)
├── reports.py              # ReportGenerator, CSVExporter
├── visualization.py         # ChartGenerator (matplotlib)
├── utils.py                  # Validation helpers, table printer
├── config.py                  # Paths, constants, defaults
├── seed_sample_data.py          # Optional: populates sample data for demos
├── README.md
├── requirements.txt
├── expenses.db              # SQLite database (auto-created on first run)
├── exports/                # CSV exports land here
├── charts/                  # Generated chart PNGs land here
└── data/                      # Reserved for future data files
```

---

## ⚙️ Installation

```bash
git clone https://github.com/<your-username>/expense-tracker-cli.git
cd expense-tracker-cli
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

---

## 🚀 Usage

### Interactive menu (beginner-friendly)
```bash
python main.py
```

### Command-line mode
```bash
# Add an expense
python main.py add --amount 500 --category Food --date 2026-07-05 --description "Lunch"

# View all expenses
python main.py view --sort-by amount

# Update / delete
python main.py update --id 3 --amount 600
python main.py delete --id 3

# Search / filter
python main.py search --keyword lunch
python main.py filter --category Food
python main.py filter --month 2026-07
python main.py filter --start 2026-07-01 --end 2026-07-31
python main.py filter --min 100 --max 500

# Categories
python main.py categories
python main.py categories --add "Gym"
python main.py categories --delete 5

# Budget
python main.py budget --month 2026-07 --set 30000
python main.py budget --month 2026-07

# Reports
python main.py report --type monthly --month 2026-07
python main.py report --type weekly --start 2026-07-01 --end 2026-07-07
python main.py report --type yearly --year 2026

# Export
python main.py export --type all
python main.py export --type monthly --month 2026-07

# Charts
python main.py chart --type bar --month 2026-07
python main.py chart --type pie --month 2026-07
python main.py chart --type trend
```

---

## 🖼 Screenshots

> _Add screenshots here after running the app — placeholders below:_

- `screenshots/menu.png` — interactive menu
- `screenshots/view_table.png` — expense table output
- `screenshots/bar_chart.png` — category bar chart
- `screenshots/pie_chart.png` — spending pie chart

---

## 🔮 Future Improvements

- Multi-user support with authentication
- Recurring/subscription expense tracking
- REST API layer using Django REST Framework (natural next step)
- Web dashboard front-end (Django + Chart.js)
- Currency conversion support
- Export to PDF reports
- Undo/redo for destructive actions
- Unit test suite with pytest

---

## 🎓 Learning Outcomes

Building this project covers:
- Layered architecture (separation of concerns)
- Object-Oriented Programming (dataclasses, encapsulation, dependency injection)
- Parameterized SQL & SQL injection prevention
- SQLite schema design (foreign keys, constraints, upserts)
- CLI design with `argparse` subcommands
- Defensive input validation and custom exceptions
- Data visualization with `matplotlib`
- CSV file generation with the standard library
- Writing code that previews Django's own architecture (settings, models, ORM, service layers)

---

## 📄 License

MIT License — free to use, modify, and showcase in your own portfolio.
