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
    Test constructing a SimpleTokenRule with a name and a bare pattern.
    '''

    # Construct the simple token rule.
    rule = SimpleTokenRule(name='PLUS', pattern=r'\+')

    # Assert the fields are set correctly.
    assert isinstance(rule, TokenRule)
    assert rule.name == 'PLUS'
    assert rule.pattern == r'\+'

# ** test: complex_token_rule_construct
def test_complex_token_rule_construct() -> None:
    '''
    Test constructing a ComplexTokenRule with a name, pattern, and action.
    '''

    # Construct the complex token rule.
    rule = ComplexTokenRule(
        name='NUMBER',
        pattern=r'\d+',
        action='t.value = int(t.value)\nreturn t',
    )

    # Assert the fields are set correctly.
    assert isinstance(rule, TokenRule)
    assert rule.name == 'NUMBER'
    assert rule.pattern == r'\d+'
    assert rule.action == 't.value = int(t.value)\nreturn t'

# ** test: token_rule_base_has_no_pattern
def test_token_rule_base_has_no_pattern() -> None:
    '''
    Test that the TokenRule base has no pattern field of its own.
    '''

    # Assert pattern is not declared on the base class.
    assert 'pattern' not in TokenRule.model_fields

# ** test: simple_token_rule_requires_pattern
def test_simple_token_rule_requires_pattern() -> None:
    '''
    Test that constructing a SimpleTokenRule without a pattern raises ValidationError.
    '''

    # Missing pattern raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleTokenRule(name='PLUS')

# ** test: complex_token_rule_requires_action
def test_complex_token_rule_requires_action() -> None:
    '''
    Test that constructing a ComplexTokenRule without an action raises ValidationError.
    '''

    # Missing action raises ValidationError.
    with pytest.raises(ValidationError):
        ComplexTokenRule(name='NUMBER', pattern=r'\d+')

# ** test: token_rule_forbids_extra_fields
def test_token_rule_forbids_extra_fields() -> None:
    '''
    Test that an unknown field raises ValidationError, per DomainObject's extra='forbid' config.
    '''

    # An unrecognized field is rejected.
    with pytest.raises(ValidationError):
        SimpleTokenRule(name='PLUS', pattern=r'\+', unknown='value')

# ** test: token_rule_subgrammar_defaults_to_none
def test_token_rule_subgrammar_defaults_to_none() -> None:
    '''
    Test that TokenRule.subgrammar defaults to None (common to every subgrammar).
    '''

    # Construct without specifying a subgrammar.
    rule = SimpleTokenRule(name='PLUS', pattern=r'\+')

    # Assert the default is None.
    assert rule.subgrammar is None

# ** test: token_rule_subgrammar_settable
def test_token_rule_subgrammar_settable() -> None:
    '''
    Test that TokenRule.subgrammar can be set to a specific subgrammar id.
    '''

    # Construct with a specific subgrammar tag.
    rule = SimpleTokenRule(name='PLUS', pattern=r'\+', subgrammar='domain')

    # Assert the tag is set correctly.
    assert rule.subgrammar == 'domain'
