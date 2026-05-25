"""
test_api_quotes.py
------------------
Integration tests for the NextGen CPQ quote endpoints.

Covers all five endpoints against the real catalog (catalog.json) and the
real in-memory store. The store is cleared before and after every test via
the autouse fixture.

Run with: pytest tests/test_api_quotes.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.database as db_module
from api.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_test_db():
    """Replace the module-level SQLAlchemy engine with an in-memory SQLite DB.

    Each test gets a clean database; the production DB file is never touched.
    """
    # StaticPool forces all connections to reuse the same underlying SQLite
    # connection, so tables created by create_all() are visible to every session.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_module.Base.metadata.create_all(bind=test_engine)

    original_engine = db_module.engine
    original_session = db_module.SessionLocal

    db_module.engine = test_engine
    db_module.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    yield

    db_module.engine = original_engine
    db_module.SessionLocal = original_session


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_quote(client, customer_id=None):
    payload = {"customer_id": customer_id} if customer_id else {}
    resp = client.post("/quotes", json=payload)
    assert resp.status_code == 201
    return resp.json()


def add_line(client, quote_id, payload):
    return client.post(f"/quotes/{quote_id}/lines", json=payload)


BASIC_LINE = {
    "sku_id": "sku-support-standard",
    "quantity": 1,
    "term": "MONTHLY",
}

PRO_LINE = {
    "sku_id": "sku-storage-pro",
    "quantity": 1,
    "term": "MONTHLY",
    "selected_attributes": {"storage_gb": 100, "region": "us-east"},
}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /quotes
# ---------------------------------------------------------------------------

class TestCreateQuote:

    def test_creates_quote_with_201(self, client):
        resp = client.post("/quotes", json={})
        assert resp.status_code == 201

    def test_returns_draft_status(self, client):
        resp = client.post("/quotes", json={})
        assert resp.json()["status"] == "DRAFT"

    def test_initial_total_is_zero(self, client):
        resp = client.post("/quotes", json={})
        data = resp.json()
        assert data["total"] == 0.0
        assert data["subtotal"] == 0.0
        assert data["line_count"] == 0

    def test_with_customer_id(self, client):
        resp = client.post("/quotes", json={"customer_id": "cust-001"})
        assert resp.json()["customer_id"] == "cust-001"

    def test_without_customer_id(self, client):
        resp = client.post("/quotes", json={})
        assert resp.json()["customer_id"] is None


# ---------------------------------------------------------------------------
# GET /quotes/{quote_id}
# ---------------------------------------------------------------------------

class TestGetQuote:

    def test_get_existing_quote(self, client):
        q = create_quote(client)
        resp = client.get(f"/quotes/{q['quote_id']}")
        assert resp.status_code == 200
        assert resp.json()["quote_id"] == q["quote_id"]

    def test_get_unknown_quote_returns_404(self, client):
        resp = client.get("/quotes/does-not-exist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /quotes/{quote_id}/lines
# ---------------------------------------------------------------------------

class TestAddLine:

    def test_add_valid_line_returns_200(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], BASIC_LINE)
        assert resp.status_code == 200

    def test_add_line_increments_line_count(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], BASIC_LINE)
        assert resp.json()["line_count"] == 1

    def test_add_line_updates_total(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], BASIC_LINE)
        assert resp.json()["total"] == 29.0

    def test_add_multiple_lines(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        resp = add_line(client, q["quote_id"], PRO_LINE)
        data = resp.json()
        assert data["line_count"] == 2
        assert data["total"] == 29.0 + 99.0

    def test_add_sku_with_required_attributes(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], PRO_LINE)
        assert resp.status_code == 200

    def test_annual_term_applies_discount(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-support-standard",
            "quantity": 1,
            "term": "ANNUAL",
        })
        # $29 * 12 * 0.85 = $295.80
        assert resp.json()["total"] == 295.80

    def test_quantity_multiplies_price(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-support-standard",
            "quantity": 3,
            "term": "MONTHLY",
        })
        assert resp.json()["total"] == 87.0

    def test_manual_discount_applied(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {**BASIC_LINE, "discount_amount": 9.0})
        assert resp.json()["total"] == 20.0

    def test_unknown_sku_returns_422(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {"sku_id": "sku-does-not-exist", "quantity": 1, "term": "MONTHLY"})
        assert resp.status_code == 422

    def test_missing_required_attribute_returns_422(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-storage-pro",
            "quantity": 1,
            "term": "MONTHLY",
            # missing storage_gb and region
        })
        assert resp.status_code == 422

    def test_wrong_attribute_type_returns_422(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-storage-basic",
            "quantity": 1,
            "term": "MONTHLY",
            "selected_attributes": {"storage_gb": "not-a-number"},
        })
        assert resp.status_code == 422

    def test_invalid_enum_value_returns_422(self, client):
        q = create_quote(client)
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-storage-pro",
            "quantity": 1,
            "term": "MONTHLY",
            "selected_attributes": {"storage_gb": 50, "region": "ap-southeast"},
        })
        assert resp.status_code == 422

    def test_incompatible_skus_returns_422(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)  # standard support
        resp = add_line(client, q["quote_id"], {
            "sku_id": "sku-support-premium",
            "quantity": 1,
            "term": "MONTHLY",
        })
        assert resp.status_code == 422
        errors = resp.json()["detail"]
        assert any(e["rule"] == "incompatibility" for e in errors)

    def test_add_line_to_finalized_quote_returns_422(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        client.post(f"/quotes/{q['quote_id']}/finalize")
        resp = add_line(client, q["quote_id"], BASIC_LINE)
        assert resp.status_code == 422

    def test_add_line_to_unknown_quote_returns_404(self, client):
        resp = add_line(client, "no-such-quote", BASIC_LINE)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /quotes/{quote_id}/lines/{line_id}
# ---------------------------------------------------------------------------

class TestRemoveLine:

    def _add_and_get_line_id(self, client, quote_id):
        add_line(client, quote_id, BASIC_LINE)
        # line_id is not exposed in QuoteResponse; fetch via the repository
        from api.dependencies import get_repository
        quote = get_repository().get(quote_id)
        return quote.versions[-1].lines[0].selection.line_id

    def test_remove_existing_line_returns_200(self, client):
        q = create_quote(client)
        line_id = self._add_and_get_line_id(client, q["quote_id"])
        resp = client.delete(f"/quotes/{q['quote_id']}/lines/{line_id}")
        assert resp.status_code == 200

    def test_remove_line_decrements_count(self, client):
        q = create_quote(client)
        line_id = self._add_and_get_line_id(client, q["quote_id"])
        resp = client.delete(f"/quotes/{q['quote_id']}/lines/{line_id}")
        assert resp.json()["line_count"] == 0

    def test_remove_line_updates_total(self, client):
        q = create_quote(client)
        line_id = self._add_and_get_line_id(client, q["quote_id"])
        resp = client.delete(f"/quotes/{q['quote_id']}/lines/{line_id}")
        assert resp.json()["total"] == 0.0

    def test_remove_nonexistent_line_returns_422(self, client):
        q = create_quote(client)
        resp = client.delete(f"/quotes/{q['quote_id']}/lines/fake-line-id")
        assert resp.status_code == 422

    def test_remove_from_finalized_quote_returns_422(self, client):
        q = create_quote(client)
        line_id = self._add_and_get_line_id(client, q["quote_id"])
        client.post(f"/quotes/{q['quote_id']}/finalize")
        resp = client.delete(f"/quotes/{q['quote_id']}/lines/{line_id}")
        assert resp.status_code == 422

    def test_remove_from_unknown_quote_returns_404(self, client):
        resp = client.delete("/quotes/no-such-quote/lines/some-line")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /quotes/{quote_id}/finalize
# ---------------------------------------------------------------------------

class TestFinalizeQuote:

    def test_finalize_returns_200(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        resp = client.post(f"/quotes/{q['quote_id']}/finalize")
        assert resp.status_code == 200

    def test_finalized_status_is_finalized(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        resp = client.post(f"/quotes/{q['quote_id']}/finalize")
        assert resp.json()["status"] == "FINALIZED"

    def test_finalized_quote_totals_preserved(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        resp = client.post(f"/quotes/{q['quote_id']}/finalize")
        assert resp.json()["total"] == 29.0

    def test_finalize_empty_quote_returns_422(self, client):
        q = create_quote(client)
        resp = client.post(f"/quotes/{q['quote_id']}/finalize")
        assert resp.status_code == 422

    def test_finalize_already_finalized_returns_422(self, client):
        q = create_quote(client)
        add_line(client, q["quote_id"], BASIC_LINE)
        client.post(f"/quotes/{q['quote_id']}/finalize")
        resp = client.post(f"/quotes/{q['quote_id']}/finalize")
        assert resp.status_code == 422

    def test_finalize_unknown_quote_returns_404(self, client):
        resp = client.post("/quotes/no-such-quote/finalize")
        assert resp.status_code == 404
