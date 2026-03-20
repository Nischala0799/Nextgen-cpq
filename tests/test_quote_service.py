"""
test_quote_service.py
---------------------
Unit tests for the NextGen CPQ Quote Service.

Run with: pytest tests/ -v
"""

import pytest

from cpq_domain.models import (
    AttributeDefinition,
    AttributeType,
    Catalog,
    Currency,
    Discount,
    DiscountType,
    Money,
    Product,
    QuoteLineSelection,
    QuoteStatus,
    SKU,
    Term,
)
from cpq_domain.config_rules import IncompatibilityRule, DependencyRule
from cpq_domain.quote_service import (
    add_line,
    create_quote,
    finalize_quote,
    remove_line,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_money(amount: float) -> Money:
    return Money(currency=Currency.USD, amount=amount)


def make_sku(sku_id: str, attributes=None) -> SKU:
    return SKU(
        sku_id=sku_id,
        name=f"SKU {sku_id}",
        base_price=make_money(100.0),
        attributes=attributes or [],
    )


def make_catalog(*skus: SKU) -> Catalog:
    products = [
        Product(product_id=f"prod-{s.sku_id}", name=f"Product {s.sku_id}", skus=[s])
        for s in skus
    ]
    return Catalog(products=products, bundles=[])


def make_selection(sku_id: str, quantity: int = 1, term: Term = Term.MONTHLY):
    return QuoteLineSelection(
        sku_id=sku_id,
        quantity=quantity,
        term=term,
    )


def make_discount(amount: float) -> Discount:
    return Discount(
        type=DiscountType.MANUAL,
        amount=make_money(amount),
    )


# ---------------------------------------------------------------------------
# create_quote
# ---------------------------------------------------------------------------

class TestCreateQuote:

    def test_creates_draft_quote(self):
        quote = create_quote()
        assert quote.status == QuoteStatus.DRAFT

    def test_starts_at_version_1(self):
        quote = create_quote()
        assert quote.active_version == 1

    def test_starts_with_one_version(self):
        quote = create_quote()
        assert len(quote.versions) == 1

    def test_initial_version_has_no_lines(self):
        quote = create_quote()
        assert quote.versions[0].lines == []

    def test_initial_totals_are_zero(self):
        quote = create_quote()
        totals = quote.versions[0].totals
        assert totals.total.amount == 0.0

    def test_with_customer_id(self):
        quote = create_quote(customer_id="cust-001")
        assert quote.customer_id == "cust-001"

    def test_without_customer_id(self):
        quote = create_quote()
        assert quote.customer_id is None


# ---------------------------------------------------------------------------
# add_line
# ---------------------------------------------------------------------------

class TestAddLine:

    def test_add_valid_line_succeeds(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        assert result.ok is True
        assert result.errors == []

    def test_add_line_increments_version(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        assert result.quote.active_version == 2

    def test_add_line_preserves_version_history(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        assert len(result.quote.versions) == 2

    def test_add_line_updates_totals(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        assert result.quote.versions[-1].totals.total.amount == 100.0

    def test_add_multiple_lines(self):
        catalog = make_catalog(make_sku("sku-A"), make_sku("sku-B"))
        quote = create_quote()
        result1 = add_line(quote, make_selection("sku-A"), catalog)
        result2 = add_line(result1.quote, make_selection("sku-B"), catalog)
        assert result2.ok is True
        assert len(result2.quote.versions[-1].lines) == 2
        assert result2.quote.versions[-1].totals.total.amount == 200.0

    def test_add_line_with_discount(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(
            quote,
            make_selection("sku-A"),
            catalog,
            discounts=[make_discount(20.0)],
        )
        assert result.ok is True
        assert result.quote.versions[-1].totals.total.amount == 80.0

    def test_invalid_sku_rejected(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-MISSING"), catalog)
        assert result.ok is False
        assert len(result.errors) > 0

    def test_invalid_config_rejected(self):
        from cpq_domain.models import AttributeDefinition, AttributeType
        sku = make_sku("sku-A", attributes=[
            AttributeDefinition(
                key="plan",
                label="Plan",
                type=AttributeType.STRING,
                required=True,
            )
        ])
        catalog = make_catalog(sku)
        quote = create_quote()
        # Missing required attribute
        result = add_line(quote, make_selection("sku-A"), catalog)
        assert result.ok is False
        assert any("plan" in e.message for e in result.errors)

    def test_incompatible_skus_rejected(self):
        catalog = make_catalog(make_sku("sku-A"), make_sku("sku-B"))
        quote = create_quote()
        result1 = add_line(quote, make_selection("sku-A"), catalog)
        rules = [IncompatibilityRule(sku_a="sku-A", sku_b="sku-B")]
        result2 = add_line(
            result1.quote,
            make_selection("sku-B"),
            catalog,
            incompatibility_rules=rules,
        )
        assert result2.ok is False
        assert any(e.rule == "incompatibility" for e in result2.errors)

    def test_cannot_add_to_finalized_quote(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        finalized = finalize_quote(result.quote)
        result2 = add_line(finalized.quote, make_selection("sku-A"), catalog)
        assert result2.ok is False
        assert any(e.rule == "quote_status" for e in result2.errors)

    def test_original_quote_not_mutated(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        original_version = quote.active_version
        add_line(quote, make_selection("sku-A"), catalog)
        assert quote.active_version == original_version


# ---------------------------------------------------------------------------
# remove_line
# ---------------------------------------------------------------------------

class TestRemoveLine:

    def test_remove_existing_line_succeeds(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = add_line(quote, make_selection("sku-A"), catalog)
        line_id = result.quote.versions[-1].lines[0].selection.line_id
        remove_result = remove_line(result.quote, line_id)
        assert remove_result.ok is True

    def test_remove_line_decrements_line_count(self):
        catalog = make_catalog(make_sku("sku-A"), make_sku("sku-B"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        r2 = add_line(r1.quote, make_selection("sku-B"), catalog)
        line_id = r2.quote.versions[-1].lines[0].selection.line_id
        r3 = remove_line(r2.quote, line_id)
        assert len(r3.quote.versions[-1].lines) == 1

    def test_remove_line_updates_totals(self):
        catalog = make_catalog(make_sku("sku-A"), make_sku("sku-B"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        r2 = add_line(r1.quote, make_selection("sku-B"), catalog)
        line_id = r2.quote.versions[-1].lines[0].selection.line_id
        r3 = remove_line(r2.quote, line_id)
        assert r3.quote.versions[-1].totals.total.amount == 100.0

    def test_remove_nonexistent_line_fails(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        result = remove_line(quote, "nonexistent-line-id")
        assert result.ok is False
        assert any(e.rule == "line_not_found" for e in result.errors)

    def test_cannot_remove_from_finalized_quote(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        finalized = finalize_quote(r1.quote)
        line_id = finalized.quote.versions[-1].lines[0].selection.line_id
        result = remove_line(finalized.quote, line_id)
        assert result.ok is False
        assert any(e.rule == "quote_status" for e in result.errors)


# ---------------------------------------------------------------------------
# finalize_quote
# ---------------------------------------------------------------------------

class TestFinalizeQuote:

    def test_finalize_draft_quote_succeeds(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        result = finalize_quote(r1.quote)
        assert result.ok is True
        assert result.quote.status == QuoteStatus.FINALIZED

    def test_cannot_finalize_empty_quote(self):
        quote = create_quote()
        result = finalize_quote(quote)
        assert result.ok is False
        assert any(e.rule == "empty_quote" for e in result.errors)

    def test_cannot_finalize_already_finalized_quote(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        r2 = finalize_quote(r1.quote)
        r3 = finalize_quote(r2.quote)
        assert r3.ok is False
        assert any(e.rule == "quote_status" for e in r3.errors)

    def test_finalized_quote_status_is_finalized(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        result = finalize_quote(r1.quote)
        assert result.quote.status == QuoteStatus.FINALIZED

    def test_original_quote_not_mutated_on_finalize(self):
        catalog = make_catalog(make_sku("sku-A"))
        quote = create_quote()
        r1 = add_line(quote, make_selection("sku-A"), catalog)
        original_status = r1.quote.status
        finalize_quote(r1.quote)
        assert r1.quote.status == original_status