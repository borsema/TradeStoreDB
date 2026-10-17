"""Unit tests for the Trade model."""
import pytest
from datetime import date, timedelta
from app.models.trade import Trade


class TestTradeModel:
    """Tests for Trade model structure and serialisation."""

    def test_trade_creation_defaults(self, db):
        """Trade should default created_date to today and expired to 'N'."""
        future = date.today() + timedelta(days=30)
        trade = Trade(
            trade_id="T99",
            version=1,
            counter_party_id="CP-X",
            portfolio_id="B9",
            maturity_date=future,
        )
        db.session.add(trade)
        db.session.commit()

        fetched = Trade.query.filter_by(trade_id="T99").first()
        assert fetched is not None
        assert fetched.expired == "N"
        assert fetched.created_date == date.today()

    def test_trade_to_dict_keys(self, db):
        """to_dict should expose all expected keys."""
        future = date.today() + timedelta(days=60)
        trade = Trade(
            trade_id="T_DICT",
            version=1,
            counter_party_id="CP-1",
            portfolio_id="B1",
            maturity_date=future,
        )
        db.session.add(trade)
        db.session.commit()

        d = trade.to_dict()
        expected_keys = {
            "id", "trade_id", "version", "counter_party_id",
            "portfolio_id", "maturity_date", "created_date", "expired",
        }
        assert expected_keys == set(d.keys())

    def test_trade_to_dict_date_format(self, db):
        """Dates in to_dict should use DD/MM/YYYY format."""
        maturity = date(2026, 12, 31)
        trade = Trade(
            trade_id="T_DATE",
            version=1,
            counter_party_id="CP-2",
            portfolio_id="B2",
            maturity_date=maturity,
        )
        db.session.add(trade)
        db.session.commit()

        d = trade.to_dict()
        assert d["maturity_date"] == "31/12/2026"

    def test_trade_repr(self, db):
        """__repr__ should include trade_id, version, expired."""
        trade = Trade(
            trade_id="T_REPR",
            version=5,
            counter_party_id="CP-5",
            portfolio_id="B3",
            maturity_date=date.today() + timedelta(days=10),
            expired="Y",
        )
        db.session.add(trade)
        db.session.commit()

        r = repr(trade)
        assert "T_REPR" in r
        assert "5" in r
        assert "Y" in r

    def test_unique_constraint_on_trade_id(self, db):
        """Inserting two trades with the same trade_id should raise IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        future = date.today() + timedelta(days=30)
        t1 = Trade(
            trade_id="T_DUP", version=1,
            counter_party_id="CP-1", portfolio_id="B1", maturity_date=future,
        )
        t2 = Trade(
            trade_id="T_DUP", version=2,
            counter_party_id="CP-2", portfolio_id="B2", maturity_date=future,
        )
        db.session.add(t1)
        db.session.commit()
        db.session.add(t2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
