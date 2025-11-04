from database import get_db_connection
import pytest
from services.library_service import get_patron_status_report
from datetime import datetime, timedelta
from conftest import test_setup

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

def test_patron_status_mixed_current_overdue_and_not_overdue(test_setup):
    """
    Mix of current overdue loans (one capped) and a not-overdue loan.
    Total late fees owed = 7 days * $0.50 + capped $15.00 = $18.50
    """
    patron = "411111"
    # Overdue by exactly 7 days → $3.50
    add_row_to_borrowed_books(
        patron_id=patron, book_id=1,
        borrow_date=datetime.today() - timedelta(days=21),
        due_date=datetime.today() - timedelta(days=7),
        return_date=None
    )
    # Overdue by 25 days → capped at $15.00
    add_row_to_borrowed_books(
        patron_id=patron, book_id=2,
        borrow_date=datetime.today() - timedelta(days=39),
        due_date=datetime.today() - timedelta(days=25),
        return_date=None
    )
    # Not overdue
    add_row_to_borrowed_books(
        patron_id=patron, book_id=3,
        borrow_date=datetime.today() - timedelta(days=4),
        due_date=datetime.today() + timedelta(days=10),
        return_date=None
    )

    result = get_patron_status_report(patron)
    assert result["num_books_currently_borrowed"] == 3
    assert round(result["total_late_fees_owed"], 2) == 18.50

def test_patron_status_only_returned_history_no_current_loans(test_setup):
    """
    Only returned items → current list empty, fees 0.00, history shows both entries.
    """
    patron = "411112"
    add_row_to_borrowed_books(
        patron_id=patron, book_id=1,
        borrow_date=datetime.today() - timedelta(days=30),
        due_date=datetime.today() - timedelta(days=16),
        return_date=datetime.today() - timedelta(days=10)
    )
    add_row_to_borrowed_books(
        patron_id=patron, book_id=2,
        borrow_date=datetime.today() - timedelta(days=20),
        due_date=datetime.today() - timedelta(days=6),
        return_date=datetime.today() - timedelta(days=2)
    )

    result = get_patron_status_report(patron)
    assert result["num_books_currently_borrowed"] == 0
    assert result["total_late_fees_owed"] == 0.00
    assert len(result["curr_borrowed_books"]) == 0
    assert len(result["borrowing_history"]) == 2

def test_patron_status_reports_due_dates_field_presence(test_setup):
    """
    Ensure due_date is included for current loans in the report payload.
    """
    patron = "411113"
    add_row_to_borrowed_books(
        patron_id=patron, book_id=1,
        borrow_date=datetime.today() - timedelta(days=5),
        due_date=datetime.today() + timedelta(days=9),
        return_date=None
    )
    result = get_patron_status_report(patron)
    assert result["num_books_currently_borrowed"] == 1
    assert "due_date" in result["curr_borrowed_books"][0]

def test_patron_status_unknown_patron_defaults(test_setup):
    """
    Unknown patron → empty current list, zero fees, zero count.
    """
    result = get_patron_status_report("000000")
    assert result["num_books_currently_borrowed"] == 0
    assert result["total_late_fees_owed"] == 0.00
    assert len(result["curr_borrowed_books"]) == 0
