"""
routers/quotes.py
-----------------
FastAPI router for all quote-related endpoints.

Endpoints:
  POST   /quotes                              Create a new quote
  GET    /quotes/{quote_id}                   Get a quote by ID
  POST   /quotes/{quote_id}/lines             Add a line to a quote
  DELETE /quotes/{quote_id}/lines/{line_id}   Remove a line from a quote
  POST   /quotes/{quote_id}/finalize          Finalize a quote
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cpq_domain.models import (
    Discount,
    DiscountType,
    Money,
    Currency,
    Quote,
    QuoteLineSelection,
    Term,
)
from cpq_domain.quote_service import (
    add_line,
    create_quote,
    finalize_quote,
    remove_line,
)
from api.dependencies import (
    get_catalog,
    get_dependency_rules,
    get_incompatibility_rules,
    get_repository,
)

router = APIRouter(prefix="/quotes", tags=["quotes"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateQuoteRequest(BaseModel):
    customer_id: Optional[str] = None


class AddLineRequest(BaseModel):
    sku_id: str
    quantity: int = 1
    term: Term = Term.MONTHLY
    selected_attributes: Dict[str, object] = {}
    add_on_sku_ids: List[str] = []
    discount_amount: Optional[float] = None  # Optional flat discount in USD


class ValidationErrorResponse(BaseModel):
    rule: str
    message: str


class QuoteResponse(BaseModel):
    quote_id: str
    customer_id: Optional[str]
    status: str
    active_version: int
    total: float
    subtotal: float
    discounts: float
    line_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quote_to_response(quote: Quote) -> QuoteResponse:
    """Convert a Quote domain object to a QuoteResponse."""
    active = next(
        (v for v in quote.versions if v.version == quote.active_version),
        None,
    )
    totals = active.totals if active else None

    return QuoteResponse(
        quote_id=quote.quote_id,
        customer_id=quote.customer_id,
        status=quote.status.value,
        active_version=quote.active_version,
        total=totals.total.amount if totals else 0.0,
        subtotal=totals.subtotal.amount if totals else 0.0,
        discounts=totals.discounts.amount if totals else 0.0,
        line_count=len(active.lines) if active else 0,
    )


def _get_quote_or_404(quote_id: str) -> Quote:
    """Look up a quote by ID or raise a 404."""
    quote = get_repository().get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote '{quote_id}' not found.")
    return quote


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def create_new_quote(request: CreateQuoteRequest) -> QuoteResponse:
    """
    Create a new empty quote in DRAFT status.
    """
    quote = create_quote(customer_id=request.customer_id)
    get_repository().save(quote)
    return _quote_to_response(quote)


@router.get("/{quote_id}")
def get_quote(quote_id: str) -> QuoteResponse:
    """
    Retrieve a quote by its ID.
    """
    quote = _get_quote_or_404(quote_id)
    return _quote_to_response(quote)


@router.post("/{quote_id}/lines", status_code=200)
def add_line_to_quote(quote_id: str, request: AddLineRequest) -> QuoteResponse:
    """
    Add a line item to a quote.

    Runs configuration validation first. If any rules are violated,
    returns 422 with the full list of errors.
    """
    quote = _get_quote_or_404(quote_id)

    selection = QuoteLineSelection(
        sku_id=request.sku_id,
        quantity=request.quantity,
        term=request.term,
        selected_attributes=request.selected_attributes,
        add_on_sku_ids=request.add_on_sku_ids,
    )

    discounts = []
    if request.discount_amount and request.discount_amount > 0:
        discounts.append(Discount(
            type=DiscountType.MANUAL,
            amount=Money(currency=Currency.USD, amount=request.discount_amount),
            description="Manual discount",
        ))

    result = add_line(
        quote=quote,
        selection=selection,
        catalog=get_catalog(),
        discounts=discounts,
        incompatibility_rules=get_incompatibility_rules(),
        dependency_rules=get_dependency_rules(),
    )

    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=[{"rule": e.rule, "message": e.message} for e in result.errors],
        )

    get_repository().save(result.quote)
    return _quote_to_response(result.quote)


@router.delete("/{quote_id}/lines/{line_id}", status_code=200)
def remove_line_from_quote(quote_id: str, line_id: str) -> QuoteResponse:
    """
    Remove a line item from a quote by its line ID.
    """
    quote = _get_quote_or_404(quote_id)

    result = remove_line(quote=quote, line_id=line_id)

    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=[{"rule": e.rule, "message": e.message} for e in result.errors],
        )

    get_repository().save(result.quote)
    return _quote_to_response(result.quote)


@router.post("/{quote_id}/finalize", status_code=200)
def finalize(quote_id: str) -> QuoteResponse:
    """
    Finalize a quote. Once finalized, no further modifications are allowed.
    """
    quote = _get_quote_or_404(quote_id)

    result = finalize_quote(quote=quote)

    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=[{"rule": e.rule, "message": e.message} for e in result.errors],
        )

    get_repository().save(result.quote)
    return _quote_to_response(result.quote)