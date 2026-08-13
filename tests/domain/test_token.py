"""Tests for Tiferet-Ly Token Rule Domain Models"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.token import (
    TokenRule,
    SimpleTokenRule,
    ComplexTokenRule,
)

# *** tests

# ** test: simple_token_rule_construct
def test_simple_token_rule_construct() -> None:
    '''
    Test constructing a SimpleTokenRule with a name, grammar_id, and a
    bare pattern.
    '''

    # Construct the simple token rule.
    rule = SimpleTokenRule(name='PLUS', grammar_id='arithmetic', pattern=r'\+')

    # Assert the fields are set correctly.
    assert isinstance(rule, TokenRule)
    assert rule.name == 'PLUS'
    assert rule.grammar_id == 'arithmetic'
    assert rule.pattern == r'\+'

# ** test: complex_token_rule_construct
def test_complex_token_rule_construct() -> None:
    '''
    Test constructing a ComplexTokenRule with a name, grammar_id,
    pattern, and action.
    '''

    # Construct the complex token rule.
    rule = ComplexTokenRule(
        name='NUMBER',
        grammar_id='arithmetic',
        pattern=r'\d+',
        action='t.value = int(t.value)\nreturn t',
    )

    # Assert the fields are set correctly.
    assert isinstance(rule, TokenRule)
    assert rule.name == 'NUMBER'
    assert rule.grammar_id == 'arithmetic'
    assert rule.pattern == r'\d+'
    assert rule.action == 't.value = int(t.value)\nreturn t'

# ** test: token_rule_base_has_no_pattern
def test_token_rule_base_has_no_pattern() -> None:
    '''
    Test that the TokenRule base has no pattern field of its own.
    '''

    # Assert pattern is not declared on the base class.
    assert 'pattern' not in TokenRule.model_fields

# ** test: token_rule_has_no_subgrammar_field
def test_token_rule_has_no_subgrammar_field() -> None:
    '''
    Test that no TokenRule variant carries the retired subgrammar field.
    '''

    # Assert subgrammar is not declared on any TokenRule variant.
    assert 'subgrammar' not in TokenRule.model_fields
    assert 'subgrammar' not in SimpleTokenRule.model_fields
    assert 'subgrammar' not in ComplexTokenRule.model_fields

# ** test: simple_token_rule_requires_pattern
def test_simple_token_rule_requires_pattern() -> None:
    '''
    Test that constructing a SimpleTokenRule without a pattern raises ValidationError.
    '''

    # Missing pattern raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleTokenRule(name='PLUS', grammar_id='arithmetic')

# ** test: complex_token_rule_requires_action
def test_complex_token_rule_requires_action() -> None:
    '''
    Test that constructing a ComplexTokenRule without an action raises ValidationError.
    '''

    # Missing action raises ValidationError.
    with pytest.raises(ValidationError):
        ComplexTokenRule(name='NUMBER', grammar_id='arithmetic', pattern=r'\d+')

# ** test: token_rule_forbids_extra_fields
def test_token_rule_forbids_extra_fields() -> None:
    '''
    Test that an unknown field raises ValidationError, per DomainObject's extra='forbid' config.
    '''

    # An unrecognized field is rejected.
    with pytest.raises(ValidationError):
        SimpleTokenRule(name='PLUS', grammar_id='arithmetic', pattern=r'\+', unknown='value')

# ** test: token_rule_requires_grammar_id
def test_token_rule_requires_grammar_id() -> None:
    '''
    Test that constructing a TokenRule variant without grammar_id raises
    ValidationError, since grammar_id is required rather than optional.
    '''

    # Missing grammar_id raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleTokenRule(name='PLUS', pattern=r'\+')

# ** test: token_rules_may_share_name_across_different_grammar_ids
def test_token_rules_may_share_name_across_different_grammar_ids() -> None:
    '''
    Test that two TokenRule instances sharing a name but declared under
    different grammar_id values may both be constructed without either
    raising. Name uniqueness scoped to a grammar_id is not a check either
    TokenRule or its Simple/Complex variants perform in isolation — each
    rule is constructed independently, with no shared registry to collide
    against.
    '''

    # Construct two token rules sharing a name under different grammars.
    first = SimpleTokenRule(name='PLUS', grammar_id='arithmetic', pattern=r'\+')
    second = SimpleTokenRule(name='PLUS', grammar_id='algebra', pattern=r'\+\+')

    # Assert both constructed successfully with the shared name.
    assert first.name == second.name == 'PLUS'
    assert first.grammar_id != second.grammar_id
