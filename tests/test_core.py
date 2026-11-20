"""Baseline and regression tests for validation and the service layer.
Every test uses a temporary SQLite file; expenses.db is never touched."""
import pytest

from database import DatabaseManager
from services import CategoryManager, DuplicateCategoryError, ExpenseManager
from utils import ValidationError, validate_amount, validate_date


@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "test.db")
    yield manager
    manager.close()


# AC1: amount validation
@pytest.mark.parametrize("raw", ["abc", "", "0", "-5", "0.001", "10000001"])
def test_validate_amount_rejects_invalid(raw):
    with pytest.raises(ValidationError):
        validate_amount(raw)


@pytest.mark.parametrize(
    "raw, expected", [("0.01", 0.01), ("12.5", 12.5), ("10000000", 10_000_000.0)]
)
def test_validate_amount_accepts_valid(raw, expected):
    assert validate_amount(raw) == expected


# AC6 (finding F9): NaN must be rejected by validation
@pytest.mark.parametrize("raw", ["nan", "NaN", " nan "])
def test_validate_amount_rejects_nan(raw):
    with pytest.raises(ValidationError):
        validate_amount(raw)


# AC2: date validation
@pytest.mark.parametrize(
    "raw",
    ["", "   ", "2026-02-30", "2026/07/05", "05-07-2026", "abc", "2026-13-01"],
)
def test_validate_date_rejects_invalid(raw):
    with pytest.raises(ValidationError):
        validate_date(raw)


@pytest.mark.parametrize(
    "raw, expected", [("2026-07-05", "2026-07-05"), (" 2026-07-05 ", "2026-07-05")]
)
def test_validate_date_accepts_valid(raw, expected):
    assert validate_date(raw) == expected


# AC3: duplicate category names are rejected, ignoring case
def test_duplicate_category_rejected(db):
    categories = CategoryManager(db)
    categories.create_category("Zebra")
    with pytest.raises(DuplicateCategoryError):
        categories.create_category("zebra")


# AC4: unknown sort key is rejected (allow-list)
def test_unknown_sort_key_rejected(db):
    with pytest.raises(ValidationError):
        ExpenseManager(db).get_all_expenses(sort_by="bogus")


# AC5: a saved expense can be read back unchanged
def test_added_expense_can_be_read_back(db):
    category = CategoryManager(db).get_all_categories()[0]
    manager = ExpenseManager(db)
    added = manager.add_expense("12.50", category.id, "2026-07-05", "lunch")
    fetched = manager.get_expense_by_id(added.id)
    assert fetched is not None
    assert fetched.amount == 12.5
    assert fetched.date == "2026-07-05"
    assert fetched.description == "lunch"