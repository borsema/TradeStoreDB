# Trade Store REST API

[![CI](https://github.com/manishborse/TradeStoreDB/actions/workflows/ci.yml/badge.svg)](https://github.com/manishborse/TradeStoreDB/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11-blue)
![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-80%20passed-brightgreen)

A production-quality Trade Store REST API built with Python/Flask and SQLAlchemy (SQLite). It receives trade records from upstream systems and enforces three core business rules before persisting them.

---

## Problem Statement

Thousands of trades are transmitted to a central store. The store must:

| Rule | Description |
|------|-------------|
| **Version check** | Reject any trade whose version is *lower* than the stored version. Same version replaces the current record. |
| **Maturity date check** | Reject trades whose maturity date is earlier than today. |
| **Auto-expire** | Automatically mark a trade as `expired = Y` when its maturity date is surpassed. |

### Sample data from the problem statement

| Trade ID | Version | Counter-Party ID | Portfolio ID | Maturity Date | Created Date   | Expired |
|----------|---------|-----------------|--------------|---------------|----------------|---------|
| T1       | 1       | CP-1            | B1           | 20/05/2020*   | today          | N       |
| T2       | 2       | CP-2            | B1           | 20/05/2021*   | today          | N       |
| T2       | 1       | CP-1            | B1           | 20/05/2021*   | 14/03/2015     | N       |
| T3       | 3       | CP-3            | B2           | 20/05/2014    | today          | Y       |

> *Use a future date when testing T1/T2 so the maturity-date rule doesn't reject them.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  REST Clients                        │
│       (curl / Postman / upstream systems)            │
└──────────────────┬───────────────────────────────────┘
                   │ HTTP
┌──────────────────▼───────────────────────────────────┐
│              Flask Blueprint /api/v1                  │
│  GET /trades   POST /trades   POST /trades/bulk      │
│  GET /trades/<id>   DELETE /trades/<id>              │
│  POST /trades/expire                                 │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│                 TradeService                          │
│  Business rules: version, maturity date, auto-expire │
└──────────────────┬───────────────────────────────────┘
                   │ SQLAlchemy ORM
┌──────────────────▼───────────────────────────────────┐
│           Trade Model  ←→  SQLite Database            │
└──────────────────────────────────────────────────────┘
```

---

## Project Structure

```
TradeStoreDB/
├── app/
│   ├── __init__.py            # Flask application factory
│   ├── config.py              # Dev / Test / Prod configs
│   ├── extensions.py          # SQLAlchemy singleton
│   ├── exceptions.py          # Domain exceptions
│   ├── models/
│   │   └── trade.py           # Trade SQLAlchemy model
│   ├── routes/
│   │   └── trade_routes.py    # REST endpoints
│   └── services/
│       └── trade_service.py   # Business logic
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_models.py         # Model unit tests
│   ├── test_service.py        # Service unit tests (TDD)
│   ├── test_routes.py         # Route integration tests
│   └── test_exceptions.py    # Exception unit tests
├── diagrams/
│   ├── sequence_store_trade.puml   # POST /trades flow
│   ├── sequence_read_expire.puml   # GET/DELETE/expire flows
│   ├── class_diagram.puml          # Domain class diagram
│   └── design_diagram.puml         # System architecture
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI/CD pipeline
├── requirements.txt
├── requirements-dev.txt
├── run.py                     # Development server entry point
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/manishborse/TradeStoreDB.git
cd TradeStoreDB

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Start the development server
python run.py
```

The API is available at `http://localhost:5000/api/v1`.

---

## API Reference

### Store a Single Trade

```http
POST /api/v1/trades
Content-Type: application/json
```

Request body:

```json
{
  "trade_id": "T1",
  "version": 1,
  "counter_party_id": "CP-1",
  "portfolio_id": "B1",
  "maturity_date": "20/05/2030",
  "created_date": "17/10/2026"
}
```

Responses:

| Status | Meaning |
|--------|---------|
| `201 Created` | Trade stored successfully |
| `400 Bad Request` | Lower version or past maturity date |
| `422 Unprocessable Entity` | Malformed JSON body |

---

### Store Multiple Trades (Batch)

```http
POST /api/v1/trades/bulk
Content-Type: application/json
```

Body: JSON array of trade objects. Invalid trades are collected in `errors`; valid ones are persisted.

Response `207 Multi-Status`:

```json
{
  "stored": [ {…}, {…} ],
  "errors": [ "Trade 'T3': maturity date 20/05/2014 is in the past. Trade rejected." ]
}
```

---

### List All Trades

```http
GET /api/v1/trades
```

Response `200 OK`: JSON array of all trade objects, ordered by `trade_id`, `version`.

---

### Get a Single Trade

```http
GET /api/v1/trades/{trade_id}
```

| Status | Meaning |
|--------|---------|
| `200 OK` | Trade object returned |
| `404 Not Found` | Trade does not exist |

---

### Delete a Trade

```http
DELETE /api/v1/trades/{trade_id}
```

| Status | Meaning |
|--------|---------|
| `200 OK` | Deletion confirmed |
| `404 Not Found` | Trade does not exist |

---

### Trigger Expiry Scan

```http
POST /api/v1/trades/expire
```

Scans all trades and sets `expired = Y` for any trade whose `maturity_date < today`.

Response `200 OK`:

```json
{ "message": "3 trade(s) marked as expired." }
```

> Typically called by a nightly cron job or scheduled task.

---

## Running Tests

```bash
# All tests with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific test file
pytest tests/test_service.py -v

# Verbose output
pytest tests/ -v
```

Expected output:

```
80 passed in 0.18s
Coverage: 99%
```

---

## CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push and pull request:

| Job | Description | Fails build if… |
|-----|-------------|-----------------|
| **Regression Tests** | pytest on Python 3.9, 3.10, 3.11 | Any test fails or coverage < 90% |
| **Vulnerability Scan** | `safety check` against `requirements.txt` | Critical/High CVEs found |
| **Lint** | `flake8` on `app/` and `run.py` | Any style violations |

Artifacts (JUnit XML, coverage XML, Safety JSON) are uploaded per run.

---

## PlantUML Diagrams

Diagrams are in the `diagrams/` directory. Render them with:

- [PlantUML online](https://www.plantuml.com/plantuml)
- VS Code PlantUML extension
- `plantuml diagrams/*.puml` (CLI)

| File | Contents |
|------|----------|
| `sequence_store_trade.puml` | Full POST /trades happy-path + error flows |
| `sequence_read_expire.puml` | GET / DELETE / expire flows |
| `class_diagram.puml` | Domain model, service, exceptions |
| `design_diagram.puml` | System architecture / component diagram |

---

## Business Rules Detail

### 1. Version Validation

```
Incoming version < Stored version  →  LowerVersionError (400)
Incoming version = Stored version  →  Replace (upsert)
Incoming version > Stored version  →  Replace (upsert)
```

### 2. Maturity Date Validation

```
maturity_date < today  →  MaturityDateInPastError (400)
maturity_date = today  →  Accepted (not in the past)
maturity_date > today  →  Accepted
```

### 3. Auto-Expiry

The `POST /api/v1/trades/expire` endpoint (or a nightly scheduler) marks all trades where:

```sql
maturity_date < CURRENT_DATE AND expired = 'N'
```

as `expired = 'Y'`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| Web Framework | Flask 2.3 |
| ORM | SQLAlchemy 2.0 via Flask-SQLAlchemy 3.1 |
| Database | SQLite (dev/test) — swap `DATABASE_URL` for PostgreSQL |
| Testing | pytest 7.4, pytest-cov 4.1 |
| Vulnerability Scan | Safety 3.2 |
| Lint | flake8 7.0 |
| CI/CD | GitHub Actions |
| Diagrams | PlantUML |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | One of `development`, `testing`, `production` |
| `DATABASE_URL` | SQLite file | Full SQLAlchemy DB URI for production |
| `SECRET_KEY` | dev key | Flask secret key — change in production |

