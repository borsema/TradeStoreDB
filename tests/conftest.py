"""Shared pytest fixtures for the Trade Store test suite."""
import pytest
from datetime import date, timedelta

from app import create_app
from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Application / DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create a testing application instance (session-scoped)."""
    application = create_app("testing")
    yield application


@pytest.fixture(scope="session")
def _db_session_create(app):
    """Create all tables once for the test session."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture
def db(app, _db_session_create):
    """Provide a clean database for each test by rolling back after each test."""
    with app.app_context():
        yield _db_session_create
        _db_session_create.session.rollback()
        # Truncate all tables between tests
        for table in reversed(_db_session_create.metadata.sorted_tables):
            _db_session_create.session.execute(table.delete())
        _db_session_create.session.commit()


@pytest.fixture
def client(app, db):
    """Provide a Flask test client with a clean database."""
    with app.test_client() as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def future_date():
    """A maturity date well in the future."""
    return (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")


@pytest.fixture
def past_date():
    """A maturity date clearly in the past."""
    return "20/05/2014"


@pytest.fixture
def today_str():
    return date.today().strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Sample trade payloads (matching the problem-statement data)
# ---------------------------------------------------------------------------

@pytest.fixture
def trade_t1(future_date):
    return {
        "trade_id": "T1",
        "version": 1,
        "counter_party_id": "CP-1",
        "portfolio_id": "B1",
        "maturity_date": future_date,
    }


@pytest.fixture
def trade_t2(future_date):
    return {
        "trade_id": "T2",
        "version": 2,
        "counter_party_id": "CP-2",
        "portfolio_id": "B1",
        "maturity_date": future_date,
    }


@pytest.fixture
def trade_t3(future_date):
    return {
        "trade_id": "T3",
        "version": 3,
        "counter_party_id": "CP-3",
        "portfolio_id": "B2",
        "maturity_date": future_date,
    }
