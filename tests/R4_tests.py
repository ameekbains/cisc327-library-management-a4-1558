from database import get_db_connection
import pytest
from services.library_service import (
    return_book_by_patron,
    borrow_book_by_patron,
    add_book_to_catalog,
    calculate_late_fee_for_book,
)
from conftest import test_setup
from datetime import timedelta, datetime

# --- Helpers ---
def get_book_id_by_isbn(isbn: str) -> int:
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM books WHERE isbn = ?", (isbn,)).fetchone()
    conn.close()
    return row["id"]

def get_book_counts(book_id: int) -> tuple[int, int]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT available_copies, total_copies FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    conn.close()
    return row["available_copies"], row["total_copies"]

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

# --- Tests ---
def test_return_book_rejects_invalid_patron_format(test_setup):
    """
    Patron ID must be exactly 6 digits — invalid format should fail gracefully.
    """
    success, _ = return_book_by_patron("12345", 1)  # 5 digits
    assert success is False

def test_return_book_wrong_patron_cannot_return_another_users_loan(test_setup):
    """
    A different patron from the borrower cannot return the book.
    """
    add_book_to_catalog("R4 Wrong Patron", "Case Test", "9999999999991", 1)
    book_id = get_book_id_by_isbn("9999999999991")

    assert borrow_book_by_patron("200001", book_id)[0] is True  # correct borrower
    # Wrong patron tries to return
    success_wrong, _ = return_book_by_patron("200002", book_id)
    assert success_wrong is False

    # Correct patron returns successfully
    success_right, _ = return_book_by_patron("200001", book_id)
    assert success_right is True

def test_return_book_idempotent_and_copies_never_exceed_total(test_setup):
    """
    Returning the same loan twice should fail the second time and never push available copies > total.
    """
    add_book_to_catalog("R4 Idempotent", "Case Test", "9999999999992", 1)
    book_id = get_book_id_by_isbn("9999999999992")

    assert borrow_book_by_patron("200010", book_id)[0] is True
    success_first, _ = return_book_by_patron("200010", book_id)
    assert success_first is True

    # Second return attempt should fail
    success_second, _ = return_book_by_patron("200010", book_id)
    assert success_second is False

    available, total = get_book_counts(book_id)
    assert available == total == 1

def test_return_book_exactly_seven_days_overdue_message_and_fee(test_setup):
    """
    Overdue by exactly 7 days → $3.50 fee and message includes '7 days' and '$3.50'.
    """
    add_book_to_catalog("R4 Seven Over", "Late Boundary", "9999999999993", 3)
    book_id = get_book_id_by_isbn("9999999999993")

    # Simulate active overdue loan (due 7 days ago)
    add_row_to_borrowed_books(
        patron_id="200020",
        book_id=book_id,
        borrow_date=datetime.today() - timedelta(days=21),
        due_date=datetime.today() - timedelta(days=7),
        return_date=None,
    )

    fee_info = calculate_late_fee_for_book("200020", book_id)
    assert fee_info["fee_amount"] == 3.50
    assert fee_info["days_overdue"] == 7

    success, message = return_book_by_patron("200020", book_id)
    assert success is True
    assert "7 days" in message
    assert "$3.50" in message

def test_return_book_max_fee_cap_in_message(test_setup):
    """
    Very late return should cap at $15.00 and reflect that in the return message.
    """
    add_book_to_catalog("R4 Max Cap", "Late Boundary", "9999999999994", 2)
    book_id = get_book_id_by_isbn("9999999999994")

    # 40 days overdue -> well beyond cap
    add_row_to_borrowed_books(
        patron_id="200021",
        book_id=book_id,
        borrow_date=datetime.today() - timedelta(days=68),
        due_date=datetime.today() - timedelta(days=40),
        return_date=None,
    )

    fee_info = calculate_late_fee_for_book("200021", book_id)
    assert fee_info["fee_amount"] == 15.00
    assert fee_info["days_overdue"] == 40

    ok, msg = return_book_by_patron("200021", book_id)
    assert ok is True
    assert "$15.00" in msg
