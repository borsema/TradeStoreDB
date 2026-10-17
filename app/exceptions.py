"""Domain-level exceptions for the Trade Store."""


class TradeStoreError(Exception):
    """Base exception for all Trade Store errors."""

    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LowerVersionError(TradeStoreError):
    """Raised when an incoming trade has a lower version than the stored one."""

    status_code = 400

    def __init__(self, trade_id: str, incoming: int, stored: int):
        super().__init__(
            f"Trade '{trade_id}': incoming version {incoming} is lower than "
            f"stored version {stored}. Trade rejected."
        )
        self.trade_id = trade_id
        self.incoming_version = incoming
        self.stored_version = stored


class MaturityDateInPastError(TradeStoreError):
    """Raised when the maturity date of a trade is earlier than today."""

    status_code = 400

    def __init__(self, trade_id: str, maturity_date: str):
        super().__init__(
            f"Trade '{trade_id}': maturity date {maturity_date} is in the past. "
            "Trade rejected."
        )
        self.trade_id = trade_id
        self.maturity_date = maturity_date


class TradeNotFoundError(TradeStoreError):
    """Raised when a requested trade does not exist in the store."""

    status_code = 404

    def __init__(self, trade_id: str):
        super().__init__(f"Trade '{trade_id}' not found.")
        self.trade_id = trade_id
