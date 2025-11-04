'''
Test cases for, 
R1: Add Book To Catalog
The system shall provide a web interface to add new books to the catalog via a form with the following fields:
- Title (required, max 200 characters)
- Author (required, max 100 characters)
- ISBN (required, exactly 13 digits)
- Total copies (required, positive integer)
- The system shall display success/error messages and redirect to the catalog view after successful addition.
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
    add_book_to_catalog,)

#provided default test case
def test_add_book_invalid_isbn_too_short():
    """Test adding a book with ISBN too short."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    
    assert success == False
    assert "13 digits" in message

#Added test cases
def test_add_book_missing_title():
    """Test adding a book with missing/empty title."""
    success, message = add_book_to_catalog(
        "", "Author", "1234567890123", 5
    )
    assert success is False
    assert "title is required" in message.lower()

def test_add_book_invalid_total_copies():
    """Test adding a book with non-positive total copies."""
    success, message = add_book_to_catalog(
        "Book", "Author", "1234567890123", -1
    )
    assert success is False
    assert "positive integer" in message.lower()

def test_add_book_author_too_long():
    """Test adding a book with author name exceeding 100 characters."""

    long_author = "A" * 101
    success, message = add_book_to_catalog("Book", long_author, "1234567890123", 5)

    assert success is False
    assert "author must be less than 100" in message.lower()

def test_add_book_duplicate_isbn(monkeypatch):
    """Test adding a book with an ISBN that already exists."""

    monkeypatch.setattr("services.library_service.get_book_by_isbn", lambda isbn: {"isbn": isbn})

    success, message = add_book_to_catalog("Book", "Author", "1234567890123", 5)

    assert success is False
    assert "already exists" in message.lower()