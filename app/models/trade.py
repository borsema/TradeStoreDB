"""Trade domain model."""
from datetime import date
from ..extensions import db


class Trade(db.Model):
    """Represents a single trade record in the store.

    Business rules enforced at the service layer:
    - Lower-version trades for an existing trade_id are rejected.
    - Same-version trades replace the existing record.
    - Trades with a maturity_date in the past are rejected on ingestion.
    - Trades whose maturity_date has passed are automatically marked expired.
    """

    __tablename__ = "trade"

    # Primary key is (trade_id, version) — a trade may have multiple versions
    # in history, but only the *latest* version is the active record.
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trade_id = db.Column(db.String(20), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    counter_party_id = db.Column(db.String(50), nullable=False)
    portfolio_id = db.Column(db.String(50), nullable=False)
    maturity_date = db.Column(db.Date, nullable=False)
    created_date = db.Column(db.Date, nullable=False, default=date.today)
    expired = db.Column(db.String(1), nullable=False, default="N")

    # Ensure only one active record per trade_id
    __table_args__ = (
        db.UniqueConstraint("trade_id", name="uq_trade_trade_id"),
    )

    def to_dict(self) -> dict:
        """Serialize the trade to a plain dictionary."""
        return {
            "id": self.id,
            "trade_id": self.trade_id,
            "version": self.version,
            "counter_party_id": self.counter_party_id,
            "portfolio_id": self.portfolio_id,
            "maturity_date": self.maturity_date.strftime("%d/%m/%Y"),
            "created_date": self.created_date.strftime("%d/%m/%Y"),
            "expired": self.expired,
        }

    def __repr__(self) -> str:
        return (
            f"<Trade trade_id={self.trade_id} version={self.version} "
            f"expired={self.expired}>"
        )
