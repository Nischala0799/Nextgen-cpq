"""
dependencies.py
---------------
Shared FastAPI dependencies.

Provides:
  - In-memory quote store
  - Catalog loaded from catalog.json
  - Incompatibility and dependency rules (hardcoded for now)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from cpq_domain.config_rules import DependencyRule, IncompatibilityRule
from cpq_domain.models import Catalog, Quote

# ---------------------------------------------------------------------------
# In-memory quote store
# ---------------------------------------------------------------------------

# Quotes are stored as a dict of quote_id -> Quote.
# Resets on every server restart — Phase 2 will introduce persistence.
_quote_store: Dict[str, Quote] = {}


def get_quote_store() -> Dict[str, Quote]:
    """Return the shared in-memory quote store."""
    return _quote_store


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