"""Tests for Tiferet-Ly Production Rule Mappers"""

# *** imports

# ** core
from typing import Any

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.production import SimpleProductionRule
from tiferet_ly.mappers.core import (
    expand_keyed_entries,
    wrap_keyed_entries,
)
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    ProductionRuleAggregate,
    ProductionRuleConfigObject,
    SimpleProductionRuleAggregate,
)

# *** constants

# ** constant: simple_core
SIMPLE_CORE = SimpleProductionRuleAggregate(
    name='expression',
    grammar_id='core',
    spec='expression : term',
)

# ** constant: simple_domain_extra
SIMPLE_DOMAIN_EXTRA = SimpleProductionRuleAggregate(
    name='expression',
    grammar_id='domain_extra',
    spec='expression : attr_decl',
)

# ** constant: complex_core
COMPLEX_CORE = ComplexProductionRuleAggregate(
    name='expression',
    grammar_id='core',
    spec='expression : expression PLUS term',
    action='p[0] = p[1] + p[3]',
)

# *** functions

# ** function: assert_rule_fields_equal
def assert_rule_fields_equal(left: Any, right: Any) -> None:
    '''
    Assert two production rules equal on every declared field.

    :param left: The left-hand rule.
    :type left: Any
    :param right: The right-hand rule.
    :type right: Any
    :return: None
    :rtype: None
    '''

    # Compare type and field values.
    assert type(left) is type(right)
    assert left.model_dump() == right.model_dump()


# ** function: round_trip
def round_trip(rule: Any) -> Any:
    '''
    Round-trip a production rule through ConfigObject serialization.

    :param rule: The source production rule.
    :type rule: Any
    :return: The reconstructed rule from .map().
    :rtype: Any
    '''

    # Serialize through to_data and back through model_validate/map.
    data = ProductionRuleConfigObject.from_model(rule).to_primitive(
        'to_data',
        exclude=set(),
    )
    return ProductionRuleConfigObject.model_validate(data).map()

# *** tests

# ** test: production_rule_aggregate_exists
def test_production_rule_aggregate_exists() -> None:
    '''
    Test that ProductionRuleAggregate exists with Aggregate mutators.
    '''

    # Assert the named artifact exposes shared NamedRuleAggregate mutators.
    assert 'rename' in dir(ProductionRuleAggregate)
    assert 'reassign_grammar' in dir(ProductionRuleAggregate)
    assert 'set_attribute' in dir(ProductionRuleAggregate)


# ** test: production_round_trip_simple_and_complex_cross_grammar
def test_production_round_trip_simple_and_complex_cross_grammar() -> None:
    '''
    Test round-tripping Simple and Complex production rules across two
    grammar_id values that share a name.
    '''

    # Round-trip each rule and assert field equality.
    assert_rule_fields_equal(round_trip(SIMPLE_CORE), SIMPLE_CORE)
    assert_rule_fields_equal(round_trip(SIMPLE_DOMAIN_EXTRA), SIMPLE_DOMAIN_EXTRA)
    assert_rule_fields_equal(round_trip(COMPLEX_CORE), COMPLEX_CORE)

    # Same-named different-grammar_id entries coexist without raising.
    assert SIMPLE_CORE.name == SIMPLE_DOMAIN_EXTRA.name
    assert SIMPLE_CORE.grammar_id != SIMPLE_DOMAIN_EXTRA.grammar_id


# ** test: production_serialized_sequence_of_single_key_mappings
def test_production_serialized_sequence_of_single_key_mappings() -> None:
    '''
    Test serialized production_rules: matches the sequence-of-single-key-
    mappings format exactly against a literal expected dict.
    '''

    # Build flat dicts with name present, then wrap for YAML shape.
    flats = [
        ProductionRuleConfigObject.from_model(rule).to_primitive('to_data', exclude=set())
        for rule in (COMPLEX_CORE, SIMPLE_CORE, SIMPLE_DOMAIN_EXTRA)
    ]
    wrapped = wrap_keyed_entries(flats, key_field='name')

    # Assert the exact sequence-of-single-key-mappings shape.
    assert wrapped == [
        {
            'expression': {
                'grammar_id': 'core',
                'spec': 'expression : expression PLUS term',
                'action': 'p[0] = p[1] + p[3]',
            },
        },
        {
            'expression': {
                'grammar_id': 'core',
                'spec': 'expression : term',
            },
        },
        {
            'expression': {
                'grammar_id': 'domain_extra',
                'spec': 'expression : attr_decl',
            },
        },
    ]

    # Simple rules must not carry an action key.
    assert 'action' not in wrapped[1]['expression']
    assert 'action' not in wrapped[2]['expression']

    # Expand round-trips back to the same flat dicts.
    assert expand_keyed_entries(wrapped, key_field='name') == flats


# ** test: production_map_raises_same_domain_error_on_corrupted_invariant
def test_production_map_raises_same_domain_error_on_corrupted_invariant() -> None:
    '''
    Test that a corrupted config object raises the same domain-level
    ValidationError at .map() time that RFP-001 construction would raise.
    '''

    # Build a config object that bypasses required-field validation.
    corrupted = ProductionRuleConfigObject.model_construct(
        name='expression',
        grammar_id='core',
        spec=None,
        action=None,
    )

    # Domain construction of the same invariant raises ValidationError.
    with pytest.raises(ValidationError) as domain_error:
        SimpleProductionRule(name='expression', grammar_id='core', spec=None)

    # .map() must raise the same class of domain-level error.
    with pytest.raises(ValidationError) as map_error:
        corrupted.map()

    # Both failures are ValidationError (mapper adds no validation of its own).
    assert type(map_error.value) is type(domain_error.value)


# ** test: production_rule_aggregate_mutations
def test_production_rule_aggregate_mutations() -> None:
    '''
    Test shared and variant-specific mutators on production rule aggregates.
    '''

    # Rename and reassign via the shared NamedRuleAggregate surface.
    simple = SimpleProductionRuleAggregate(
        name='expression',
        grammar_id='core',
        spec='expression : term',
    )
    simple.rename('expr')
    simple.reassign_grammar('domain_extra')
    simple.set_spec('expr : term')
    assert simple.name == 'expr'
    assert simple.grammar_id == 'domain_extra'
    assert simple.spec == 'expr : term'

    # Complex rules also expose set_action.
    complex_rule = ComplexProductionRuleAggregate(
        name='expression',
        grammar_id='core',
        spec='expression : expression PLUS term',
        action='p[0] = p[1]',
    )
    complex_rule.set_action('p[0] = p[1] + p[3]')
    assert complex_rule.action == 'p[0] = p[1] + p[3]'
    assert isinstance(simple, ProductionRuleAggregate)
    assert isinstance(complex_rule, ProductionRuleAggregate)
