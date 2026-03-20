from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


# --------------------
# Core Enums
# --------------------

class Term(str, Enum):
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"


class Currency(str, Enum):
    USD = "USD"


# --------------------
# Value Objects
# --------------------

class Money(BaseModel):
    currency: Currency = Currency.USD
    amount: float = Field(
        ...,
        ge=0,
        description="Monetary amount. Float for now; switch to Decimal/cents later if needed."
    )


# --------------------
# Product Configuration
# --------------------

class AttributeType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"


class AttributeDefinition(BaseModel):
    key: str
    label: str
    type: AttributeType
    required: bool = False
    enum_values: Optional[List[str]] = None


class SKU(BaseModel):
    sku_id: str
    name: str
    base_price: Money
    attributes: List[AttributeDefinition] = Field(default_factory=list)


class Product(BaseModel):
    product_id: str
    name: str
    skus: List[SKU]
    add_on_product_ids: List[str] = Field(default_factory=list)


class Bundle(BaseModel):
    bundle_id: str
    name: str
    included_product_ids: List[str]


class Catalog(BaseModel):
    products: List[Product] = Field(default_factory=list)
    bundles: List[Bundle] = Field(default_factory=list)


# --------------------
# Attribute Selections
# --------------------

AttributeValue = Union[str, int, float, bool]
AttributeSelections = Dict[str, AttributeValue]


# --------------------
# Quote + Pricing Models
# --------------------

class DiscountType(str, Enum):
    MANUAL = "MANUAL"
    RULE_BASED = "RULE_BASED"


class Discount(BaseModel):
    discount_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: DiscountType
    description: Optional[str] = None
    amount: Money = Field(..., description="Absolute discount amount in currency value (not percentage).")


class PriceBreakdown(BaseModel):
    """
    Line-level pricing components. These are placeholders initially; the pricing engine
    will populate them later.
    """
    base: Money
    term_adjustment: Money
    quantity_adjustment: Money
    discounts: Money
    total: Money


class QuoteLineSelection(BaseModel):
    """
    The user's configuration choices for a single quoted line item.
    """
    line_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku_id: str
    quantity: int = Field(..., ge=1)
    term: Term
    selected_attributes: AttributeSelections = Field(default_factory=dict)
    add_on_sku_ids: List[str] = Field(default_factory=list)


class QuoteLine(BaseModel):
    """
    A priced quote line: selection + breakdown + applied discounts.
    """
    selection: QuoteLineSelection
    breakdown: PriceBreakdown
    applied_discounts: List[Discount] = Field(default_factory=list)


class QuoteTotals(BaseModel):
    """
    Quote-level totals for a given version.
    """
    subtotal: Money
    discounts: Money
    total: Money


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class QuoteVersion(BaseModel):
    """
    Immutable snapshot of quote lines + totals at a point in time.
    """
    version: int = Field(..., ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lines: List[QuoteLine] = Field(default_factory=list)
    totals: QuoteTotals


class Quote(BaseModel):
    """
    Quote container with version history.
    """
    quote_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: Optional[str] = None
    status: QuoteStatus = QuoteStatus.DRAFT
    active_version: int = 1
    versions: List[QuoteVersion] = Field(default_factory=list)


def new_quote(customer_id: Optional[str] = None) -> Quote:
    """
    Create a new Quote with an initial empty version (version=1) and zero totals.
    """
    zero = Money(currency=Currency.USD, amount=0)

    initial_totals = QuoteTotals(
        subtotal=zero,
        discounts=zero,
        total=zero,
    )

    initial_version = QuoteVersion(
        version=1,
        lines=[],
        totals=initial_totals,
    )

    return Quote(
        customer_id=customer_id,
        active_version=1,
        versions=[initial_version],
    )
