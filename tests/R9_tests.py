import pytest
from unittest.mock import Mock

import services.library_service as library_service
from services.payment_service import PaymentGateway

# -------------------------------------------------------------------
# refund_late_fee_payment tests
# -------------------------------------------------------------------

def test_refund_late_fee_payment_successful_refund():
    """Happy path: valid transaction and amount, gateway approves."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund processed")

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_123",
        amount=10.0,
        payment_gateway=mock_gateway,
    )

    assert success is True
    assert message == "Refund processed"

    mock_gateway.refund_payment.assert_called_once_with("txn_123", 10.0)


def test_refund_late_fee_payment_invalid_transaction_id_rejected():
    """Invalid transaction_id format -> immediate rejection, gateway not called."""
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = library_service.refund_late_fee_payment(
        transaction_id="bad_txn",
        amount=10.0,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Invalid transaction ID."
    mock_gateway.refund_payment.assert_not_called()


@pytest.mark.parametrize("amount", [-1.0, 0.0])
def test_refund_late_fee_payment_invalid_refund_amounts_non_positive(amount):
    """Amount <= 0 -> rejected, gateway not called."""
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_123",
        amount=amount,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Refund amount must be greater than 0."
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_amount_exceeds_maximum():
    """Amount > 15.00 -> exceeds maximum late fee."""
    mock_gateway = Mock(spec=PaymentGateway)

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_123",
        amount=20.0,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Refund amount exceeds maximum late fee."
    mock_gateway.refund_payment.assert_not_called()


def test_refund_late_fee_payment_declined_by_gateway():
    """Branch: gateway called but returns success=False."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (False, "Declined by bank")

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_123",
        amount=5.0,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Refund failed: Declined by bank"
    mock_gateway.refund_payment.assert_called_once_with("txn_123", 5.0)


def test_refund_late_fee_payment_gateway_exception_handling():
    """Gateway raises exception -> caught and returned as error."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.side_effect = Exception("Gateway offline")

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_123",
        amount=5.0,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Refund processing error: Gateway offline"
    mock_gateway.refund_payment.assert_called_once_with("txn_123", 5.0)


def test_refund_late_fee_payment_uses_default_gateway_when_not_injected(mocker):
    """Covers branch where payment_gateway is None in refund function."""
    gateway_instance = Mock(spec=PaymentGateway)
    gateway_instance.refund_payment.return_value = (True, "OK")

    mocker.patch("services.library_service.PaymentGateway", return_value=gateway_instance)

    success, message = library_service.refund_late_fee_payment(
        transaction_id="txn_999",
        amount=8.0,
        payment_gateway=None,
    )

    assert success is True
    assert message == "OK"
    gateway_instance.refund_payment.assert_called_once_with("txn_999", 8.0)