"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_all_patron_record, get_book_by_id, get_book_by_isbn, get_patron_borrow_count, get_patron_borrowed_books,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books
)
from services.payment_service import PaymentGateway

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed > 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    Implements R4 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
    
    Returns:
        tuple: (success: bool, message: str)
    """

    patron_current_books = get_patron_borrowed_books(patron_id)

    borrowed_book = [record for record in patron_current_books if record["book_id"] == book_id]
    if not borrowed_book:
        return False, "You have not currently borrowed this book."
    
    # Update available copies
    availability_success = update_book_availability(book_id, +1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    # Calculates any late fees owed
    calculate_fee = calculate_late_fee_for_book(patron_id, book_id)
    late_fees = calculate_fee["fee_amount"]
    days_late = calculate_fee["days_overdue"]

    # Update return date
    return_date = datetime.now()
    
    # Record return date
    update_return_date = update_borrow_record_return_date(patron_id, book_id, return_date)
    if not update_return_date:
        return False, "Database error occurred while updating book return date."

    if late_fees == 0.00:
        return True, f'You have successfully returned your book. There are no late fees on this book. Thank you!'
    
    return True, f'You have successfully returned your book. This book is {days_late} days late and you owe ${calculate_fee["fee_amount"]:.2f} in late fees for this book.'


def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fees for a specific book.
    Implements R5 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
    
    Returns:
        dict: {"fee_amount": float, "days_overdue": int}
    """

    patron_current_books = get_patron_borrowed_books(patron_id)

    borrowed_book = [record for record in patron_current_books if record["book_id"] == book_id]

    # Check if no borrowed books
    if not borrowed_book:
        return {"fee_amount": 0.00, "days_overdue": 0}

    for book in borrowed_book:
        overdue_status = book["is_overdue"]

    # Check if book is overdue
    if not overdue_status:
        return {"fee_amount": 0.00, "days_overdue": 0}
    
    today = datetime.now()
    for book in borrowed_book:
        borrow_due_date = book["due_date"]

    # Get number of days overdue
    time_diff = today - borrow_due_date
    num_days_overdue = time_diff.days

    overdue_amt = 0.00

    # $0.50/day for first 7 days overdue
    if num_days_overdue <= 7:
        overdue_amt = num_days_overdue * 0.50
        return {"fee_amount": overdue_amt, "days_overdue": num_days_overdue}
    
    # $1.00/day for each additional day after 7 days
    elif (num_days_overdue > 7):
        overdue_amt = (7 * 0.50) + ((num_days_overdue - 7) * 1.00)

        if overdue_amt < 15.00:
            return {"fee_amount": overdue_amt, "days_overdue": num_days_overdue}
        
        # Maximum $15.00 late fee
        else:
            return {"fee_amount": 15.00, "days_overdue": num_days_overdue}


def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    Implements R6 as per requirements  
    
    Args:
        search_term: Entered search value
        search_type: title, author, or isbn
    
    Returns:
        List[Dict]: [{"id": int, "title": str, "author": str, "isbn": str, "total_copies": int, "available_copies": int}]
    """
    
    all_books = get_all_books()

    search_results = []

    for b in all_books:

        # Support exact matching for isbn
        if search_type == "isbn":
            if "isbn" in b and b["isbn"] == search_term:
                search_results.append(b)
        
        # Support partial matching for title (case-insensitive)
        elif search_type == "title":
            if "title" in b and search_term.lower() in b["title"].lower():
                search_results.append(b)

        # Support partial matching for author (case-insensitive)
        elif search_type == "author":
            if "author" in b and search_term.lower() in b["author"].lower():
                search_results.append(b)

    return search_results


def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    Implements R7 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
    
    Returns:
        Dict: {
            "curr_borrowed_books": List[Dict]: [{
                "book_id": int,
                "title": str,
                "borrow_date": datetime,
                "due_date": datetime
                }],

            "total_late_fees_owed": float, 
            
            "num_books_currently_borrowed": int, 
            
            "borrowing_history" List[Dict]: [{
                "book_id": int,
                "title": str,
                "return_date": datetime
                }]
            }
    """

    patron_current_books = get_patron_borrowed_books(patron_id)

    # Currently borrowed books with due dates
    currently_borrowed = []
    for books in patron_current_books:
        currently_borrowed.append({
            "book_id": books.get("book_id"),
            "title": books.get("title"),
            "borrow_date": books.get("borrow_date"),
            "due_date": books.get("due_date")
        })

    # Number of books currently borrowed
    num_currently_borrowed = len(currently_borrowed)

    # Total late fees owed
    book_fees = []
    for id in currently_borrowed:
        book_fees.append(calculate_late_fee_for_book(patron_id, id.get("book_id")))
    
    overdue_fees = []
    for fee_amt in book_fees:
        overdue_fees.append(float(fee_amt.get("fee_amount")))
    
    total_overdue = sum(overdue_fees)

    # Get patron's borrowing record (past and present)
    patron_all_books = get_all_patron_record(patron_id)

    # Borrowing history
    borrowing_history = []
    for item in patron_all_books:
        borrowing_history.append({
            "book_id": item.get("book_id"),
            "title":item.get("title"),
            "return_date": item.get("return_date")
        })

    # Round overdue amt to two decimal places
    total_overdue_rounded = round(total_overdue, 2)

    return {
        "curr_borrowed_books": currently_borrowed, 
        "total_late_fees_owed": total_overdue_rounded, 
        "num_books_currently_borrowed": num_currently_borrowed, 
        "borrowing_history": borrowing_history
    }

def pay_late_fees(patron_id: str, book_id: int, payment_gateway: PaymentGateway = None) -> Tuple[bool, str, Optional[str]]:
    """
    Process payment for late fees using external payment gateway.
    
    NEW FEATURE FOR ASSIGNMENT 3: Demonstrates need for mocking/stubbing
    This function depends on an external payment service that should be mocked in tests.
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book with late fees
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str, transaction_id: Optional[str])
        
    Example for you to mock:
        # In tests, mock the payment gateway:
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123", "Success")
        success, msg, txn = pay_late_fees("123456", 1, mock_gateway)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits.", None
    
    # Calculate late fee first
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    
    # Check if there's a fee to pay
    if not fee_info or 'fee_amount' not in fee_info:
        return False, "Unable to calculate late fees.", None
    
    fee_amount = fee_info.get('fee_amount', 0.0)
    
    if fee_amount <= 0:
        return False, "No late fees to pay for this book.", None
    
    # Get book details for payment description
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found.", None
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process payment through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN THEIR TESTS!
    try:
        success, transaction_id, message = payment_gateway.process_payment(
            patron_id=patron_id,
            amount=fee_amount,
            description=f"Late fees for '{book['title']}'"
        )
        
        if success:
            return True, f"Payment successful! {message}", transaction_id
        else:
            return False, f"Payment failed: {message}", None
            
    except Exception as e:
        # Handle payment gateway errors
        return False, f"Payment processing error: {str(e)}", None


def refund_late_fee_payment(transaction_id: str, amount: float, payment_gateway: PaymentGateway = None) -> Tuple[bool, str]:
    """
    Refund a late fee payment (e.g., if book was returned on time but fees were charged in error).
    
    NEW FEATURE FOR ASSIGNMENT 3: Another function requiring mocking
    
    Args:
        transaction_id: Original transaction ID to refund
        amount: Amount to refund
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate inputs
    if not transaction_id or not transaction_id.startswith("txn_"):
        return False, "Invalid transaction ID."
    
    if amount <= 0:
        return False, "Refund amount must be greater than 0."
    
    if amount > 15.00:  # Maximum late fee per book
        return False, "Refund amount exceeds maximum late fee."
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process refund through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN YOUR TESTS!
    try:
        success, message = payment_gateway.refund_payment(transaction_id, amount)
        
        if success:
            return True, message
        else:
            return False, f"Refund failed: {message}"
            
    except Exception as e:
        return False, f"Refund processing error: {str(e)}"