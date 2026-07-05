"""
main.py
=======
The entry point of the application, and the ONLY file that:
    1. Talks directly to the user (input()/print()).
    2. Parses command-line arguments.
    3. Wires together DatabaseManager + all the service/report/chart
       classes and calls their methods.

Every other file exists so that this file can stay short and readable.
This is the "thin controller" pattern: main.py orchestrates, it doesn't
implement business logic itself.

Django connection:
-------------------
main.py plays the same role as a Django "view" — it receives a request
(here, a CLI command instead of an HTTP request), calls into the service/
model layer to do the real work, and formats a response (printed text
instead of an HTML page or JSON). The mental model transfers directly.
"""

import argparse
import sys

from config import ensure_directories_exist, APP_NAME, APP_VERSION
from database import DatabaseManager
from reports import CSVExporter, ReportGenerator
from services import (
    BudgetManager,
    CategoryManager,
    DuplicateCategoryError,
    ExpenseManager,
)
from utils import ValidationError, current_month, print_table, parse_month
from visualization import ChartGenerator


# ==========================================================================
# ARGPARSE COMMAND HANDLERS
# ==========================================================================
# Each function below corresponds to one CLI command (e.g. `python main.py
# add`). They all take the parsed `args` namespace plus the shared manager
# objects, so we're not relying on any global state.

def handle_add(args, expense_manager: ExpenseManager, category_manager: CategoryManager) -> None:
    """Handle: python main.py add --amount 500 --category Food --date 2026-07-05 --description "Lunch" """
    category = category_manager.get_category_by_name(args.category)
    if category is None:
        print(f"Category '{args.category}' not found. Use 'view-categories' to see valid options.")
        return

    expense = expense_manager.add_expense(
        amount=args.amount,
        category_id=category.id,
        date=args.date,
        description=args.description or "",
    )
    print(f"Expense added successfully: {expense}")


def handle_view(args, expense_manager: ExpenseManager) -> None:
    """Handle: python main.py view [--sort-by date|amount|category] [--desc]"""
    expenses = expense_manager.get_all_expenses(sort_by=args.sort_by, descending=not args.asc)
    _print_expenses_table(expenses)


def handle_update(args, expense_manager: ExpenseManager, category_manager: CategoryManager) -> None:
    """Handle: python main.py update --id 3 --amount 600 """
    category_id = None
    if args.category:
        category = category_manager.get_category_by_name(args.category)
        if category is None:
            print(f"Category '{args.category}' not found.")
            return
        category_id = category.id

    expense_manager.update_expense(
        expense_id=args.id,
        amount=args.amount,
        category_id=category_id,
        date=args.date,
        description=args.description,
    )
    print(f"Expense {args.id} updated successfully.")


def handle_delete(args, expense_manager: ExpenseManager) -> None:
    """Handle: python main.py delete --id 3"""
    expense_manager.delete_expense(args.id)
    print(f"Expense {args.id} deleted successfully.")


def handle_search(args, expense_manager: ExpenseManager) -> None:
    """Handle: python main.py search --keyword lunch"""
    expenses = expense_manager.search_expenses(args.keyword)
    _print_expenses_table(expenses)


def handle_filter(args, expense_manager: ExpenseManager, category_manager: CategoryManager) -> None:
    """Handle: python main.py filter --category Food | --month 2026-07 |
    --start 2026-07-01 --end 2026-07-31 | --min 100 --max 500"""
    if args.category:
        category = category_manager.get_category_by_name(args.category)
        if category is None:
            print(f"Category '{args.category}' not found.")
            return
        expenses = expense_manager.filter_by_category(category.id)
    elif args.month:
        expenses = expense_manager.filter_by_month(args.month)
    elif args.start and args.end:
        expenses = expense_manager.filter_by_date_range(args.start, args.end)
    elif args.min is not None and args.max is not None:
        expenses = expense_manager.filter_by_amount_range(args.min, args.max)
    else:
        print("Specify one filter: --category, --month, --start/--end, or --min/--max.")
        return
    _print_expenses_table(expenses)


def handle_categories(args, category_manager: CategoryManager) -> None:
    """Handle: python main.py categories --add Food | --edit 1 NewName | --delete 1 | (no args = list)"""
    if args.add:
        category = category_manager.create_category(args.add)
        print(f"Category created: {category}")
    elif args.delete is not None:
        category_manager.delete_category(args.delete)
        print(f"Category {args.delete} deleted.")
    else:
        categories = category_manager.get_all_categories()
        print_table(["ID", "Name"], [[c.id, c.name] for c in categories])


def handle_budget(args, budget_manager: BudgetManager) -> None:
    """Handle: python main.py budget --month 2026-07 --set 50000 | --check 2026-07"""
    month = parse_month(args.month or current_month())
    if args.set is not None:
        budget_manager.set_budget(month, str(args.set))
        print(f"Budget for {month} set to {float(args.set):.2f}.")

    status = budget_manager.get_budget_status(month)
    _print_budget_status(status)


def handle_report(args, report_generator: ReportGenerator) -> None:
    """Handle: python main.py report --type monthly --month 2026-07"""
    if args.type == "monthly":
        report = report_generator.monthly_report(args.month or current_month())
    elif args.type == "weekly":
        if not (args.start and args.end):
            print("Weekly report requires --start and --end dates.")
            return
        report = report_generator.weekly_report(args.start, args.end)
    elif args.type == "yearly":
        report = report_generator.yearly_report(args.year)
    else:
        print(f"Unknown report type: {args.type}")
        return
    _print_report(report)


def handle_export(args, expense_manager: ExpenseManager, report_generator: ReportGenerator, csv_exporter: CSVExporter) -> None:
    """Handle: python main.py export --type all|monthly --month 2026-07"""
    if args.type == "all":
        expenses = expense_manager.get_all_expenses()
        path = csv_exporter.export_expenses(expenses)
    elif args.type == "monthly":
        report = report_generator.monthly_report(args.month or current_month())
        path = csv_exporter.export_report(report)
    else:
        print(f"Unknown export type: {args.type}")
        return
    print(f"Exported to: {path}")


def handle_chart(args, report_generator: ReportGenerator, chart_generator: ChartGenerator) -> None:
    """Handle: python main.py chart --type bar|pie|trend --month 2026-07"""
    month = args.month or current_month()
    report = report_generator.monthly_report(month)
    breakdown = report["category_breakdown"]

    if not breakdown:
        print(f"No expenses found for {month} — nothing to chart.")
        return

    if args.type == "bar":
        path = chart_generator.bar_chart(breakdown, title=f"Spending by Category ({month})")
    elif args.type == "pie":
        path = chart_generator.pie_chart(breakdown, title=f"Spending Distribution ({month})")
    elif args.type == "trend":
        # Build a dict of {month: total} across ALL months that have data.
        all_expenses = report_generator.expense_manager.get_all_expenses()
        months = sorted({e.date[:7] for e in all_expenses})
        monthly_totals = {
            m: report_generator.total_expenses(report_generator.expense_manager.filter_by_month(m))
            for m in months
        }
        path = chart_generator.monthly_trend_line_chart(monthly_totals)
    else:
        print(f"Unknown chart type: {args.type}")
        return
    print(f"Chart saved to: {path}")


# ==========================================================================
# DISPLAY HELPERS
# ==========================================================================

def _print_expenses_table(expenses) -> None:
    if not expenses:
        print("No expenses found.")
        return
    rows = [
        [e.id, e.date, e.category_name, f"{e.amount:.2f}", e.description]
        for e in expenses
    ]
    print_table(["ID", "Date", "Category", "Amount", "Description"], rows)


def _print_budget_status(status: dict) -> None:
    print(f"\n--- Budget Status for {status['month']} ---")
    if status["budget"] is None:
        print(f"No budget set. Total spent so far: {status['spent']:.2f}")
        return
    print(f"Budget:     {status['budget']:.2f}")
    print(f"Spent:      {status['spent']:.2f}")
    print(f"Remaining:  {status['remaining']:.2f}")
    print(f"Used:       {status['percent_used']}%")
    if status["over_budget"]:
        print("⚠️  WARNING: You have EXCEEDED your budget for this month!")
    elif status["warning"]:
        print(f"⚠️  WARNING: You have used over {status['percent_used']}% of your budget.")


def _print_report(report: dict) -> None:
    print(f"\n=== {report['title']} ===")
    print(f"Total spent:    {report['total']:.2f}")
    print(f"Transactions:   {report['count']}")
    print(f"Average:        {report['average']:.2f}")
    print(f"Highest:        {report['highest']}")
    print(f"Lowest:         {report['lowest']}")
    print(f"Most used cat.: {report['most_used_category']}")
    print("\nCategory breakdown:")
    for category, total in report["category_breakdown"].items():
        print(f"  {category:<15} {total:>10.2f}")


# ==========================================================================
# INTERACTIVE MENU (beginner-friendly alternative to argparse commands)
# ==========================================================================

def run_interactive_menu(
    expense_manager: ExpenseManager,
    category_manager: CategoryManager,
    budget_manager: BudgetManager,
    report_generator: ReportGenerator,
    csv_exporter: CSVExporter,
    chart_generator: ChartGenerator,
) -> None:
    """
    A simple numbered text menu, looped until the user chooses to exit.

    This exists alongside the argparse commands because recruiters and
    beginners often find a guided menu easier to demo live than
    remembering flag names. Both interfaces share the exact same
    service-layer methods underneath — proof that the business logic is
    properly decoupled from any one "front end."
    """
    menu = """
==============================
   EXPENSE TRACKER - MAIN MENU
==============================
1. Add expense
2. View all expenses
3. Delete expense
4. View categories
5. Add category
6. Set / check monthly budget
7. Monthly report
8. Export all expenses to CSV
9. Generate charts (bar + pie) for a month
0. Exit
"""
    while True:
        print(menu)
        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                amount = input("Amount: ").strip()
                category_name = input("Category: ").strip()
                date = input("Date (YYYY-MM-DD): ").strip()
                description = input("Description (optional): ").strip()
                category = category_manager.get_category_by_name(category_name)
                if category is None:
                    print(f"Category '{category_name}' not found.")
                    continue
                expense = expense_manager.add_expense(amount, category.id, date, description)
                print(f"Added: {expense}")

            elif choice == "2":
                _print_expenses_table(expense_manager.get_all_expenses())

            elif choice == "3":
                expense_id = int(input("Expense ID to delete: ").strip())
                expense_manager.delete_expense(expense_id)
                print("Deleted.")

            elif choice == "4":
                categories = category_manager.get_all_categories()
                print_table(["ID", "Name"], [[c.id, c.name] for c in categories])

            elif choice == "5":
                name = input("New category name: ").strip()
                category = category_manager.create_category(name)
                print(f"Created: {category}")

            elif choice == "6":
                month = input(f"Month (YYYY-MM) [{current_month()}]: ").strip() or current_month()
                set_amount = input("Set new budget amount (leave blank to just check): ").strip()
                if set_amount:
                    budget_manager.set_budget(month, set_amount)
                status = budget_manager.get_budget_status(month)
                _print_budget_status(status)

            elif choice == "7":
                month = input(f"Month (YYYY-MM) [{current_month()}]: ").strip() or current_month()
                report = report_generator.monthly_report(month)
                _print_report(report)

            elif choice == "8":
                path = csv_exporter.export_expenses(expense_manager.get_all_expenses())
                print(f"Exported to: {path}")

            elif choice == "9":
                month = input(f"Month (YYYY-MM) [{current_month()}]: ").strip() or current_month()
                report = report_generator.monthly_report(month)
                if not report["category_breakdown"]:
                    print(f"No expenses found for {month}.")
                    continue
                bar_path = chart_generator.bar_chart(report["category_breakdown"], title=f"Spending by Category ({month})")
                pie_path = chart_generator.pie_chart(report["category_breakdown"], title=f"Spending Distribution ({month})")
                print(f"Bar chart saved to: {bar_path}")
                print(f"Pie chart saved to: {pie_path}")

            elif choice == "0":
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Please select a number from the menu.")

        except ValidationError as e:
            print(f"Input error: {e}")
        except DuplicateCategoryError as e:
            print(f"Duplicate: {e}")
        except ValueError:
            print("Please enter a valid number where expected.")
        except Exception as e:  # noqa: BLE001 - top-level safety net for the CLI
            print(f"Unexpected error: {e}")


# ==========================================================================
# ARGPARSE SETUP
# ==========================================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build the full argparse command tree. Using subparsers gives us the
    `python main.py <command> --flags` style seen in real tools like git
    and pip — a very deliberate design choice to make this project feel
    like a "real" CLI tool rather than a toy script.
    """
    parser = argparse.ArgumentParser(
        prog="main.py", description=f"{APP_NAME} v{APP_VERSION}"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("--amount", required=True)
    add_parser.add_argument("--category", required=True)
    add_parser.add_argument("--date", required=True)
    add_parser.add_argument("--description", default="")

    # --- view ---
    view_parser = subparsers.add_parser("view", help="View all expenses")
    view_parser.add_argument("--sort-by", default="date", choices=["date", "amount", "category"])
    view_parser.add_argument("--asc", action="store_true", help="Sort ascending instead of descending")

    # --- update ---
    update_parser = subparsers.add_parser("update", help="Update an existing expense")
    update_parser.add_argument("--id", required=True, type=int)
    update_parser.add_argument("--amount")
    update_parser.add_argument("--category")
    update_parser.add_argument("--date")
    update_parser.add_argument("--description")

    # --- delete ---
    delete_parser = subparsers.add_parser("delete", help="Delete an expense")
    delete_parser.add_argument("--id", required=True, type=int)

    # --- search ---
    search_parser = subparsers.add_parser("search", help="Search expenses by keyword")
    search_parser.add_argument("--keyword", required=True)

    # --- filter ---
    filter_parser = subparsers.add_parser("filter", help="Filter expenses")
    filter_parser.add_argument("--category")
    filter_parser.add_argument("--month")
    filter_parser.add_argument("--start")
    filter_parser.add_argument("--end")
    filter_parser.add_argument("--min", type=float)
    filter_parser.add_argument("--max", type=float)

    # --- categories ---
    categories_parser = subparsers.add_parser("categories", help="Manage categories")
    categories_parser.add_argument("--add")
    categories_parser.add_argument("--delete", type=int)

    # --- budget ---
    budget_parser = subparsers.add_parser("budget", help="Set or check monthly budget")
    budget_parser.add_argument("--month")
    budget_parser.add_argument("--set", type=float)

    # --- report ---
    report_parser = subparsers.add_parser("report", help="Generate a report")
    report_parser.add_argument("--type", required=True, choices=["monthly", "weekly", "yearly"])
    report_parser.add_argument("--month")
    report_parser.add_argument("--start")
    report_parser.add_argument("--end")
    report_parser.add_argument("--year")

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Export to CSV")
    export_parser.add_argument("--type", required=True, choices=["all", "monthly"])
    export_parser.add_argument("--month")

    # --- chart ---
    chart_parser = subparsers.add_parser("chart", help="Generate a chart")
    chart_parser.add_argument("--type", required=True, choices=["bar", "pie", "trend"])
    chart_parser.add_argument("--month")

    # --- menu ---
    subparsers.add_parser("menu", help="Launch the interactive text menu")

    return parser


def main() -> None:
    """
    Application entry point:
        1. Ensure folders exist.
        2. Open the database (creates tables/seeds categories if needed).
        3. Build all service-layer objects, injecting the shared db.
        4. Parse CLI args and dispatch to the right handler — or launch
           the interactive menu if no command (or 'menu') was given.
        5. Always close the database connection on the way out, even if
           an error occurred (the try/finally guarantees this).
    """
    ensure_directories_exist()
    db = DatabaseManager()

    try:
        expense_manager = ExpenseManager(db)
        category_manager = CategoryManager(db)
        budget_manager = BudgetManager(db, expense_manager)
        report_generator = ReportGenerator(expense_manager)
        csv_exporter = CSVExporter()
        chart_generator = ChartGenerator()

        parser = build_parser()
        args = parser.parse_args()

        try:
            if args.command is None or args.command == "menu":
                run_interactive_menu(
                    expense_manager, category_manager, budget_manager,
                    report_generator, csv_exporter, chart_generator,
                )
            elif args.command == "add":
                handle_add(args, expense_manager, category_manager)
            elif args.command == "view":
                handle_view(args, expense_manager)
            elif args.command == "update":
                handle_update(args, expense_manager, category_manager)
            elif args.command == "delete":
                handle_delete(args, expense_manager)
            elif args.command == "search":
                handle_search(args, expense_manager)
            elif args.command == "filter":
                handle_filter(args, expense_manager, category_manager)
            elif args.command == "categories":
                handle_categories(args, category_manager)
            elif args.command == "budget":
                handle_budget(args, budget_manager)
            elif args.command == "report":
                handle_report(args, report_generator)
            elif args.command == "export":
                handle_export(args, expense_manager, report_generator, csv_exporter)
            elif args.command == "chart":
                handle_chart(args, report_generator, chart_generator)

        except (ValidationError, DuplicateCategoryError) as e:
            print(f"Error: {e}")
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
