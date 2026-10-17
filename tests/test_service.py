"""Unit tests for TradeService — covers all three business rules and edge cases."""
import pytest
from datetime import date, timedelta

from app.services.trade_service import TradeService
from app.exceptions import (
    LowerVersionError,
    MaturityDateInPastError,
    TradeNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future(days: int = 365) -> str:
    return (date.today() + timedelta(days=days)).strftime("%d/%m/%Y")


def _past(days: int = 365) -> str:
    return (date.today() - timedelta(days=days)).strftime("%d/%m/%Y")


def _base_payload(**overrides) -> dict:
    payload = {
        "trade_id": "T1",
        "version": 1,
        "counter_party_id": "CP-1",
        "portfolio_id": "B1",
        "maturity_date": _future(),
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# store_trade — happy path
# ---------------------------------------------------------------------------

class TestStoreTrade:
    """Tests for TradeService.store_trade."""

    def test_store_new_trade(self, db):
        """A brand-new trade_id should be inserted successfully."""
        svc = TradeService()
        trade = svc.store_trade(_base_payload())
        assert trade.trade_id == "T1"
        assert trade.version == 1
        assert trade.expired == "N"

    def test_store_trade_sets_created_date_today(self, db):
        """created_date defaults to today when not provided."""
        svc = TradeService()
        trade = svc.store_trade(_base_payload())
        assert trade.created_date == date.today()

    def test_store_trade_with_explicit_created_date(self, db):
        """created_date is honoured when supplied."""
        svc = TradeService()
        trade = svc.store_trade(_base_payload(created_date="01/01/2025"))
        assert trade.created_date == date(2025, 1, 1)

    def test_store_trade_returns_trade_instance(self, db):
        """store_trade should return a Trade ORM object."""
        from app.models.trade import Trade
        svc = TradeService()
        trade = svc.store_trade(_base_payload())
        assert isinstance(trade, Trade)

    # ------------------------------------------------------------------
    # Rule: same version replaces existing record
    # ------------------------------------------------------------------

    def test_same_version_replaces_record(self, db):
        """Incoming trade with same version should overwrite the existing record."""
        svc = TradeService()
        svc.store_trade(_base_payload(counter_party_id="CP-1"))

        updated = svc.store_trade(_base_payload(counter_party_id="CP-UPDATED", version=1))
        assert updated.counter_party_id == "CP-UPDATED"
        assert updated.version == 1

    def test_higher_version_replaces_record(self, db):
        """Incoming trade with higher version should overwrite the existing record."""
        svc = TradeService()
        svc.store_trade(_base_payload(version=1))
        updated = svc.store_trade(_base_payload(version=2, counter_party_id="CP-2"))
        assert updated.version == 2
        assert updated.counter_party_id == "CP-2"

    def test_upsert_does_not_create_duplicate(self, db):
        """After an upsert there must still be only one record per trade_id."""
        from app.models.trade import Trade
        svc = TradeService()
        svc.store_trade(_base_payload(version=1))
        svc.store_trade(_base_payload(version=2))

        count = Trade.query.filter_by(trade_id="T1").count()
        assert count == 1

    # ------------------------------------------------------------------
    # Rule 1 — reject lower version
    # ------------------------------------------------------------------

    def test_lower_version_raises_error(self, db):
        """Incoming trade with version < existing version must be rejected."""
        svc = TradeService()
        svc.store_trade(_base_payload(version=5))

        with pytest.raises(LowerVersionError) as exc_info:
            svc.store_trade(_base_payload(version=3))

        assert "T1" in str(exc_info.value)
        assert exc_info.value.incoming_version == 3
        assert exc_info.value.stored_version == 5

    def test_lower_version_does_not_modify_stored_trade(self, db):
        """Store should remain unchanged after a lower-version rejection."""
        svc = TradeService()
        svc.store_trade(_base_payload(version=5, counter_party_id="CP-ORIGINAL"))

        with pytest.raises(LowerVersionError):
            svc.store_trade(_base_payload(version=3, counter_party_id="CP-INTRUDER"))

        trade = svc.get_trade_by_id("T1")
        assert trade.version == 5
        assert trade.counter_party_id == "CP-ORIGINAL"

    # ------------------------------------------------------------------
    # Rule 2 — reject past maturity dates
    # ------------------------------------------------------------------

    def test_past_maturity_date_raises_error(self, db):
        """Trade with maturity_date < today must be rejected."""
        svc = TradeService()
        with pytest.raises(MaturityDateInPastError) as exc_info:
            svc.store_trade(_base_payload(maturity_date=_past()))

        assert "T1" in str(exc_info.value)

    def test_maturity_today_is_accepted(self, db):
        """Maturity date equal to today is NOT in the past (< today), so it is accepted."""
        svc = TradeService()
        today = date.today().strftime("%d/%m/%Y")
        # The rule is: reject if maturity_date < today. Today itself is allowed.
        trade = svc.store_trade(_base_payload(maturity_date=today))
        assert trade is not None

    def test_maturity_tomorrow_is_accepted(self, db):
        """Maturity date set to tomorrow must be accepted."""
        svc = TradeService()
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
        trade = svc.store_trade(_base_payload(maturity_date=tomorrow))
        assert trade is not None

    # ------------------------------------------------------------------
    # Rule 3 — auto-set expired flag
    # ------------------------------------------------------------------

    def test_future_maturity_sets_expired_n(self, db):
        """Trade with future maturity date should have expired='N'."""
        svc = TradeService()
        trade = svc.store_trade(_base_payload(maturity_date=_future()))
        assert trade.expired == "N"

    # ------------------------------------------------------------------
    # Validation — missing / bad fields
    # ------------------------------------------------------------------

    def test_missing_trade_id_raises_value_error(self, db):
        svc = TradeService()
        payload = _base_payload()
        del payload["trade_id"]
        with pytest.raises(ValueError, match="trade_id"):
            svc.store_trade(payload)

    def test_missing_version_raises_value_error(self, db):
        svc = TradeService()
        payload = _base_payload()
        del payload["version"]
        with pytest.raises(ValueError, match="version"):
            svc.store_trade(payload)

    def test_missing_maturity_date_raises_value_error(self, db):
        svc = TradeService()
        payload = _base_payload()
        del payload["maturity_date"]
        with pytest.raises(ValueError):
            svc.store_trade(payload)

    def test_invalid_date_format_raises_value_error(self, db):
        svc = TradeService()
        with pytest.raises(ValueError, match="not a recognised date format"):
            svc.store_trade(_base_payload(maturity_date="not-a-date"))

    def test_iso_date_format_accepted(self, db):
        """YYYY-MM-DD format should also be accepted."""
        svc = TradeService()
        future_iso = (date.today() + timedelta(days=200)).strftime("%Y-%m-%d")
        trade = svc.store_trade(_base_payload(maturity_date=future_iso))
        assert trade is not None

    # ------------------------------------------------------------------
    # Problem-statement sample data
    # ------------------------------------------------------------------

    def test_problem_statement_t1(self, db):
        """T1 v1 — valid, should be stored."""
        svc = TradeService()
        trade = svc.store_trade({
            "trade_id": "T1",
            "version": 1,
            "counter_party_id": "CP-1",
            "portfolio_id": "B1",
            "maturity_date": _future(200),
        })
        assert trade.trade_id == "T1"

    def test_problem_statement_t2(self, db):
        """T2 v2 — valid, should be stored."""
        svc = TradeService()
        trade = svc.store_trade({
            "trade_id": "T2",
            "version": 2,
            "counter_party_id": "CP-2",
            "portfolio_id": "B1",
            "maturity_date": _future(300),
        })
        assert trade.trade_id == "T2"

    def test_problem_statement_t3_past_maturity(self, db):
        """T3 v3 — maturity 20/05/2014 is in the past, must be rejected."""
        svc = TradeService()
        with pytest.raises(MaturityDateInPastError):
            svc.store_trade({
                "trade_id": "T3",
                "version": 3,
                "counter_party_id": "CP-3",
                "portfolio_id": "B2",
                "maturity_date": "20/05/2014",
            })

    def test_problem_statement_lower_version_t2(self, db):
        """T2 v1 arriving after T2 v2 must be rejected."""
        svc = TradeService()
        svc.store_trade({
            "trade_id": "T2",
            "version": 2,
            "counter_party_id": "CP-2",
            "portfolio_id": "B1",
            "maturity_date": _future(300),
        })
        with pytest.raises(LowerVersionError):
            svc.store_trade({
                "trade_id": "T2",
                "version": 1,
                "counter_party_id": "CP-1",
                "portfolio_id": "B1",
                "maturity_date": _future(300),
            })


# ---------------------------------------------------------------------------
# store_trades_bulk
# ---------------------------------------------------------------------------

class TestStoreTradeBulk:
    """Tests for TradeService.store_trades_bulk."""

    def test_bulk_all_valid(self, db):
        svc = TradeService()
        payloads = [
            _base_payload(trade_id="T10", version=1),
            _base_payload(trade_id="T11", version=1),
        ]
        result = svc.store_trades_bulk(payloads)
        assert len(result["stored"]) == 2
        assert len(result["errors"]) == 0

    def test_bulk_partial_failure(self, db):
        """Invalid trades are collected in errors; valid ones are persisted."""
        svc = TradeService()
        payloads = [
            _base_payload(trade_id="T20", version=1),
            _base_payload(trade_id="T21", version=1, maturity_date=_past()),  # invalid
        ]
        result = svc.store_trades_bulk(payloads)
        assert len(result["stored"]) == 1
        assert len(result["errors"]) == 1
        assert "T21" in result["errors"][0]

    def test_bulk_all_invalid(self, db):
        svc = TradeService()
        payloads = [
            _base_payload(trade_id="T30", version=1, maturity_date=_past()),
            _base_payload(trade_id="T31", version=1, maturity_date=_past()),
        ]
        result = svc.store_trades_bulk(payloads)
        assert len(result["stored"]) == 0
        assert len(result["errors"]) == 2

    def test_bulk_empty_list(self, db):
        svc = TradeService()
        result = svc.store_trades_bulk([])
        assert result == {"stored": [], "errors": []}


# ---------------------------------------------------------------------------
# get_all_trades
# ---------------------------------------------------------------------------

class TestGetAllTrades:
    """Tests for TradeService.get_all_trades."""

    def test_returns_all_stored_trades(self, db):
        svc = TradeService()
        svc.store_trade(_base_payload(trade_id="T40", version=1))
        svc.store_trade(_base_payload(trade_id="T41", version=1))
        trades = svc.get_all_trades()
        ids = [t.trade_id for t in trades]
        assert "T40" in ids
        assert "T41" in ids

    def test_returns_empty_list_when_no_trades(self, db):
        svc = TradeService()
        assert svc.get_all_trades() == []


# ---------------------------------------------------------------------------
# get_trade_by_id
# ---------------------------------------------------------------------------

class TestGetTradeById:
    """Tests for TradeService.get_trade_by_id."""

    def test_returns_correct_trade(self, db):
        svc = TradeService()
        svc.store_trade(_base_payload(trade_id="T50"))
        trade = svc.get_trade_by_id("T50")
        assert trade.trade_id == "T50"

    def test_raises_not_found_for_missing_id(self, db):
        svc = TradeService()
        with pytest.raises(TradeNotFoundError) as exc_info:
            svc.get_trade_by_id("NONEXISTENT")
        assert "NONEXISTENT" in str(exc_info.value)


# ---------------------------------------------------------------------------
# delete_trade
# ---------------------------------------------------------------------------

class TestDeleteTrade:
    """Tests for TradeService.delete_trade."""

    def test_delete_existing_trade(self, db):
        svc = TradeService()
        svc.store_trade(_base_payload(trade_id="T60"))
        svc.delete_trade("T60")
        with pytest.raises(TradeNotFoundError):
            svc.get_trade_by_id("T60")

    def test_delete_nonexistent_trade_raises(self, db):
        svc = TradeService()
        with pytest.raises(TradeNotFoundError):
            svc.delete_trade("GHOST")


# ---------------------------------------------------------------------------
# expire_matured_trades
# ---------------------------------------------------------------------------

class TestExpireMaturedTrades:
    """Tests for TradeService.expire_matured_trades (Rule 3)."""

    def test_expires_matured_trades(self, db):
        """Trades with maturity_date in the past should be marked expired='Y'."""
        from app.models.trade import Trade

        # Insert a trade that has already matured — bypass service validation
        # by inserting directly into the DB
        matured_trade = Trade(
            trade_id="T_MATURED",
            version=1,
            counter_party_id="CP-X",
            portfolio_id="B9",
            maturity_date=date(2020, 1, 1),  # clearly in the past
            expired="N",
        )
        db.session.add(matured_trade)
        db.session.commit()

        svc = TradeService()
        count = svc.expire_matured_trades()
        assert count >= 1

        refreshed = Trade.query.filter_by(trade_id="T_MATURED").first()
        assert refreshed.expired == "Y"

    def test_does_not_expire_future_trades(self, db):
        """Trades with maturity_date in the future should remain expired='N'."""
        svc = TradeService()
        svc.store_trade(_base_payload(trade_id="T_FUTURE", maturity_date=_future(500)))
        svc.expire_matured_trades()
        trade = svc.get_trade_by_id("T_FUTURE")
        assert trade.expired == "N"

    def test_already_expired_trades_not_counted_again(self, db):
        """Trades already marked expired='Y' should not be touched again."""
        from app.models.trade import Trade

        already_expired = Trade(
            trade_id="T_ALREADY_EXP",
            version=1,
            counter_party_id="CP-Z",
            portfolio_id="B0",
            maturity_date=date(2019, 1, 1),
            expired="Y",
        )
        db.session.add(already_expired)
        db.session.commit()

        svc = TradeService()
        count = svc.expire_matured_trades()
        # Should be 0 because the trade was already 'Y'
        assert count == 0

    def test_returns_zero_when_no_trades_to_expire(self, db):
        svc = TradeService()
        count = svc.expire_matured_trades()
        assert count == 0
