"""
quote_service.py
----------------
NextGen CPQ – Quote Service 

Responsibilities:
  - Create new quotes
  - Add line items to a quote (validate config → price → store)
  - Remove line items from a quote
  - Finalize a quote
  - Maintain immutable version history on every mutation

The quote service is the single entry point for all quote mutations.
It orchestrates the config rules engine and pricing engine,
keeping those layers cleanly separated from each other.

All functions are pure — they accept a Quote and return a new Quote.
The original is never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cpq_domain.config_rules import (
    DependencyRule,
    IncompatibilityRule,
    ValidationError,
    validate_quote_configuration,
)
from cpq_domain.models import (
    Catalog,
    Discount,
    Quote,
    QuoteLine,
    QuoteLineSelection,
    QuoteStatus,
    QuoteTotals,
    QuoteVersion,
    new_quote,
)
from cpq_domain.pricing_engine import calculate_totals, price_line


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class QuoteResult:
    """
    Returned by every quote service operation.

    Attributes:
        ok:     True if the operation succeeded, False if it was rejected.
        quote:  The updated Quote (if ok=True) or the unchanged Quote (if ok=False).
        errors: List of ValidationErrors explaining why the operation was rejected.
    """
    ok: bool
    quote: Quote
    errors: List[ValidationError]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_quote(customer_id: str | None = None) -> Quote:
    """
    Create a new empty quote with version 1 and zero totals.

    Args:
        customer_id: Optional identifier for the customer this quote is for.

    Returns:
        A fresh Quote in DRAFT status.
    """
    return new_quote(customer_id=customer_id)


# ---------------------------------------------------------------------------
# Add line
# ---------------------------------------------------------------------------

def add_line(
    quote: Quote,
    selection: QuoteLineSelection,
    catalog: Catalog,
    discounts: List[Discount] | None = None,
    incompatibility_rules: List[IncompatibilityRule] | None = None,
    dependency_rules: List[DependencyRule] | None = None,
) -> QuoteResult:
    """
    Validate and add a new line item to the quote.

    Flow:
      1. Reject if quote is already FINALIZED
      2. Get current lines from the active version
      3. Run configuration validation across all lines including the new one
      4. If validation fails, return errors and leave the quote unchanged
      5. Price the new line
      6. Append to lines and recalculate totals
      7. Create a new QuoteVersion and return updated Quote

    Args:
        quote:                The current quote to add a line to.
        selection:            The user's product configuration for the new line.
        catalog:              Product catalog for SKU lookups.
        discounts:            Optional discounts to apply to this line.
        incompatibility_rules: Optional incompatibility rules to enforce.
        dependency_rules:     Optional dependency rules to enforce.

    Returns:
        QuoteResult with ok=True and updated quote, or ok=False with errors.
    """
    discounts = discounts or []
    incompatibility_rules = incompatibility_rules or []
    dependency_rules = dependency_rules or []

    # Step 1: Reject if finalized
    if quote.status == QuoteStatus.FINALIZED:
        return QuoteResult(
            ok=False,
            quote=quote,
            errors=[ValidationError(
                rule="quote_status",
                message="Cannot modify a finalized quote.",
            )],
        )

    # Step 2: Get current selections from active version
    current_lines = _get_active_lines(quote)
    current_selections = [line.selection for line in current_lines]
    all_selections = current_selections + [selection]

    # Step 3: Validate configuration
    errors = validate_quote_configuration(
        selections=all_selections,
        catalog=catalog,
        incompatibility_rules=incompatibility_rules,
        dependency_rules=dependency_rules,
    )

    # Step 4: Reject if invalid
    if errors:
        return QuoteResult(ok=False, quote=quote, errors=errors)

    # Step 5: Price the new line
    priced_line = price_line(selection, catalog, discounts=discounts)

    # Step 6: Build updated lines and totals
    updated_lines = current_lines + [priced_line]
    updated_totals = calculate_totals(updated_lines)

    # Step 7: Create new version and return
    updated_quote = _create_new_version(quote, updated_lines, updated_totals)
    return QuoteResult(ok=True, quote=updated_quote, errors=[])


# ---------------------------------------------------------------------------
# Remove line
# ---------------------------------------------------------------------------

def remove_line(
    quote: Quote,
    line_id: str,
) -> QuoteResult:
    """
    Remove a line item from the quote by its line_id.

    Flow:
      1. Reject if quote is FINALIZED
      2. Find the line in the active version
      3. If not found, return an error
      4. Remove the line, recalculate totals, create new version

    Args:
        quote:   The current quote.
        line_id: The line_id of the QuoteLineSelection to remove.

    Returns:
        QuoteResult with ok=True and updated quote, or ok=False with errors.
    """
    # Step 1: Reject if finalized
    if quote.status == QuoteStatus.FINALIZED:
        return QuoteResult(
            ok=False,
            quote=quote,
            errors=[ValidationError(
                rule="quote_status",
                message="Cannot modify a finalized quote.",
            )],
        )

    # Step 2 & 3: Find and remove the line
    current_lines = _get_active_lines(quote)
    updated_lines = [l for l in current_lines if l.selection.line_id != line_id]

    if len(updated_lines) == len(current_lines):
        return QuoteResult(
            ok=False,
            quote=quote,
            errors=[ValidationError(
                rule="line_not_found",
                message=f"Line '{line_id}' not found in active quote version.",
            )],
        )

    # Step 4: Recalculate totals and create new version
    updated_totals = calculate_totals(updated_lines)
    updated_quote = _create_new_version(quote, updated_lines, updated_totals)
    return QuoteResult(ok=True, quote=updated_quote, errors=[])


# ---------------------------------------------------------------------------
# Finalize
# ---------------------------------------------------------------------------

def finalize_quote(quote: Quote) -> QuoteResult:
    """
    Mark the quote as FINALIZED.

    A finalized quote cannot be modified further.
    Cannot finalize an already finalized quote.
    Cannot finalize an empty quote (no lines).

    Args:
        quote: The current quote.

    Returns:
        QuoteResult with ok=True and finalized quote, or ok=False with errors.
    """
    if quote.status == QuoteStatus.FINALIZED:
        return QuoteResult(
            ok=False,
            quote=quote,
            errors=[ValidationError(
                rule="quote_status",
                message="Quote is already finalized.",
            )],
        )

    current_lines = _get_active_lines(quote)
    if not current_lines:
        return QuoteResult(
            ok=False,
            quote=quote,
            errors=[ValidationError(
                rule="empty_quote",
                message="Cannot finalize an empty quote with no line items.",
            )],
        )

    finalized_quote = quote.model_copy(update={"status": QuoteStatus.FINALIZED})
    return QuoteResult(ok=True, quote=finalized_quote, errors=[])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_active_lines(quote: Quote) -> List[QuoteLine]:
    """Return the lines from the currently active quote version."""
    for version in quote.versions:
        if version.version == quote.active_version:
            return list(version.lines)
    return []


def _get_active_totals(quote: Quote) -> QuoteTotals:
    """Return the totals from the currently active quote version."""
    for version in quote.versions:
        if version.version == quote.active_version:
            return version.totals
    return calculate_totals([])


def _create_new_version(
    quote: Quote,
    lines: List[QuoteLine],
    totals: QuoteTotals,
) -> Quote:
    """
    Create a new QuoteVersion and return an updated Quote.

    The new version number is one higher than the current active version.
    The original quote's versions list is preserved (immutable history).
    """
    new_version_number = quote.active_version + 1

    new_version = QuoteVersion(
        version=new_version_number,
        lines=lines,
        totals=totals,
    )

    updated_versions = list(quote.versions) + [new_version]

    return quote.model_copy(update={
        "active_version": new_version_number,
        "versions": updated_versions,
    })