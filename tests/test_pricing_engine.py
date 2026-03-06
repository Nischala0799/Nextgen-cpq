import pytest

from cpq_domain.models import (
    Catalog,
    Currency,
    Discount,
    DiscountType,
    Money,
    Product,
    QuoteLineSelection,
    SKU,
    Term,
)
from cpq_domain.pricing_engine import (
    ANNUAL_DISCOUNT_FACTOR,
    apply_discounts,
    apply_quantity,
    apply_term_adjustment,
    calculate_base_price,
    calculate_totals,
    price_line,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_money(amount: float) -> Money:
    return Money(currency=Currency.USD, amount=amount)

def make_sku(sku_id: str, base_price: float) -> SKU:
    return SKU(
        sku_id=sku_id,
        name=f"SKU {sku_id}",
        base_price=make_money(base_price),
    )

def make_catalog(*skus: SKU) -> Catalog:
    products = [
        Product(product_id=f"prod-{s.sku_id}", name=f"Product {s.sku_id}", skus=[s])
        for s in skus
    ]
    return Catalog(products=products, bundles=[])

def make_selection(sku_id: str, quantity: int = 1, term: Term = Term.MONTHLY):
    return QuoteLineSelection(sku_id=sku_id, quantity=quantity, term=term)

def make_discount(amount: float, dtype: DiscountType = DiscountType.MANUAL):
    return Discount(type=dtype, amount=make_money(amount), description="Test discount")


# ---------------------------------------------------------------------------
# calculate_base_price
# ---------------------------------------------------------------------------

class TestCalculateBasePrice:

    def test_returns_sku_base_price(self):
        sku = make_sku("sku-001", 100.0)
        assert calculate_base_price(sku).amount == 100.0

    def test_rounds_to_two_decimals(self):
        sku = make_sku("sku-002", 99.999)
        assert calculate_base_price(sku).amount == 100.0

    def test_zero_base_price(self):
        sku = make_sku("sku-003", 0.0)
        assert calculate_base_price(sku).amount == 0.0


# ---------------------------------------------------------------------------
# apply_quantity
# ---------------------------------------------------------------------------

class TestApplyQuantity:

    def test_single_unit(self):
        assert apply_quantity(make_money(100.0), 1).amount == 100.0

    def test_multiple_units(self):
        assert apply_quantity(make_money(50.0), 5).amount == 250.0

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError, match="Quantity must be >= 1"):
            apply_quantity(make_money(100.0), 0)

    def test_negative_quantity_raises(self):
        with pytest.raises(ValueError):
            apply_quantity(make_money(100.0), -1)


# ---------------------------------------------------------------------------
# apply_term_adjustment
# ---------------------------------------------------------------------------

class TestApplyTermAdjustment:

    def test_monthly_no_adjustment(self):
        adjusted, adjustment = apply_term_adjustment(make_money(200.0), Term.MONTHLY)
        assert adjusted.amount == 200.0
        assert adjustment.amount == 0.0

    def test_annual_applies_factor(self):
        adjusted, _ = apply_term_adjustment(make_money(100.0), Term.ANNUAL)
        assert adjusted.amount == round(100.0 * 12 * ANNUAL_DISCOUNT_FACTOR, 2)

    def test_annual_adjustment_is_negative(self):
        _, adjustment = apply_term_adjustment(make_money(100.0), Term.ANNUAL)
        assert adjustment.amount > 0


# ---------------------------------------------------------------------------
# apply_discounts
# ---------------------------------------------------------------------------

class TestApplyDiscounts:

    def test_no_discounts(self):
        final, total = apply_discounts(make_money(500.0), [])
        assert final.amount == 500.0
        assert total.amount == 0.0

    def test_single_discount(self):
        final, total = apply_discounts(make_money(500.0), [make_discount(50.0)])
        assert final.amount == 450.0
        assert total.amount == 50.0

    def test_multiple_discounts(self):
        final, total = apply_discounts(
            make_money(500.0), [make_discount(50.0), make_discount(100.0)]
        )
        assert final.amount == 350.0
        assert total.amount == 150.0

    def test_floors_at_zero(self):
        final, _ = apply_discounts(make_money(100.0), [make_discount(999.0)])
        assert final.amount == 0.0


# ---------------------------------------------------------------------------
# price_line
# ---------------------------------------------------------------------------

class TestPriceLine:

    def test_monthly_no_discount(self):
        catalog = make_catalog(make_sku("sku-A", 100.0))
        line = price_line(make_selection("sku-A", quantity=2), catalog)
        assert line.breakdown.base.amount == 100.0
        assert line.breakdown.total.amount == 200.0

    def test_annual_pricing(self):
        catalog = make_catalog(make_sku("sku-B", 100.0))
        line = price_line(make_selection("sku-B", term=Term.ANNUAL), catalog)
        assert line.breakdown.total.amount == round(100.0 * 12 * ANNUAL_DISCOUNT_FACTOR, 2)

    def test_with_discount(self):
        catalog = make_catalog(make_sku("sku-C", 200.0))
        line = price_line(make_selection("sku-C"), catalog, discounts=[make_discount(30.0)])
        assert line.breakdown.total.amount == 170.0

    def test_sku_not_found_raises(self):
        catalog = make_catalog(make_sku("sku-X", 100.0))
        with pytest.raises(ValueError, match="SKU 'sku-MISSING' not found"):
            price_line(make_selection("sku-MISSING"), catalog)


# ---------------------------------------------------------------------------
# calculate_totals
# ---------------------------------------------------------------------------

class TestCalculateTotals:

    def test_empty_lines(self):
        totals = calculate_totals([])
        assert totals.total.amount == 0.0

    def test_single_line(self):
        catalog = make_catalog(make_sku("sku-T1", 100.0))
        lines = [price_line(make_selection("sku-T1"), catalog)]
        totals = calculate_totals(lines)
        assert totals.subtotal.amount == 100.0
        assert totals.total.amount == 100.0

    def test_multiple_lines(self):
        catalog = make_catalog(make_sku("sku-T2", 100.0), make_sku("sku-T3", 200.0))
        lines = [
            price_line(make_selection("sku-T2"), catalog),
            price_line(make_selection("sku-T3"), catalog),
        ]
        totals = calculate_totals(lines)
        assert totals.total.amount == 300.0

    def test_totals_reflect_discounts(self):
        catalog = make_catalog(make_sku("sku-T4", 500.0))
        lines = [price_line(make_selection("sku-T4"), catalog, discounts=[make_discount(100.0)])]
        totals = calculate_totals(lines)
        assert totals.subtotal.amount == 500.0
        assert totals.discounts.amount == 100.0
        assert totals.total.amount == 400.0