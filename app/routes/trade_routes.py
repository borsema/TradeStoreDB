"""Trade Store REST API routes.

Endpoints
---------
GET    /api/v1/trades                  – list all trades
GET    /api/v1/trades/<trade_id>       – fetch a single trade
POST   /api/v1/trades                  – store a single trade
POST   /api/v1/trades/bulk             – store many trades (batch)
DELETE /api/v1/trades/<trade_id>       – delete a trade
POST   /api/v1/trades/expire           – trigger expiry scan
"""
from flask import Blueprint, jsonify, request

from ..services.trade_service import TradeService
from ..exceptions import (
    LowerVersionError,
    MaturityDateInPastError,
    TradeNotFoundError,
    TradeStoreError,
)

trade_bp = Blueprint("trades", __name__)
_svc = TradeService()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _error(message: str, status: int):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@trade_bp.route("/trades", methods=["GET"])
def list_trades():
    """Return all trades in the store.

    Returns:
        200 – JSON array of trade objects.
    """
    trades = _svc.get_all_trades()
    return jsonify([t.to_dict() for t in trades]), 200


@trade_bp.route("/trades/<string:trade_id>", methods=["GET"])
def get_trade(trade_id: str):
    """Return the active record for a given trade_id.

    Returns:
        200 – trade object.
        404 – trade not found.
    """
    try:
        trade = _svc.get_trade_by_id(trade_id)
        return jsonify(trade.to_dict()), 200
    except TradeNotFoundError as exc:
        return _error(exc.message, exc.status_code)


@trade_bp.route("/trades", methods=["POST"])
def create_trade():
    """Store a single trade.

    Request body (JSON):
        trade_id, version, counter_party_id, portfolio_id,
        maturity_date (DD/MM/YYYY), created_date (optional)

    Returns:
        201 – stored trade object.
        400 – validation failure (lower version / past maturity date).
        422 – malformed request body.
    """
    data = request.get_json(silent=True)
    if not data:
        return _error("Request body must be valid JSON.", 422)

    try:
        trade = _svc.store_trade(data)
        return jsonify(trade.to_dict()), 201
    except (LowerVersionError, MaturityDateInPastError) as exc:
        return _error(exc.message, exc.status_code)
    except ValueError as exc:
        return _error(str(exc), 400)
    except TradeStoreError as exc:
        return _error(exc.message, exc.status_code)


@trade_bp.route("/trades/bulk", methods=["POST"])
def create_trades_bulk():
    """Store a batch of trades in a single request.

    Trades that pass validation are persisted; invalid ones are collected
    in the 'errors' list without aborting the entire batch.

    Request body (JSON): array of trade objects.

    Returns:
        207 – partial success (some trades stored, some rejected).
        422 – body is not a JSON array.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return _error("Request body must be a JSON array of trade objects.", 422)

    result = _svc.store_trades_bulk(data)
    return jsonify(result), 207


@trade_bp.route("/trades/<string:trade_id>", methods=["DELETE"])
def delete_trade(trade_id: str):
    """Delete a trade by trade_id.

    Returns:
        200 – deletion confirmed.
        404 – trade not found.
    """
    try:
        _svc.delete_trade(trade_id)
        return jsonify({"message": f"Trade '{trade_id}' deleted successfully."}), 200
    except TradeNotFoundError as exc:
        return _error(exc.message, exc.status_code)


@trade_bp.route("/trades/expire", methods=["POST"])
def expire_trades():
    """Trigger the maturity-date expiry scan.

    Marks all trades whose maturity_date < today as expired='Y'.

    Returns:
        200 – number of trades updated.
    """
    count = _svc.expire_matured_trades()
    return jsonify({"message": f"{count} trade(s) marked as expired."}), 200
