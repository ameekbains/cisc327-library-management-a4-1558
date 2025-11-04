import pytest
from unittest.mock import Mock

import services.library_service as library_service
from services.payment_service import PaymentGateway


# -------------------------------------------------------------------
# pay_late_fees tests
# -------------------------------------------------------------------

def test_pay_late_fees_successful_payment(mocker):
    """Happy path: valid patron, fee > 0, book found, payment approved."""
    # Stub logic/database-related functions
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.00},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 1, "title": "Test Book"},
    )

    # Mock payment gateway (with verification)
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (True, "txn_123", "Approved")

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="123456",
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is True
    assert "Payment successful" in message
    assert "Approved" in message
    assert transaction_id == "txn_123"

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=5.00,
        description="Late fees for 'Test Book'",
    )


def test_pay_late_fees_payment_declined_by_gateway(mocker):
    """Gateway returns success=False -> payment failed."""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 7.50},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 2, "title": "Declined Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (
        False,
        "txn_456",
        "Declined by bank",
    )

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="654321",
        book_id=2,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Payment failed: Declined by bank"
    assert transaction_id is None

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="654321",
        amount=7.50,
        description="Late fees for 'Declined Book'",
    )


def test_pay_late_fees_invalid_patron_id_gateway_not_called():
    """Invalid patron ID: returns immediately, gateway must NOT be called."""
    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="12345",  # not 6 digits
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Invalid patron ID. Must be exactly 6 digits."
    assert transaction_id is None

    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_zero_late_fees_gateway_not_called(mocker):
    """Fee calculated but is 0 -> no payment should be attempted."""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0.0},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 1, "title": "Any Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="123456",
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "No late fees to pay for this book."
    assert transaction_id is None

    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error_exception_handling(mocker):
    """process_payment raises exception -> handled and returned as error message."""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 3.25},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 3, "title": "Network Error Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network down")

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="999999",
        book_id=3,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Payment processing error: Network down"
    assert transaction_id is None

    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_unable_to_calculate_fee(mocker):
    """Branch: fee_info missing fee_amount key -> 'Unable to calculate late fees.'"""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"days_overdue": 3},  # no 'fee_amount' key
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 1, "title": "Any Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="123456",
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Unable to calculate late fees."
    assert transaction_id is None

    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_book_not_found(mocker):
    """Branch: book lookup returns None -> Book not found, gateway not called."""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 4.0},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value=None,
    )

    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="123456",
        book_id=999,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Book not found."
    assert transaction_id is None

    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_uses_default_payment_gateway_when_not_injected(mocker):
    """Covers the branch where payment_gateway parameter is None."""
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 6.0},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"id": 4, "title": "Default Gateway Book"},
    )

    # Patch the PaymentGateway class that pay_late_fees uses
    gateway_instance = Mock(spec=PaymentGateway)
    gateway_instance.process_payment.return_value = (
        True,
        "txn_789",
        "OK",
    )
    mocker.patch("services.library_service.PaymentGateway", return_value=gateway_instance)

    success, message, transaction_id = library_service.pay_late_fees(
        patron_id="123456",
        book_id=4,
        payment_gateway=None,  # rely on default
    )

    assert success is True
    assert "Payment successful" in message
    assert transaction_id == "txn_789"

    gateway_instance.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=6.0,
        description="Late fees for 'Default Gateway Book'",
    )