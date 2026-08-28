"""Tests for Tiferet-Ly Token Rule Mappers"""

# *** imports

# ** core
from typing import Any

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.token import ComplexTokenRule, SimpleTokenRule
from tiferet_ly.mappers.core import (
    expand_keyed_entries,
    wrap_keyed_entries,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    SyntheticTokenRuleAggregate,
    TokenRuleAggregate,
    TokenRuleConfigObject,
)

# *** constants

# ** constant: simple_core
SIMPLE_CORE = SimpleTokenRuleAggregate(
    name='PLUS',
    grammar_id='core',
    pattern=r'\+',
)

# ** constant: simple_domain_extra
SIMPLE_DOMAIN_EXTRA = SimpleTokenRuleAggregate(
    name='PLUS',
    grammar_id='domain_extra',
    pattern=r'\+\+',
)

# ** constant: complex_core
COMPLEX_CORE = ComplexTokenRuleAggregate(
    name='NUMBER',
    grammar_id='core',
    pattern=r'\d+',
    action='t.value = int(t.value)\nreturn t',
)

# ** constant: synthetic_core
SYNTHETIC_CORE = SyntheticTokenRuleAggregate(
    name='INDENT',
    grammar_id='core',
)

# *** functions

# ** function: assert_rule_fields_equal
def assert_rule_fields_equal(left: Any, right: Any) -> None:
    '''
    Assert two token rules equal on every declared field.

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
    Round-trip a token rule through ConfigObject serialization.

    :param rule: The source token rule.
    :type rule: Any
    :return: The reconstructed rule from .map().
    :rtype: Any
    '''

    # Serialize through to_data and back through model_validate/map.
    data = TokenRuleConfigObject.from_model(rule).to_primitive(
        'to_data',
        exclude=set(),
    )
    return TokenRuleConfigObject.model_validate(data).map()

# *** tests

# ** test: token_rule_aggregate_exists
def test_token_rule_aggregate_exists() -> None:
    '''
    Test that TokenRuleAggregate is a TokenRule Aggregate subclass.
    '''

    # Assert the named artifact exposes shared NamedRuleAggregate mutators.
    assert 'rename' in dir(TokenRuleAggregate)
    assert 'reassign_grammar' in dir(TokenRuleAggregate)
    assert 'set_attribute' in dir(TokenRuleAggregate)


# ** test: token_round_trip_simple_and_complex_cross_grammar
def test_token_round_trip_simple_and_complex_cross_grammar() -> None:
    '''
    Test round-tripping Simple and Complex token rules across two
    grammar_id values that share a name.
    '''

    # Round-trip each rule and assert field equality.
    assert_rule_fields_equal(round_trip(SIMPLE_CORE), SIMPLE_CORE)
    assert_rule_fields_equal(round_trip(SIMPLE_DOMAIN_EXTRA), SIMPLE_DOMAIN_EXTRA)
    assert_rule_fields_equal(round_trip(COMPLEX_CORE), COMPLEX_CORE)

    # Same-named different-grammar_id entries coexist without raising.
    assert SIMPLE_CORE.name == SIMPLE_DOMAIN_EXTRA.name
    assert SIMPLE_CORE.grammar_id != SIMPLE_DOMAIN_EXTRA.grammar_id


# ** test: synthetic_token_round_trips_with_no_pattern_or_action
def test_synthetic_token_round_trips_with_no_pattern_or_action() -> None:
    '''
    Test that a SyntheticTokenRuleAggregate round-trips through
    TokenRuleConfigObject.map()/.from_model() without requiring a
    pattern or action.
    '''

    # Round-trip the synthetic rule and assert field equality.
    round_tripped = round_trip(SYNTHETIC_CORE)
    assert isinstance(round_tripped, SyntheticTokenRuleAggregate)
    assert_rule_fields_equal(round_tripped, SYNTHETIC_CORE)

    # The serialized data carries neither pattern nor action.
    flat = TokenRuleConfigObject.from_model(SYNTHETIC_CORE).to_primitive('to_data', exclude=set())
    assert 'pattern' not in flat
    assert 'action' not in flat


# ** test: token_serialized_sequence_of_single_key_mappings
def test_token_serialized_sequence_of_single_key_mappings() -> None:
    '''
    Test serialized tokens: matches the sequence-of-single-key-mappings
    format exactly against a literal expected dict.
    '''

    # Build flat dicts with name present, then wrap for YAML shape.
    flats = [
        TokenRuleConfigObject.from_model(rule).to_primitive('to_data', exclude=set())
        for rule in (SIMPLE_CORE, COMPLEX_CORE, SIMPLE_DOMAIN_EXTRA)
    ]
    wrapped = wrap_keyed_entries(flats, key_field='name')

    # Assert the exact sequence-of-single-key-mappings shape.
    assert wrapped == [
        {
            'PLUS': {
                'grammar_id': 'core',
                'pattern': r'\+',
            },
        },
        {
            'NUMBER': {
                'grammar_id': 'core',
                'pattern': r'\d+',
                'action': 't.value = int(t.value)\nreturn t',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'domain_extra',
                'pattern': r'\+\+',
            },
        },
    ]

    # Simple rules must not carry an action key.
    assert 'action' not in wrapped[0]['PLUS']
    assert 'action' not in wrapped[2]['PLUS']

    # Expand round-trips back to the same flat dicts.
    assert expand_keyed_entries(wrapped, key_field='name') == flats


# ** test: token_map_with_no_pattern_or_action_is_synthetic_not_corrupted
def test_token_map_with_no_pattern_or_action_is_synthetic_not_corrupted() -> None:
    '''
    Test that a config object with neither pattern nor action set is no
    longer a corrupted SimpleTokenRule invariant (RFP-001 era): per
    RFP-010, that shape is the legitimate discriminator for a
    SyntheticTokenRuleAggregate.
    '''

    # Build a config object carrying neither pattern nor action.
    synthetic = TokenRuleConfigObject.model_construct(
        name='INDENT',
        grammar_id='core',
        pattern=None,
        action=None,
    )

    # .map() constructs a synthetic aggregate rather than raising.
    mapped = synthetic.map()
    assert isinstance(mapped, SyntheticTokenRuleAggregate)
    assert mapped.name == 'INDENT'
    assert mapped.grammar_id == 'core'


# ** test: token_map_raises_same_domain_error_on_corrupted_invariant
def test_token_map_raises_same_domain_error_on_corrupted_invariant() -> None:
    '''
    Test that a config object with an action but no pattern raises the
    same domain-level ValidationError at .map() time that ComplexTokenRule
    construction would raise — action present with pattern absent stays an
    invalid combination.
    '''

    # Build a config object that bypasses required-field validation.
    corrupted = TokenRuleConfigObject.model_construct(
        name='NUMBER',
        grammar_id='core',
        pattern=None,
        action='return t',
    )

    # Domain construction of the same invariant raises ValidationError.
    with pytest.raises(ValidationError) as domain_error:
        ComplexTokenRule(name='NUMBER', grammar_id='core', pattern=None, action='return t')

    # .map() must raise the same class of domain-level error.
    with pytest.raises(ValidationError) as map_error:
        corrupted.map()

    # Both failures are ValidationError (mapper adds no validation of its own).
    assert type(map_error.value) is type(domain_error.value)


# ** test: token_rule_aggregate_mutations
def test_token_rule_aggregate_mutations() -> None:
    '''
    Test shared and variant-specific mutators on token rule aggregates.
    '''

    # Rename and reassign via the shared NamedRuleAggregate surface.
    simple = SimpleTokenRuleAggregate(name='PLUS', grammar_id='core', pattern=r'\+')
    simple.rename('ADD')
    simple.reassign_grammar('domain_extra')
    simple.set_pattern(r'\+\+')
    assert simple.name == 'ADD'
    assert simple.grammar_id == 'domain_extra'
    assert simple.pattern == r'\+\+'

    # Complex rules also expose set_action.
    complex_rule = ComplexTokenRuleAggregate(
        name='NUMBER',
        grammar_id='core',
        pattern=r'\d+',
        action='return t',
    )
    complex_rule.set_action('t.value = int(t.value)\nreturn t')
    assert complex_rule.action == 't.value = int(t.value)\nreturn t'
    assert isinstance(simple, TokenRuleAggregate)
    assert isinstance(complex_rule, TokenRuleAggregate)
