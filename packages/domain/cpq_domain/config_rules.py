"""
config_rules.py
---------------
NextGen CPQ – Configuration Rules Engine 

Responsibilities:
  - Validate that all required SKU attributes are provided
  - Validate that attribute values match their expected type
  - Validate that selected add-on SKU IDs exist in the catalog
  - Validate that incompatible product pairs are not selected together
  - Validate that product dependencies are satisfied

All functions are pure and return a list of validation errors.
An empty list means the configuration is valid.
No exceptions are raised for business rule violations —
errors are collected and returned all at once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set

from cpq_domain.models import (
    AttributeType,
    Catalog,
    QuoteLineSelection,
)


# ---------------------------------------------------------------------------
# Validation Error
# ---------------------------------------------------------------------------

@dataclass
class ValidationError:
    """
    Represents a single configuration rule violation.

    Attributes:
        rule:    The name of the rule that was violated.
        message: A human-readable description of the violation.
    """
    rule: str
    message: str


# ---------------------------------------------------------------------------
# Incompatibility + Dependency Rule Definitions
# ---------------------------------------------------------------------------

@dataclass
class IncompatibilityRule:
    """
    Defines a pair of SKU IDs that cannot be selected together.

    Example:
        IncompatibilityRule(sku_a="sku-basic", sku_b="sku-enterprise")
        → A quote line cannot contain both basic and enterprise SKUs.
    """
    sku_a: str
    sku_b: str


@dataclass
class DependencyRule:
    """
    Defines that selecting one SKU requires another SKU to also be selected.

    Example:
        DependencyRule(required_sku="sku-addon-sso", depends_on="sku-enterprise")
        → SSO add-on can only be selected if the enterprise SKU is also present.
    """
    required_sku: str
    depends_on: str


# ---------------------------------------------------------------------------
# Rule 1: Required Attributes
# ---------------------------------------------------------------------------

def validate_required_attributes(
    selection: QuoteLineSelection,
    catalog: Catalog,
) -> List[ValidationError]:
    """
    Check that all required attributes for the selected SKU are provided.

    Looks up the SKU in the catalog, finds all AttributeDefinitions
    where required=True, and verifies each has a non-empty value
    in selection.selected_attributes.

    Returns:
        List of ValidationError for each missing required attribute.
    """
    errors: List[ValidationError] = []

    sku = _find_sku(catalog, selection.sku_id)
    if sku is None:
        return [ValidationError(
            rule="required_attributes",
            message=f"SKU '{selection.sku_id}' not found in catalog.",
        )]

    for attr_def in sku.attributes:
        if not attr_def.required:
            continue

        value = selection.selected_attributes.get(attr_def.key)

        if value is None:
            errors.append(ValidationError(
                rule="required_attributes",
                message=(
                    f"SKU '{selection.sku_id}': required attribute "
                    f"'{attr_def.key}' is missing."
                ),
            ))

    return errors


# ---------------------------------------------------------------------------
# Rule 2: Attribute Type Validation
# ---------------------------------------------------------------------------

def validate_attribute_types(
    selection: QuoteLineSelection,
    catalog: Catalog,
) -> List[ValidationError]:
    """
    Check that provided attribute values match their defined AttributeType.

    Only validates attributes that are actually provided in selected_attributes.
    Missing required attributes are handled by validate_required_attributes.

    Type rules:
        STRING  → value must be a str
        NUMBER  → value must be an int or float
        BOOLEAN → value must be a bool
        ENUM    → value must be a str present in attr_def.enum_values

    Returns:
        List of ValidationError for each type mismatch.
    """
    errors: List[ValidationError] = []

    sku = _find_sku(catalog, selection.sku_id)
    if sku is None:
        return []  # SKU existence is validated elsewhere

    for attr_def in sku.attributes:
        value = selection.selected_attributes.get(attr_def.key)
        if value is None:
            continue  # not provided — handled by required_attributes rule

        valid = True

        if attr_def.type == AttributeType.STRING:
            valid = isinstance(value, str)

        elif attr_def.type == AttributeType.NUMBER:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)

        elif attr_def.type == AttributeType.BOOLEAN:
            valid = isinstance(value, bool)

        elif attr_def.type == AttributeType.ENUM:
            allowed = attr_def.enum_values or []
            valid = isinstance(value, str) and value in allowed

        if not valid:
            errors.append(ValidationError(
                rule="attribute_type",
                message=(
                    f"SKU '{selection.sku_id}': attribute '{attr_def.key}' "
                    f"has invalid value '{value}' for type '{attr_def.type}'."
                ),
            ))

    return errors


# ---------------------------------------------------------------------------
# Rule 3: Add-on SKU Existence
# ---------------------------------------------------------------------------

def validate_addon_skus(
    selection: QuoteLineSelection,
    catalog: Catalog,
) -> List[ValidationError]:
    """
    Check that all selected add-on SKU IDs exist in the catalog.

    Returns:
        List of ValidationError for each unrecognised add-on SKU ID.
    """
    errors: List[ValidationError] = []
    all_sku_ids = _all_sku_ids(catalog)

    for addon_sku_id in selection.add_on_sku_ids:
        if addon_sku_id not in all_sku_ids:
            errors.append(ValidationError(
                rule="addon_sku_existence",
                message=(
                    f"Add-on SKU '{addon_sku_id}' does not exist in the catalog."
                ),
            ))

    return errors


# ---------------------------------------------------------------------------
# Rule 4: Incompatibility Rules
# ---------------------------------------------------------------------------

def validate_incompatibilities(
    selections: List[QuoteLineSelection],
    rules: List[IncompatibilityRule],
) -> List[ValidationError]:
    """
    Check that no two incompatible SKUs are selected in the same quote.

    Args:
        selections: All line selections in the current quote.
        rules:      List of IncompatibilityRule pairs to enforce.

    Returns:
        List of ValidationError for each incompatible pair found.
    """
    errors: List[ValidationError] = []
    selected_sku_ids: Set[str] = {s.sku_id for s in selections}

    for rule in rules:
        if rule.sku_a in selected_sku_ids and rule.sku_b in selected_sku_ids:
            errors.append(ValidationError(
                rule="incompatibility",
                message=(
                    f"SKUs '{rule.sku_a}' and '{rule.sku_b}' "
                    f"cannot be selected together."
                ),
            ))

    return errors


# ---------------------------------------------------------------------------
# Rule 5: Dependency Rules
# ---------------------------------------------------------------------------

def validate_dependencies(
    selections: List[QuoteLineSelection],
    rules: List[DependencyRule],
) -> List[ValidationError]:
    """
    Check that all SKU dependencies are satisfied in the quote.

    If a selection includes required_sku, then depends_on must also
    be present somewhere in the quote selections.

    Args:
        selections: All line selections in the current quote.
        rules:      List of DependencyRule definitions to enforce.

    Returns:
        List of ValidationError for each unsatisfied dependency.
    """
    errors: List[ValidationError] = []
    selected_sku_ids: Set[str] = {s.sku_id for s in selections}

    for rule in rules:
        if rule.required_sku in selected_sku_ids:
            if rule.depends_on not in selected_sku_ids:
                errors.append(ValidationError(
                    rule="dependency",
                    message=(
                        f"SKU '{rule.required_sku}' requires "
                        f"'{rule.depends_on}' to also be selected."
                    ),
                ))

    return errors


# ---------------------------------------------------------------------------
# Top-level validator
# ---------------------------------------------------------------------------

def validate_quote_configuration(
    selections: List[QuoteLineSelection],
    catalog: Catalog,
    incompatibility_rules: List[IncompatibilityRule] | None = None,
    dependency_rules: List[DependencyRule] | None = None,
) -> List[ValidationError]:
    """
    Run all configuration rules against the full set of quote line selections.

    Collects and returns ALL violations across all rules.
    An empty list means the configuration is fully valid.

    Args:
        selections:            All line selections in the quote.
        catalog:               Product catalog for SKU/attribute lookups.
        incompatibility_rules: Optional list of incompatibility rules.
        dependency_rules:      Optional list of dependency rules.

    Returns:
        A flat list of all ValidationErrors found. Empty = valid.
    """
    incompatibility_rules = incompatibility_rules or []
    dependency_rules = dependency_rules or []

    errors: List[ValidationError] = []

    # Line-level rules (run per selection)
    for selection in selections:
        errors.extend(validate_required_attributes(selection, catalog))
        errors.extend(validate_attribute_types(selection, catalog))
        errors.extend(validate_addon_skus(selection, catalog))

    # Quote-level rules (run across all selections)
    errors.extend(validate_incompatibilities(selections, incompatibility_rules))
    errors.extend(validate_dependencies(selections, dependency_rules))

    return errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_sku(catalog: Catalog, sku_id: str):
    """Return the SKU with the given sku_id, or None if not found."""
    for product in catalog.products:
        for sku in product.skus:
            if sku.sku_id == sku_id:
                return sku
    return None


def _all_sku_ids(catalog: Catalog) -> Set[str]:
    """Return a set of all SKU IDs across all products in the catalog."""
    return {
        sku.sku_id
        for product in catalog.products
        for sku in product.skus
    }