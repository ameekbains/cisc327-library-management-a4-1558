'''
R2: Book Catalog Display
The system shall display all books in the catalog in a table format showing:
- Book ID, Title, Author, ISBN
- Available copies / Total copies
- Actions (Borrow button for available books)
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
    add_book_to_catalog,
    borrow_book_by_patron,
    calculate_late_fee_for_book,
    get_patron_status_report,
    return_book_by_patron,
    search_books_in_catalog
)

#tests for R2
@pytest.fixture
def client():
    app = create_app()  # Creates an instance of the app for testing R2
    app.config['TESTING'] = True  # Ensures testing mode is on
    with app.test_client() as client:  # Creates a test client
        yield client  # Used as test client
        
def _patch_get_all_books(monkeypatch, books):
    """
    Patch the function the /catalog route uses to fetch books.
    Tries routes.catalog_routes.get_all_books first; falls back to database.get_all_books.
    """
    try:
        import routes.catalog_routes as cr
        monkeypatch.setattr(cr, "get_all_books", lambda: books)
        return
    except Exception:
        pass
    import database as db
    monkeypatch.setattr(db, "get_all_books", lambda: books)

# We rely on the `client` fixture in tests/conftest.py
def test_catalog_table_and_cells(monkeypatch, client):
    """Headers match template; rows show all required fields."""
    books = [
        {"id": 10, "title": "Alpha Tales", "author": "Writer X",
         "isbn": "5555555555555", "available_copies": 3, "total_copies": 7},
        {"id": 11, "title": "Beta Notes", "author": "Writer Y",
         "isbn": "4444444444444", "available_copies": 0, "total_copies": 4},
    ]
    _patch_get_all_books(monkeypatch, books)

    resp = client.get("/catalog")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"

    html = resp.get_data(as_text=True)

    # Exact headers from your template
    for header in ("ID", "Title", "Author", "ISBN", "Availability", "Actions"):
        assert f"<th>{header}</th>" in html

    # Rows show fields
    for b in books:
        assert f">{b['id']}<" in html
        assert b["title"] in html
        assert b["author"] in html
        assert b["isbn"] in html

    # Availability formatting per template
    assert 'class="status-available"' in html and "3/7 Available" in html
    assert 'class="status-unavailable"' in html and "Not Available" in html

def test_borrow_form_shown_for_open_item(monkeypatch, client):
    """Available book shows the Borrow form with correct inputs/constraints."""
    books = [
        {"id": 99, "title": "Gamma Book", "author": "ZZ",
         "isbn": "3333333333333", "available_copies": 2, "total_copies": 5},
    ]
    _patch_get_all_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)

    # Borrow button text
    assert ">Borrow<" in html
    # Hidden book_id present with correct value
    assert 'type="hidden"' in html and 'name="book_id"' in html and 'value="99"' in html
    # Patron input constraints from template
    assert 'name="patron_id"' in html
    assert 'pattern="[0-9]{6}"' in html
    assert 'maxlength="6"' in html
    assert "required" in html
    # Form should be POST
    assert re.search(r'<form[^>]*method="POST"', html, flags=re.IGNORECASE)

def test_no_form_if_fully_unavailable(monkeypatch, client):
    """Unavailable book renders 'Not Available' and no Borrow form/button."""
    books = [
        {"id": 15, "title": "Delta Work", "author": "YY",
         "isbn": "2222222222222", "available_copies": 0, "total_copies": 6},
    ]
    _patch_get_all_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)
    assert "Not Available" in html
    # No borrow controls when unavailable
    assert "Borrow</button>" not in html
    assert "<form" not in html

def test_catalog_empty_message(monkeypatch, client):
    """Empty catalog shows the empty-state message and the Add New Book link."""
    _patch_get_all_books(monkeypatch, [])

    html = client.get("/catalog").get_data(as_text=True)
    assert "No books in catalog" in html
    assert "Add New Book" in html