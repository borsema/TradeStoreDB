"""Integration tests for Trade Store REST API endpoints."""
import json
import pytest
from datetime import date, timedelta


def _future(days: int = 365) -> str:
    return (date.today() + timedelta(days=days)).strftime("%d/%m/%Y")


def _past(days: int = 365) -> str:
    return (date.today() - timedelta(days=days)).strftime("%d/%m/%Y")


def _post(client, payload: dict):
    return client.post(
        "/api/v1/trades",
        data=json.dumps(payload),
        content_type="application/json",
    )


def _base_payload(**overrides) -> dict:
    data = {
        "trade_id": "T1",
        "version": 1,
        "counter_party_id": "CP-1",
        "portfolio_id": "B1",
        "maturity_date": _future(),
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# POST /api/v1/trades
# ---------------------------------------------------------------------------

class TestCreateTrade:
    """Tests for POST /api/v1/trades."""

    def test_create_trade_returns_201(self, client):
        resp = _post(client, _base_payload())
        assert resp.status_code == 201

    def test_create_trade_response_body(self, client):
        resp = _post(client, _base_payload(trade_id="T1", version=1))
        body = resp.get_json()
        assert body["trade_id"] == "T1"
        assert body["version"] == 1
        assert body["expired"] == "N"

    def test_create_trade_past_maturity_returns_400(self, client):
        resp = _post(client, _base_payload(maturity_date=_past()))
        assert resp.status_code == 400
        assert "maturity date" in resp.get_json()["error"].lower()

    def test_create_trade_lower_version_returns_400(self, client):
        _post(client, _base_payload(version=5))
        resp = _post(client, _base_payload(version=3))
        assert resp.status_code == 400
        assert "lower" in resp.get_json()["error"].lower()

    def test_create_trade_same_version_replaces_200_then_201(self, client):
        """First insert → 201. Same version upsert → 201."""
        r1 = _post(client, _base_payload(version=1, counter_party_id="CP-FIRST"))
        r2 = _post(client, _base_payload(version=1, counter_party_id="CP-SECOND"))
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r2.get_json()["counter_party_id"] == "CP-SECOND"

    def test_create_trade_higher_version_replaces(self, client):
        _post(client, _base_payload(version=1))
        resp = _post(client, _base_payload(version=2, counter_party_id="CP-NEW"))
        assert resp.status_code == 201
        assert resp.get_json()["version"] == 2

    def test_create_trade_missing_field_returns_400(self, client):
        payload = _base_payload()
        del payload["trade_id"]
        resp = _post(client, payload)
        assert resp.status_code == 400

    def test_create_trade_non_json_body_returns_422(self, client):
        resp = client.post(
            "/api/v1/trades",
            data="not json",
            content_type="text/plain",
        )
        assert resp.status_code == 422

    def test_create_trade_empty_body_returns_422(self, client):
        resp = client.post("/api/v1/trades", content_type="application/json")
        assert resp.status_code == 422

    def test_create_trade_today_maturity_accepted(self, client):
        """Maturity date = today is NOT 'in the past' (rule: < today), so it is accepted."""
        today = date.today().strftime("%d/%m/%Y")
        resp = _post(client, _base_payload(maturity_date=today))
        assert resp.status_code == 201

    # ------------------------------------------------------------------
    # Problem-statement scenarios
    # ------------------------------------------------------------------

    def test_ps_t1_v1_accepted(self, client):
        resp = _post(client, {
            "trade_id": "T1", "version": 1,
            "counter_party_id": "CP-1", "portfolio_id": "B1",
            "maturity_date": _future(200),
        })
        assert resp.status_code == 201

    def test_ps_t2_v2_then_v1_rejected(self, client):
        _post(client, {
            "trade_id": "T2", "version": 2,
            "counter_party_id": "CP-2", "portfolio_id": "B1",
            "maturity_date": _future(300),
        })
        resp = _post(client, {
            "trade_id": "T2", "version": 1,
            "counter_party_id": "CP-1", "portfolio_id": "B1",
            "maturity_date": _future(300),
        })
        assert resp.status_code == 400

    def test_ps_t3_past_maturity_rejected(self, client):
        resp = _post(client, {
            "trade_id": "T3", "version": 3,
            "counter_party_id": "CP-3", "portfolio_id": "B2",
            "maturity_date": "20/05/2014",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/v1/trades
# ---------------------------------------------------------------------------

class TestListTrades:
    """Tests for GET /api/v1/trades."""

    def test_list_trades_empty(self, client):
        resp = client.get("/api/v1/trades")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_list_trades_returns_all(self, client):
        _post(client, _base_payload(trade_id="TA", version=1))
        _post(client, _base_payload(trade_id="TB", version=1))
        resp = client.get("/api/v1/trades")
        assert resp.status_code == 200
        ids = [t["trade_id"] for t in resp.get_json()]
        assert "TA" in ids
        assert "TB" in ids

    def test_list_trades_response_is_json_array(self, client):
        resp = client.get("/api/v1/trades")
        assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# GET /api/v1/trades/<trade_id>
# ---------------------------------------------------------------------------

class TestGetTrade:
    """Tests for GET /api/v1/trades/<trade_id>."""

    def test_get_existing_trade(self, client):
        _post(client, _base_payload(trade_id="TG1", version=1))
        resp = client.get("/api/v1/trades/TG1")
        assert resp.status_code == 200
        assert resp.get_json()["trade_id"] == "TG1"

    def test_get_nonexistent_trade_returns_404(self, client):
        resp = client.get("/api/v1/trades/DOES_NOT_EXIST")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_get_trade_shows_latest_version(self, client):
        _post(client, _base_payload(trade_id="TG2", version=1))
        _post(client, _base_payload(trade_id="TG2", version=3, counter_party_id="CP-3"))
        resp = client.get("/api/v1/trades/TG2")
        assert resp.get_json()["version"] == 3


# ---------------------------------------------------------------------------
# DELETE /api/v1/trades/<trade_id>
# ---------------------------------------------------------------------------

class TestDeleteTrade:
    """Tests for DELETE /api/v1/trades/<trade_id>."""

    def test_delete_existing_trade_returns_200(self, client):
        _post(client, _base_payload(trade_id="TD1", version=1))
        resp = client.delete("/api/v1/trades/TD1")
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

    def test_deleted_trade_no_longer_fetchable(self, client):
        _post(client, _base_payload(trade_id="TD2", version=1))
        client.delete("/api/v1/trades/TD2")
        resp = client.get("/api/v1/trades/TD2")
        assert resp.status_code == 404

    def test_delete_nonexistent_trade_returns_404(self, client):
        resp = client.delete("/api/v1/trades/GHOST")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/trades/bulk
# ---------------------------------------------------------------------------

class TestBulkCreate:
    """Tests for POST /api/v1/trades/bulk."""

    def test_bulk_all_valid_returns_207(self, client):
        payload = [
            _base_payload(trade_id="TB1", version=1),
            _base_payload(trade_id="TB2", version=1),
        ]
        resp = client.post(
            "/api/v1/trades/bulk",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 207
        body = resp.get_json()
        assert len(body["stored"]) == 2
        assert body["errors"] == []

    def test_bulk_partial_failure(self, client):
        payload = [
            _base_payload(trade_id="TB3", version=1),
            _base_payload(trade_id="TB4", version=1, maturity_date=_past()),  # invalid
        ]
        resp = client.post(
            "/api/v1/trades/bulk",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 207
        body = resp.get_json()
        assert len(body["stored"]) == 1
        assert len(body["errors"]) == 1

    def test_bulk_non_array_body_returns_422(self, client):
        resp = client.post(
            "/api/v1/trades/bulk",
            data=json.dumps({"trade_id": "X"}),
            content_type="application/json",
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/trades/expire
# ---------------------------------------------------------------------------

class TestExpireTrades:
    """Tests for POST /api/v1/trades/expire."""

    def test_expire_endpoint_returns_200(self, client):
        resp = client.post("/api/v1/trades/expire")
        assert resp.status_code == 200

    def test_expire_endpoint_returns_count(self, client):
        resp = client.post("/api/v1/trades/expire")
        body = resp.get_json()
        assert "trade(s) marked as expired" in body["message"]

    def test_expire_marks_matured_trades(self, client):
        """Trades with past maturity, inserted directly into DB, are expired."""
        from app.models.trade import Trade
        from app.extensions import db
        from app import create_app

        # We need app context to insert directly
        app = create_app("testing")
        with app.app_context():
            db.create_all()
            t = Trade(
                trade_id="T_EXP_ROUTE",
                version=1,
                counter_party_id="CP-E",
                portfolio_id="BE",
                maturity_date=date(2020, 6, 1),
                expired="N",
            )
            db.session.add(t)
            db.session.commit()

            test_client = app.test_client()
            resp = test_client.post("/api/v1/trades/expire")
            assert resp.status_code == 200
            assert "1" in resp.get_json()["message"]

            refreshed = Trade.query.filter_by(trade_id="T_EXP_ROUTE").first()
            assert refreshed.expired == "Y"
            db.drop_all()
