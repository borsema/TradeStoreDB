"""Unit tests for Trade Store domain exceptions."""
import pytest
from app.exceptions import (
    TradeStoreError,
    LowerVersionError,
    MaturityDateInPastError,
    TradeNotFoundError,
)


class TestExceptions:
    """Verify exception hierarchy, status codes, and messages."""

    def test_lower_version_error_is_trade_store_error(self):
        exc = LowerVersionError("T1", 1, 5)
        assert isinstance(exc, TradeStoreError)

    def test_lower_version_error_status_code(self):
        exc = LowerVersionError("T1", 1, 5)
        assert exc.status_code == 400

    def test_lower_version_error_message(self):
        exc = LowerVersionError("T1", 1, 5)
        assert "T1" in exc.message
        assert "1" in exc.message
        assert "5" in exc.message

    def test_lower_version_error_attributes(self):
        exc = LowerVersionError("T2", 3, 7)
        assert exc.trade_id == "T2"
        assert exc.incoming_version == 3
        assert exc.stored_version == 7

    def test_maturity_date_error_is_trade_store_error(self):
        exc = MaturityDateInPastError("T3", "01/01/2020")
        assert isinstance(exc, TradeStoreError)

    def test_maturity_date_error_status_code(self):
        exc = MaturityDateInPastError("T3", "01/01/2020")
        assert exc.status_code == 400

    def test_maturity_date_error_message(self):
        exc = MaturityDateInPastError("T3", "01/01/2020")
        assert "T3" in exc.message
        assert "01/01/2020" in exc.message

    def test_trade_not_found_error_is_trade_store_error(self):
        exc = TradeNotFoundError("T_MISSING")
        assert isinstance(exc, TradeStoreError)

    def test_trade_not_found_error_status_code(self):
        exc = TradeNotFoundError("T_MISSING")
        assert exc.status_code == 404

    def test_trade_not_found_error_message(self):
        exc = TradeNotFoundError("T_MISSING")
        assert "T_MISSING" in exc.message

    def test_exceptions_are_catchable_as_base(self):
        """All exceptions should be catchable as TradeStoreError."""
        for exc_cls, args in [
            (LowerVersionError, ("T", 1, 2)),
            (MaturityDateInPastError, ("T", "01/01/2000")),
            (TradeNotFoundError, ("T",)),
        ]:
            exc = exc_cls(*args)
            with pytest.raises(TradeStoreError):
                raise exc
