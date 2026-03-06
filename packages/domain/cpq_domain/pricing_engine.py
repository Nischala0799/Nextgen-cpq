from __future__ import annotations

from typing import List

from cpq_domain.models import (
    Catalog,
    Currency,
    Discount,
    Money,
    PriceBreakdown,
    QuoteLine,
    QuoteLineSelection,
    QuoteTotals,
    SKU,
    Term,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Annual price = monthly * 12 * ANNUAL_DISCOUNT_FACTOR
# 0.85 = 15% savings for committing to annual term
ANNUAL_DISCOUNT_FACTOR = 0.85


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _zero() -> Money:
    """Return a zero-value Money object in USD."""
    return Money(currency=Currency.USD, amount=0.0)


def _money(amount: float) -> Money:
    """Create a USD Money object rounded to 2 decimal places."""
    return Money(currency=Currency.USD, amount=round(amount, 2))


def _lookup_sku(catalog: Catalog, sku_id: str) -> SKU:
    """
    Find a SKU by sku_id across all products in the catalog.

    Raises:
        ValueError: if the SKU is not found.
    """
    for product in catalog.products:
        for sku in product.skus:
            if sku.sku_id == sku_id:
                return sku
    raise ValueError(f"SKU '{sku_id}' not found in catalog.")


def _sum_discounts(discounts: List[Discount]) -> float:
    """Sum all discount amounts into a single float."""
    return sum(d.amount.amount for d in discounts)


# ---------------------------------------------------------------------------
# Core pricing steps
# ---------------------------------------------------------------------------

def calculate_base_price(sku: SKU) -> Money:
    """
    Step 1: Return the SKU's base unit price.

    This is the raw price before quantity, term, or discount adjustments.
    """
    return _money(sku.base_price.amount)


def apply_quantity(base_price: Money, quantity: int) -> Money:
    """
    Step 2: Multiply base price by quantity.

    Args:
        base_price: Unit price for one item.
        quantity:   Number of units (must be >= 1).

    Returns:
        Total price for all units before term/discount adjustments.
    """
    if quantity < 1:
        raise ValueError(f"Quantity must be >= 1, got {quantity}.")
    return _money(base_price.amount * quantity)


def apply_term_adjustment(
    quantity_price: Money,
    term: Term,
) -> tuple[Money, Money]:
    """
    Step 3: Adjust price based on billing term.

    MONTHLY: no adjustment.
    ANNUAL:  multiply by 12 months, apply ANNUAL_DISCOUNT_FACTOR.

    Example:
        Monthly unit price = $100, qty = 2 → quantity_price = $200
        Annual raw         = $200 * 12 = $2,400
        Annual discounted  = $2,400 * 0.85 = $2,040
        term_adjustment    = $2,040 - $2,400 = -$360 (savings)

    Returns:
        (adjusted_price, term_adjustment)
        term_adjustment is negative for annual (represents savings).
    """
    if term == Term.MONTHLY:
        return quantity_price, _zero()

    annual_raw = quantity_price.amount * 12
    annual_discounted = annual_raw * ANNUAL_DISCOUNT_FACTOR
    term_adjustment = annual_raw - annual_discounted

    return _money(annual_discounted), _money(term_adjustment)


def apply_discounts(
    price_after_term: Money,
    discounts: List[Discount],
) -> tuple[Money, Money]:
    """
    Step 4: Subtract all discounts from the price.

    Discounts are absolute Money amounts (not percentages), as defined
    in models.py. MANUAL and RULE_BASED discounts are treated identically
    here — the distinction is metadata for reporting only.

    Final price is floored at 0.00 (cannot go negative).

    Returns:
        (final_price, total_discount_amount)
    """
    total_discount = _sum_discounts(discounts)
    final_amount = max(0.0, price_after_term.amount - total_discount)
    return _money(final_amount), _money(total_discount)


# ---------------------------------------------------------------------------
# Line-level pricing
# ---------------------------------------------------------------------------

def price_line(
    selection: QuoteLineSelection,
    catalog: Catalog,
    discounts: List[Discount] | None = None,
) -> QuoteLine:
    """
    Price a single QuoteLineSelection into a fully populated QuoteLine.

    Steps:
      1. Look up the SKU in the catalog
      2. Calculate base price
      3. Apply quantity multiplier
      4. Apply term adjustment
      5. Apply discounts
      6. Assemble PriceBreakdown and QuoteLine

    Args:
        selection: The user's configuration choices for this line.
        catalog:   Product catalog used to look up SKU base prices.
        discounts: Optional list of discounts to apply to this line.

    Returns:
        A fully priced QuoteLine with a populated PriceBreakdown.
    """
    discounts = discounts or []

    # Step 1: Look up SKU
    sku = _lookup_sku(catalog, selection.sku_id)

    # Step 2: Base price (unit)
    base = calculate_base_price(sku)

    # Step 3: Quantity
    after_quantity = apply_quantity(base, selection.quantity)
    quantity_adjustment = _money(after_quantity.amount - base.amount)

    # Step 4: Term
    after_term, term_adjustment = apply_term_adjustment(
        after_quantity, selection.term
    )

    # Step 5: Discounts
    final_price, total_discounts = apply_discounts(after_term, discounts)

    # Step 6: Assemble
    breakdown = PriceBreakdown(
        base=base,
        term_adjustment=term_adjustment,
        quantity_adjustment=quantity_adjustment,
        discounts=total_discounts,
        total=final_price,
    )

    return QuoteLine(
        selection=selection,
        breakdown=breakdown,
        applied_discounts=discounts,
    )


# ---------------------------------------------------------------------------
# Quote-level totals
# ---------------------------------------------------------------------------

def calculate_totals(lines: List[QuoteLine]) -> QuoteTotals:
    """
    Aggregate all QuoteLines into QuoteTotals.

    Subtotal = sum of each line's pre-discount price
    Discounts = sum of all line-level discount amounts
    Total     = subtotal - discounts

    Args:
        lines: All priced lines in the current quote version.

    Returns:
        QuoteTotals with subtotal, discounts, and final total.
    """
    subtotal = 0.0
    total_discounts = 0.0

    for line in lines:
        bd = line.breakdown
        pre_discount = bd.total.amount + bd.discounts.amount
        subtotal += pre_discount
        total_discounts += bd.discounts.amount

    return QuoteTotals(
        subtotal=_money(subtotal),
        discounts=_money(total_discounts),
        total=_money(subtotal - total_discounts),
    )