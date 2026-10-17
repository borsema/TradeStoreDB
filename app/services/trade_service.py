"""Trade Store service layer — all business logic lives here."""
from datetime import date
from typing import List, Optional

from ..extensions import db
from ..models.trade import Trade
from ..exceptions import (
    LowerVersionError,
    MaturityDateInPastError,
    TradeNotFoundError,
)


class TradeService:
    """Provides all CRUD and business-logic operations for the Trade Store.

    Business rules implemented:
    1. Reject trades whose maturity_date < today (MaturityDateInPastError).
    2. Reject trades whose version < existing version (LowerVersionError).
    3. Replace (upsert) a trade when the incoming version == existing version.
    4. Insert a new record when the trade_id is new.
    5. Auto-expire trades when their maturity_date has passed (nightly scan).
    """

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def store_trade(self, payload: dict) -> Trade:
        """Validate and persist a single trade.

        Args:
            payload: Dictionary with keys: trade_id, version,
                     counter_party_id, portfolio_id, maturity_date,
                     created_date (optional).

        Returns:
            The persisted Trade instance.

        Raises:
            MaturityDateInPastError: Maturity date is before today.
            LowerVersionError: Incoming version is lower than stored version.
            ValueError: Missing required field or invalid date format.
        """
        trade_id = self._require(payload, "trade_id")
        version = int(self._require(payload, "version"))
        counter_party_id = self._require(payload, "counter_party_id")
        portfolio_id = self._require(payload, "portfolio_id")
        maturity_date = self._parse_date(payload, "maturity_date", trade_id)
        created_date = (
            self._parse_date(payload, "created_date", trade_id)
            if "created_date" in payload and payload["created_date"]
            else date.today()
        )

        # Rule 1 — maturity date must not be in the past
        today = date.today()
        if maturity_date < today:
            raise MaturityDateInPastError(
                trade_id, maturity_date.strftime("%d/%m/%Y")
            )

        # Auto-set expired flag
        expired = "Y" if maturity_date < today else "N"

        existing: Optional[Trade] = Trade.query.filter_by(
            trade_id=trade_id
        ).first()

        if existing is not None:
            # Rule 2 — reject lower version
            if version < existing.version:
                raise LowerVersionError(trade_id, version, existing.version)

            # Rule 3 — same or higher version: update in-place
            existing.version = version
            existing.counter_party_id = counter_party_id
            existing.portfolio_id = portfolio_id
            existing.maturity_date = maturity_date
            existing.created_date = created_date
            existing.expired = expired
            db.session.commit()
            db.session.refresh(existing)
            return existing

        # Rule 4 — new trade_id: insert
        trade = Trade(
            trade_id=trade_id,
            version=version,
            counter_party_id=counter_party_id,
            portfolio_id=portfolio_id,
            maturity_date=maturity_date,
            created_date=created_date,
            expired=expired,
        )
        db.session.add(trade)
        db.session.commit()
        db.session.refresh(trade)
        return trade

    def store_trades_bulk(self, payloads: List[dict]) -> dict:
        """Process a list of trade payloads, collecting per-trade errors.

        Trades that pass validation are persisted; those that fail are
        recorded in the 'errors' list without aborting the batch.

        Args:
            payloads: List of trade dictionaries.

        Returns:
            Dictionary with 'stored' (list of Trade dicts) and
            'errors' (list of error messages).
        """
        stored = []
        errors = []
        for payload in payloads:
            try:
                trade = self.store_trade(payload)
                stored.append(trade.to_dict())
            except (LowerVersionError, MaturityDateInPastError, ValueError) as exc:
                errors.append(str(exc))
        return {"stored": stored, "errors": errors}

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_all_trades(self) -> List[Trade]:
        """Return all trades ordered by trade_id then version."""
        return (
            Trade.query.order_by(Trade.trade_id, Trade.version).all()
        )

    def get_trade_by_id(self, trade_id: str) -> Trade:
        """Return the active trade record for *trade_id*.

        Raises:
            TradeNotFoundError: No trade with that id exists.
        """
        trade = Trade.query.filter_by(trade_id=trade_id).first()
        if trade is None:
            raise TradeNotFoundError(trade_id)
        return trade

    def delete_trade(self, trade_id: str) -> None:
        """Delete a trade by trade_id.

        Raises:
            TradeNotFoundError: No trade with that id exists.
        """
        trade = self.get_trade_by_id(trade_id)
        db.session.delete(trade)
        db.session.commit()

    # ------------------------------------------------------------------
    # Scheduled / maintenance operations
    # ------------------------------------------------------------------

    def expire_matured_trades(self) -> int:
        """Mark all trades whose maturity_date < today as expired='Y'.

        Returns:
            Number of trades updated.
        """
        today = date.today()
        updated = (
            db.session.query(Trade)
            .filter(Trade.maturity_date < today, Trade.expired == "N")
            .all()
        )
        count = 0
        for trade in updated:
            trade.expired = "Y"
            count += 1
        if count:
            db.session.commit()
        return count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require(payload: dict, field: str) -> str:
        value = payload.get(field)
        if value is None or str(value).strip() == "":
            raise ValueError(f"Field '{field}' is required and cannot be empty.")
        return str(value).strip()

    @staticmethod
    def _parse_date(payload: dict, field: str, trade_id: str) -> date:
        """Parse a date field from a payload dictionary.

        Accepts ``datetime.date`` objects (passed through unchanged) or
        strings in DD/MM/YYYY, YYYY-MM-DD, or DD-MM-YYYY formats.

        Args:
            payload: Source dictionary.
            field: Key to read from *payload*.
            trade_id: Used in error messages.

        Returns:
            A ``datetime.date`` object.

        Raises:
            ValueError: The field is missing or the string format is not recognised.
        """
        import datetime as _dt

        raw = payload.get(field)

        # Already a date object — pass through
        if isinstance(raw, _dt.date):
            return raw

        if not raw:
            raise ValueError(
                f"Trade '{trade_id}': field '{field}' is required."
            )

        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return _dt.datetime.strptime(str(raw).strip(), fmt).date()
            except ValueError:
                continue

        raise ValueError(
            f"Trade '{trade_id}': '{field}' value '{raw}' is not a recognised "
            "date format. Use DD/MM/YYYY or YYYY-MM-DD."
        )
