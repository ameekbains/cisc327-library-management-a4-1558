import pytest
from database import get_db_connection
from services.library_service import calculate_late_fee_for_book
from conftest import test_setup
from datetime import timedelta, datetime

def add_row_to_borrowed_books(patron_id: str, book_id: int, borrow_date: datetime, due_date: datetime, return_date=None) -> None:
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date, return_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (patron_id, book_id, borrow_date, due_date, return_date),
    )
    conn.commit()
    conn.close()

def test_late_fee_exactly_seven_days_overdue(test_setup):
    """
    Boundary: exactly 7 days overdue → 7 x $0.50 = $3.50
    """
    add_row_to_borrowed_books(
        patron_id="311111",
        book_id=1,
        borrow_date=datetime.today() - timedelta(days=21),
        due_date=datetime.today() - timedelta(days=7),
    )
    res = calculate_late_fee_for_book("311111", 1)
    assert res["fee_amount"] == 3.50
    assert res["days_overdue"] == 7

def test_late_fee_due_today_is_zero(test_setup):
    """
    Due today (0 days overdue) → 0.00
    """
    add_row_to_borrowed_books(
        patron_id="311112",
        book_id=1,
        borrow_date=datetime.today() - timedelta(days=14),
        due_date=datetime.today(),
    )
    res = calculate_late_fee_for_book("311112", 1)
    assert res["fee_amount"] == 0.00
    assert res["days_overdue"] == 0

def test_late_fee_future_due_is_zero(test_setup):
    """
    Not yet due (negative 'overdue') → treated as 0.00
    """
    add_row_to_borrowed_books(
        patron_id="311113",
        book_id=1,
        borrow_date=datetime.today() - timedelta(days=10),
        due_date=datetime.today() + timedelta(days=4),
    )
    res = calculate_late_fee_for_book("311113", 1)
    assert res["fee_amount"] == 0.00
    assert res["days_overdue"] == 0

def test_late_fee_large_overdue_capped_at_15(test_setup):
    """
    60 days overdue should cap at $15.00
    """
    add_row_to_borrowed_books(
        patron_id="311114",
        book_id=1,
        borrow_date=datetime.today() - timedelta(days=74),
        due_date=datetime.today() - timedelta(days=60),
    )
    res = calculate_late_fee_for_book("311114", 1)
    assert res["fee_amount"] == 15.00
    assert res["days_overdue"] == 60