import pytest
from services.library_service import search_books_in_catalog, add_book_to_catalog
from database import get_db_connection
from conftest import test_setup

def get_isbns(curr):
    return {b["isbn"] for b in curr}

def test_search_invalid_type_returns_empty(test_setup):
    """
    Non-supported search type should return no results (graceful handling).
    """
    out = search_books_in_catalog("anything", "publisher")
    assert isinstance(out, list)
    assert len(out) == 0

def test_search_title_multiple_matches_case_insensitive(test_setup):
    """
    Add two books containing 'python' in the title and ensure both are returned via partial case-insensitive match.
    """
    add_book_to_catalog("Deep Learning with Python", "François Chollet", "0123456789012", 5)
    add_book_to_catalog("Pythonic Testing", "Jane Doe", "2222222222222", 3)

    res = search_books_in_catalog("PYTHON", "title")
    isbns = get_isbns(res)
    assert "0123456789012" in isbns
    assert "2222222222222" in isbns

def test_search_author_returns_multiple_partial_matches(test_setup):
    """
    Add two books by the same author and verify partial author query returns both.
    """
    add_book_to_catalog("Unit Testing in Practice", "Jane Doe", "3333333333333", 2)
    add_book_to_catalog("Clean Code Tips", "Jane Doe", "4444444444444", 2)

    res = search_books_in_catalog("jane do", "author")
    isbns = get_isbns(res)
    assert "3333333333333" in isbns
    assert "4444444444444" in isbns

def test_search_isbn_requires_exact_match_and_no_hyphens(test_setup):
    """
    ISBN search must be exact and should not match hyphenated input.
    """
    # Known seed likely has The Great Gatsby 9780743273565 — verify hyphenated does NOT match
    res_hyphen = search_books_in_catalog("978-0743273565", "isbn")
    assert len(res_hyphen) == 0

    # Exact match for a book we add right now
    add_book_to_catalog("Precise ISBN", "Exact Author", "5555555555555", 1)
    res_exact = search_books_in_catalog("5555555555555", "isbn")
    assert len(res_exact) == 1
    assert res_exact[0]["isbn"] == "5555555555555"

def test_search_isbn_partial_should_not_match(test_setup):
    """
    Partial ISBN strings must not return results.
    """
    add_book_to_catalog("Another Precise", "Exact Author", "6666666666666", 1)
    res = search_books_in_catalog("666666666666", "isbn")  # 12 digits only
    assert len(res) == 0
