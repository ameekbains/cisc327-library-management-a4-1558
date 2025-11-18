import pytest
from unittest.mock import patch

from services.payment_service import PaymentGateway


# --- Common fixture to disable real sleeping in all tests --------------------


@pytest.fixture(autouse=True)
def no_sleep():
    """
    Patch time.sleep in the payment_services module for ALL tests,
    so tests run instantly instead of waiting 0.5s/0.3s.
    """
    with patch("services.payment_service.time.sleep", return_value=None):
        yield


# --- Tests for process_payment ----------------------------------------------


@patch("services.payment_service.time.time", return_value=1700000000)
def test_process_payment_success(mock_time):
    gateway = PaymentGateway()

    success, txn_id, msg = gateway.process_payment(
        patron_id="123456",
        amount=10.50,
        description="Late fees",
    )

    assert success is True
    assert txn_id == "txn_123456_1700000000"
    assert msg == "Payment of $10.50 processed successfully"


@pytest.mark.parametrize(
    "amount, expected_msg",
    [
        (0, "Invalid amount: must be greater than 0"),
        (-5, "Invalid amount: must be greater than 0"),
    ],
)
def test_process_payment_invalid_amount(amount, expected_msg):
    gateway = PaymentGateway()

    success, txn_id, msg = gateway.process_payment(
        patron_id="123456",
        amount=amount,
        description="Late fees",
    )

    assert success is False
    assert txn_id == ""
    assert msg == expected_msg


def test_process_payment_amount_exceeds_limit():
    gateway = PaymentGateway()

    success, txn_id, msg = gateway.process_payment(
        patron_id="123456",
        amount=1000.01,
        description="Huge charge",
    )

    assert success is False
    assert txn_id == ""
    assert msg == "Payment declined: amount exceeds limit"


def test_process_payment_invalid_patron_id():
    gateway = PaymentGateway()

    success, txn_id, msg = gateway.process_payment(
        patron_id="12345",  # only 5 digits instead of 6
        amount=10,
        description="Late fees",
    )

    assert success is False
    assert txn_id == ""
    assert msg == "Invalid patron ID format"

@pytest.mark.parametrize("transaction_id", ["", "123", "tx_abc"])
def test_refund_payment_invalid_transaction_id(transaction_id):
    gateway = PaymentGateway()

    success, msg = gateway.refund_payment(
        transaction_id=transaction_id,
        amount=5,
    )

    assert success is False
    assert msg == "Invalid transaction ID"


@pytest.mark.parametrize("amount", [0, -1])
def test_refund_payment_invalid_amount(amount):
    gateway = PaymentGateway()

    success, msg = gateway.refund_payment(
        transaction_id="txn_123456_1700000000",
        amount=amount,
    )

    assert success is False
    assert msg == "Invalid refund amount"


# --- Tests for verify_payment_status ----------------------------------------


def test_verify_payment_status_not_found():
    gateway = PaymentGateway()

    result = gateway.verify_payment_status("bad_id")

    assert result == {
        "status": "not_found",
        "message": "Transaction not found",
    }


def test_verify_payment_status_completed_with_mocker(mocker):
    """
    Example using pytest-mock's `mocker` fixture instead of unittest.mock.patch.
    """
    gateway = PaymentGateway()

    # Patch time.time in the payment_services module
    mocker.patch("services.payment_service.time.time", return_value=1700000000)

    transaction_id = "txn_123456_1699999999"

    result = gateway.verify_payment_status(transaction_id)

    assert result["transaction_id"] == transaction_id
    assert result["status"] == "completed"
    assert result["amount"] == 10.50
    assert result["timestamp"] == 1700000000


# --- Example of mocking the gateway itself with mocker ----------------------


def test_process_payment_mocked_gateway_method(mocker):
    """
    This shows how you would mock PaymentGateway.process_payment itself, the way
    you would in tests for OTHER modules that depend on PaymentGateway.

    Here we patch the method so it doesn't run the real logic at all.
    """
    mocker.patch(
        "services.payment_service.PaymentGateway.process_payment",
        return_value=(True, "txn_fake_1", "OK"),
    )

    gateway = PaymentGateway(api_key="real_key")

    success, txn_id, msg = gateway.process_payment(
        patron_id="000001",
        amount=999.99,
        description="Does not matter; method is mocked",
    )

    assert success is True
    assert txn_id == "txn_fake_1"
    assert msg == "OK"
