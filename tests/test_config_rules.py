"""
test_config_rules.py
--------------------
Unit tests for the NextGen CPQ Configuration Rules Engine (Week 2).

Run with: pytest tests/ -v
"""

import pytest

from cpq_domain.models import (
    AttributeDefinition,
    AttributeType,
    Catalog,
    Currency,
    Money,
    Product,
    QuoteLineSelection,
    SKU,
    Term,
)
from cpq_domain.config_rules import (
    DependencyRule,
    IncompatibilityRule,
    ValidationError,
    validate_addon_skus,
    validate_attribute_types,
    validate_dependencies,
    validate_incompatibilities,
    validate_quote_configuration,
    validate_required_attributes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_money(amount: float) -> Money:
    return Money(currency=Currency.USD, amount=amount)


def make_attr(
    key: str,
    attr_type: AttributeType,
    required: bool = False,
    enum_values=None,
) -> AttributeDefinition:
    return AttributeDefinition(
        key=key,
        label=key.capitalize(),
        type=attr_type,
        required=required,
        enum_values=enum_values,
    )


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


def make_selection(
    sku_id: str,
    selected_attributes=None,
    add_on_sku_ids=None,
) -> QuoteLineSelection:
    return QuoteLineSelection(
        sku_id=sku_id,
        quantity=1,
        term=Term.MONTHLY,
        selected_attributes=selected_attributes or {},
        add_on_sku_ids=add_on_sku_ids or [],
    )


def error_rules(errors) -> list[str]:
    """Extract just the rule names from a list of ValidationErrors."""
    return [e.rule for e in errors]


# ---------------------------------------------------------------------------
# validate_required_attributes
# ---------------------------------------------------------------------------

class TestValidateRequiredAttributes:

    def test_no_required_attributes_passes(self):
        sku = make_sku("sku-001")
        catalog = make_catalog(sku)
        selection = make_selection("sku-001")
        errors = validate_required_attributes(selection, catalog)
        assert errors == []

    def test_required_attribute_provided_passes(self):
        sku = make_sku("sku-002", attributes=[
            make_attr("plan", AttributeType.STRING, required=True)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-002", selected_attributes={"plan": "pro"})
        errors = validate_required_attributes(selection, catalog)
        assert errors == []

    def test_missing_required_attribute_fails(self):
        sku = make_sku("sku-003", attributes=[
            make_attr("plan", AttributeType.STRING, required=True)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-003")
        errors = validate_required_attributes(selection, catalog)
        assert len(errors) == 1
        assert "plan" in errors[0].message

    def test_multiple_missing_required_attributes(self):
        sku = make_sku("sku-004", attributes=[
            make_attr("plan", AttributeType.STRING, required=True),
            make_attr("region", AttributeType.STRING, required=True),
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-004")
        errors = validate_required_attributes(selection, catalog)
        assert len(errors) == 2

    def test_optional_attribute_not_provided_passes(self):
        sku = make_sku("sku-005", attributes=[
            make_attr("notes", AttributeType.STRING, required=False)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-005")
        errors = validate_required_attributes(selection, catalog)
        assert errors == []

    def test_sku_not_found_returns_error(self):
        catalog = make_catalog(make_sku("sku-X"))
        selection = make_selection("sku-MISSING")
        errors = validate_required_attributes(selection, catalog)
        assert len(errors) == 1
        assert "not found" in errors[0].message


# ---------------------------------------------------------------------------
# validate_attribute_types
# ---------------------------------------------------------------------------

class TestValidateAttributeTypes:

    def test_valid_string_attribute(self):
        sku = make_sku("sku-010", attributes=[
            make_attr("plan", AttributeType.STRING)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-010", selected_attributes={"plan": "pro"})
        assert validate_attribute_types(selection, catalog) == []

    def test_invalid_string_attribute(self):
        sku = make_sku("sku-011", attributes=[
            make_attr("plan", AttributeType.STRING)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-011", selected_attributes={"plan": 123})
        errors = validate_attribute_types(selection, catalog)
        assert len(errors) == 1
        assert "plan" in errors[0].message

    def test_valid_number_attribute(self):
        sku = make_sku("sku-012", attributes=[
            make_attr("seats", AttributeType.NUMBER)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-012", selected_attributes={"seats": 10})
        assert validate_attribute_types(selection, catalog) == []

    def test_invalid_number_attribute(self):
        sku = make_sku("sku-013", attributes=[
            make_attr("seats", AttributeType.NUMBER)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-013", selected_attributes={"seats": "ten"})
        errors = validate_attribute_types(selection, catalog)
        assert len(errors) == 1

    def test_boolean_treated_as_number_fails(self):
        """bool is a subclass of int in Python — must be explicitly rejected."""
        sku = make_sku("sku-014", attributes=[
            make_attr("seats", AttributeType.NUMBER)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-014", selected_attributes={"seats": True})
        errors = validate_attribute_types(selection, catalog)
        assert len(errors) == 1

    def test_valid_boolean_attribute(self):
        sku = make_sku("sku-015", attributes=[
            make_attr("active", AttributeType.BOOLEAN)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-015", selected_attributes={"active": True})
        assert validate_attribute_types(selection, catalog) == []

    def test_valid_enum_attribute(self):
        sku = make_sku("sku-016", attributes=[
            make_attr("tier", AttributeType.ENUM, enum_values=["basic", "pro", "enterprise"])
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-016", selected_attributes={"tier": "pro"})
        assert validate_attribute_types(selection, catalog) == []

    def test_invalid_enum_value(self):
        sku = make_sku("sku-017", attributes=[
            make_attr("tier", AttributeType.ENUM, enum_values=["basic", "pro"])
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-017", selected_attributes={"tier": "ultimate"})
        errors = validate_attribute_types(selection, catalog)
        assert len(errors) == 1
        assert "tier" in errors[0].message


# ---------------------------------------------------------------------------
# validate_addon_skus
# ---------------------------------------------------------------------------

class TestValidateAddonSkus:

    def test_no_addons_passes(self):
        catalog = make_catalog(make_sku("sku-020"))
        selection = make_selection("sku-020")
        assert validate_addon_skus(selection, catalog) == []

    def test_valid_addon_passes(self):
        catalog = make_catalog(make_sku("sku-021"), make_sku("sku-addon-001"))
        selection = make_selection("sku-021", add_on_sku_ids=["sku-addon-001"])
        assert validate_addon_skus(selection, catalog) == []

    def test_invalid_addon_fails(self):
        catalog = make_catalog(make_sku("sku-022"))
        selection = make_selection("sku-022", add_on_sku_ids=["sku-nonexistent"])
        errors = validate_addon_skus(selection, catalog)
        assert len(errors) == 1
        assert "sku-nonexistent" in errors[0].message

    def test_multiple_invalid_addons(self):
        catalog = make_catalog(make_sku("sku-023"))
        selection = make_selection(
            "sku-023", add_on_sku_ids=["sku-bad-1", "sku-bad-2"]
        )
        errors = validate_addon_skus(selection, catalog)
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# validate_incompatibilities
# ---------------------------------------------------------------------------

class TestValidateIncompatibilities:

    def test_no_incompatible_skus_passes(self):
        selections = [make_selection("sku-A"), make_selection("sku-B")]
        rules = [IncompatibilityRule(sku_a="sku-X", sku_b="sku-Y")]
        assert validate_incompatibilities(selections, rules) == []

    def test_incompatible_pair_detected(self):
        selections = [make_selection("sku-A"), make_selection("sku-B")]
        rules = [IncompatibilityRule(sku_a="sku-A", sku_b="sku-B")]
        errors = validate_incompatibilities(selections, rules)
        assert len(errors) == 1
        assert "sku-A" in errors[0].message
        assert "sku-B" in errors[0].message

    def test_only_one_of_pair_selected_passes(self):
        selections = [make_selection("sku-A")]
        rules = [IncompatibilityRule(sku_a="sku-A", sku_b="sku-B")]
        assert validate_incompatibilities(selections, rules) == []

    def test_multiple_incompatible_pairs(self):
        selections = [
            make_selection("sku-A"),
            make_selection("sku-B"),
            make_selection("sku-C"),
        ]
        rules = [
            IncompatibilityRule(sku_a="sku-A", sku_b="sku-B"),
            IncompatibilityRule(sku_a="sku-A", sku_b="sku-C"),
        ]
        errors = validate_incompatibilities(selections, rules)
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# validate_dependencies
# ---------------------------------------------------------------------------

class TestValidateDependencies:

    def test_dependency_satisfied_passes(self):
        selections = [make_selection("sku-addon"), make_selection("sku-base")]
        rules = [DependencyRule(required_sku="sku-addon", depends_on="sku-base")]
        assert validate_dependencies(selections, rules) == []

    def test_dependency_not_satisfied_fails(self):
        selections = [make_selection("sku-addon")]
        rules = [DependencyRule(required_sku="sku-addon", depends_on="sku-base")]
        errors = validate_dependencies(selections, rules)
        assert len(errors) == 1
        assert "sku-addon" in errors[0].message
        assert "sku-base" in errors[0].message

    def test_dependency_not_triggered_if_sku_absent(self):
        selections = [make_selection("sku-other")]
        rules = [DependencyRule(required_sku="sku-addon", depends_on="sku-base")]
        assert validate_dependencies(selections, rules) == []

    def test_multiple_unsatisfied_dependencies(self):
        selections = [make_selection("sku-A"), make_selection("sku-B")]
        rules = [
            DependencyRule(required_sku="sku-A", depends_on="sku-X"),
            DependencyRule(required_sku="sku-B", depends_on="sku-Y"),
        ]
        errors = validate_dependencies(selections, rules)
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# validate_quote_configuration (full integration)
# ---------------------------------------------------------------------------

class TestValidateQuoteConfiguration:

    def test_fully_valid_configuration(self):
        sku = make_sku("sku-full", attributes=[
            make_attr("plan", AttributeType.STRING, required=True)
        ])
        catalog = make_catalog(sku)
        selection = make_selection("sku-full", selected_attributes={"plan": "pro"})
        errors = validate_quote_configuration([selection], catalog)
        assert errors == []

    def test_collects_all_errors_across_rules(self):
        """All violations are returned at once, not just the first."""
        sku = make_sku("sku-multi", attributes=[
            make_attr("plan", AttributeType.STRING, required=True),
            make_attr("seats", AttributeType.NUMBER, required=True),
        ])
        catalog = make_catalog(sku, make_sku("sku-other"))
        # Missing both required attributes
        selection = make_selection("sku-multi")
        errors = validate_quote_configuration([selection], catalog)
        assert len(errors) >= 2

    def test_incompatibility_caught_in_full_validation(self):
        catalog = make_catalog(make_sku("sku-A"), make_sku("sku-B"))
        selections = [make_selection("sku-A"), make_selection("sku-B")]
        rules = [IncompatibilityRule(sku_a="sku-A", sku_b="sku-B")]
        errors = validate_quote_configuration(
            selections, catalog, incompatibility_rules=rules
        )
        assert any(e.rule == "incompatibility" for e in errors)

    def test_dependency_caught_in_full_validation(self):
        catalog = make_catalog(make_sku("sku-addon"), make_sku("sku-base"))
        selections = [make_selection("sku-addon")]
        rules = [DependencyRule(required_sku="sku-addon", depends_on="sku-base")]
        errors = validate_quote_configuration(
            selections, catalog, dependency_rules=rules
        )
        assert any(e.rule == "dependency" for e in errors)

    def test_empty_selections_passes(self):
        catalog = make_catalog(make_sku("sku-Z"))
        errors = validate_quote_configuration([], catalog)
        assert errors == []