"""
dependencies.py
---------------
Shared FastAPI dependencies.

Provides:
  - QuoteRepository backed by SQLite
  - Catalog loaded from catalog.json
  - Incompatibility and dependency rules (hardcoded for now)
"""

from __future__ import annotations

import json
from pathlib import Path

from cpq_domain.config_rules import DependencyRule, IncompatibilityRule
from cpq_domain.models import Catalog
from api.database import get_session
from api.repository import QuoteRepository

# ---------------------------------------------------------------------------
# Quote repository
# ---------------------------------------------------------------------------

def get_repository() -> QuoteRepository:
    """Return a QuoteRepository backed by a new SQLAlchemy session."""
    return QuoteRepository(get_session())


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def load_catalog() -> Catalog:
    """
    Load the product catalog from catalog.json.

    The file is resolved relative to this module's location so it works
    regardless of where uvicorn is launched from.
    """
    catalog_path = Path(__file__).parent / "catalog.json"
    with open(catalog_path, "r") as f:
        data = json.load(f)
    return Catalog(**data)


# Catalog is loaded once at startup and shared across all requests.
_catalog: Catalog = load_catalog()


def get_catalog() -> Catalog:
    """Return the shared product catalog."""
    return _catalog


# ---------------------------------------------------------------------------
# Business rules
# ---------------------------------------------------------------------------

# Incompatibility rules — SKUs that cannot be selected together.
INCOMPATIBILITY_RULES: list[IncompatibilityRule] = [
    IncompatibilityRule(
        sku_a="sku-support-standard",
        sku_b="sku-support-premium",
    ),
]

# Dependency rules — SKUs that require another SKU to be present.
DEPENDENCY_RULES: list[DependencyRule] = []


def get_incompatibility_rules() -> list[IncompatibilityRule]:
    return INCOMPATIBILITY_RULES


def get_dependency_rules() -> list[DependencyRule]:
    return DEPENDENCY_RULES