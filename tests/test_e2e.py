# tests/test_e2e.py

import os
import re
import uuid

import pytest
from playwright.sync_api import Page, expect

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Base URL where your Flask app is running.
# Override with APP_BASE_URL env var if needed, e.g. http://localhost:8000
BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")

ADD_BOOK_URL = f"{BASE_URL}/add_book"
CATALOG_URL = f"{BASE_URL}/catalog"

# Pattern for a successful borrow flash message.
# R3 says it should "display appropriate success/error messages"
# so we match generic "borrowed"/"success".
BORROW_SUCCESS_PATTERN = re.compile(r"borrowed|success", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_unique_book_data():
    """
    Generate a unique, valid book for R1:

    - Title: required, <= 200 chars
    - Author: required, <= 100 chars
    - ISBN: required, exactly 13 digits (numeric)
    - Total copies: required, positive integer
    """
    suffix = uuid.uuid4().hex[:6]

    # Build a 13-digit numeric ISBN: "978" + 10-digit zero-padded suffix
    # (total = 13 digits, satisfies R1 ISBN rule)
    isbn_suffix_int = uuid.uuid4().int % 10**10
    isbn_13_digits = "978" + f"{isbn_suffix_int:010d}"

    return {
        "title": f"Test Book {suffix}",        # short, < 200 chars
        "author": f"Test Author {suffix}",     # short, < 100 chars
        "isbn": isbn_13_digits,                # exactly 13 digits
        "total_copies": "3",                   # positive integer
    }


def add_book_through_ui(page: Page, book: dict):
    """
    Fill and submit the /add_book form using the real browser.

    Matches catalog_bp.add_book route, which expects via POST:
        title, author, isbn, total_copies

    Assumes input fields like:
        <input name="title">
        <input name="author">
        <input name="isbn">
        <input name="total_copies">
    """
    page.goto(ADD_BOOK_URL)

    # Fill form with valid values per R1
    page.locator('input[name="title"]').fill(book["title"])
    page.locator('input[name="author"]').fill(book["author"])
    page.locator('input[name="isbn"]').fill(book["isbn"])
    page.locator('input[name="total_copies"]').fill(book["total_copies"])

    # Submit the form (assumes one submit button)
    with page.expect_navigation(url=re.compile(r".*/catalog$")):
        page.locator('button[type="submit"]').click()


def assert_book_visible_in_catalog(page: Page, book: dict):
    """
    Assert that the given book appears in the catalog table.

    Matches catalog_bp.catalog -> /catalog, which should list:
      - Book ID, Title, Author, ISBN
      - Available copies / Total copies
      - Actions (Borrow button)
    """
    page.goto(CATALOG_URL)
    expect(page).to_have_url(re.compile(r".*/catalog$"))

    # Try to find a row matching the title (table format per R2)
    row = page.get_by_role("row", name=re.compile(re.escape(book["title"])))
    if not row.count():
        # Fallback: just assert the title text exists on the page
        title_locator = page.get_by_text(book["title"])
        expect(title_locator).to_be_visible()
    else:
        row = row.first
        expect(row).to_contain_text(book["title"])
        expect(row).to_contain_text(book["author"])
        expect(row).to_contain_text(book["isbn"])


def borrow_book_from_catalog(page: Page, book: dict, patron_id: str):
    """
    Borrow the given book from the catalog page.

    Matches borrowing_bp.borrow_book, which expects form parameters:
        patron_id (R3: 6-digit format)
        book_id

    Assumptions about the catalog template:
      - Each book is rendered in a 'row' (e.g. <tr>).
      - That row contains the title text.
      - In that row, there is:
          <input name="patron_id">   (text field)
          <input type="hidden" name="book_id" ...>
          A "Borrow" button/link that submits to /borrow.
    """
    page.goto(CATALOG_URL)
    expect(page).to_have_url(re.compile(r".*/catalog$"))

    # Locate the row for our book by its title
    row = page.get_by_role("row", name=re.compile(re.escape(book["title"])))
    if not row.count():
        # Fallback: find the title and go up to its <tr>
        title_locator = page.get_by_text(book["title"])
        expect(title_locator).to_be_visible()
        row = title_locator.locator("xpath=ancestor::tr[1]")

    row = row.first

    # Fill patron_id (must be 6-digit numeric per R3)
    row.locator('input[name="patron_id"]').fill(patron_id)

    # Click the "Borrow" button in that row
    with page.expect_navigation(url=re.compile(r".*/catalog$")):
        row.get_by_text(re.compile(r"Borrow", re.IGNORECASE)).click()


def assert_borrow_confirmation_visible(page: Page):
    """
    Verify a borrow confirmation message is shown.

    borrowing_bp.borrow_book flashes message and redirects back to /catalog.
    We assert a generic success/borrow text (R3: "displays appropriate
    success/error messages").
    """
    confirmation = page.get_by_text(BORROW_SUCCESS_PATTERN)
    expect(confirmation).to_be_visible()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_add_new_book_appears_in_catalog(page: Page):
    """
    Flow 1 (R1 + R2):
      - Navigate to /add_book.
      - Fill Title, Author, ISBN (13 digits), Total copies (positive int).
      - Submit the form.
      - Verify the new book appears in the catalog table.
    """
    book = make_unique_book_data()

    add_book_through_ui(page, book)
    assert_book_visible_in_catalog(page, book)


@pytest.mark.e2e
def test_borrow_book_flow_shows_confirmation_message(page: Page):
    """
    Flow 2 (R1 + R2 + R3):
      - Add a valid new book to the catalog via the UI.
      - Navigate to /catalog.
      - In that row, enter a valid patron ID (6-digit format) and click Borrow.
      - Verify a borrow confirmation message appears.

    This exercises:
      - Add Book web interface (R1)
      - Catalog display (R2)
      - Borrowing interface (R3)
    """
    book = make_unique_book_data()

    # R3: Patron ID must be a 6-digit format (numeric string like "123456")
    patron_id = "123456"

    # Ensure there is a book to borrow
    add_book_through_ui(page, book)
    assert_book_visible_in_catalog(page, book)

    # Borrow that book using a valid patron ID
    borrow_book_from_catalog(page, book, patron_id)

    # Assert we see a confirmation/success message
    assert_borrow_confirmation_visible(page)
