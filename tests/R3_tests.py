'''R3: Book Borrowing Interface
The system shall provide a borrowing interface to borrow books by patron ID:

- Accepts patron ID and book ID as the form parameters
- Validates patron ID (6-digit format)
- Checks book availability and patron borrowing limits (max 5 books)
- Creates borrowing record and updates available copies
- Displays appropriate success/error messages
'''

import sys
import os

# Add the parent directory of tests to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import re
import pytest
from app import create_app

from services.library_service import (
    borrow_book_by_patron,)


#tests for R3
def test_borrow_book_valid_input(monkeypatch):
    """Borrowing succeeds with valid patron ID and available copies."""

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 2)
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is True
    assert "successfully borrowed" in message.lower()


def test_borrow_book_invalid_patron_id():
    """Borrowing fails if patron ID is not 6 digits."""

    success, message = borrow_book_by_patron("12AB", 1)

    assert success is False
    assert "invalid patron id" in message.lower()


def test_borrow_book_not_found(monkeypatch):
    """Borrowing fails if book does not exist."""

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: None)

    success, message = borrow_book_by_patron("123456", 99)

    assert success is False
    assert "book not found" in message.lower()


def test_borrow_book_not_available(monkeypatch):
    """Borrowing fails if no available copies remain."""

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 0})

    success, message = borrow_book_by_patron("123456", 1)

    assert success is False
    assert "not available" in message.lower()


def test_borrow_book_patron_limit(monkeypatch):
    """Borrowing fails if patron already borrowed 5 books."""

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 6)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is False
    assert "maximum borrowing limit" in message.lower()