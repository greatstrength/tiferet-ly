"""Tests for Tiferet-Ly Production Rule Domain Models"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.production import (
    ProductionRule,
    SimpleProductionRule,
    ComplexProductionRule,
)

# *** tests

# ** test: simple_production_rule_construct
def test_simple_production_rule_construct() -> None:
    '''
    Test constructing a SimpleProductionRule with a name and a bare spec.
    '''

    # Construct the simple production rule.
    rule = SimpleProductionRule(name='expression', spec='expression : term')

    # Assert the fields are set correctly.
    assert isinstance(rule, ProductionRule)
    assert rule.name == 'expression'
    assert rule.spec == 'expression : term'

# ** test: complex_production_rule_construct
def test_complex_production_rule_construct() -> None:
    '''
    Test constructing a ComplexProductionRule with a name, spec, and action.
    '''

    # Construct the complex production rule.
    rule = ComplexProductionRule(
        name='expression',
        spec='expression : expression PLUS term',
        action='p[0] = p[1] + p[3]',
    )

    # Assert the fields are set correctly.
    assert isinstance(rule, ProductionRule)
    assert rule.name == 'expression'
    assert rule.spec == 'expression : expression PLUS term'
    assert rule.action == 'p[0] = p[1] + p[3]'

# ** test: production_rule_base_has_no_spec
def test_production_rule_base_has_no_spec() -> None:
    '''
    Test that the ProductionRule base has no spec field of its own.
    '''

    # Assert spec is not declared on the base class.
    assert 'spec' not in ProductionRule.model_fields

# ** test: simple_production_rule_requires_spec
def test_simple_production_rule_requires_spec() -> None:
    '''
    Test that constructing a SimpleProductionRule without a spec raises ValidationError.
    '''

    # Missing spec raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleProductionRule(name='expression')

# ** test: complex_production_rule_requires_action
def test_complex_production_rule_requires_action() -> None:
    '''
    Test that constructing a ComplexProductionRule without an action raises ValidationError.
    '''

    # Missing action raises ValidationError.
    with pytest.raises(ValidationError):
        ComplexProductionRule(name='expression', spec='expression : term')

# ** test: production_rule_subgrammar_defaults_to_none
def test_production_rule_subgrammar_defaults_to_none() -> None:
    '''
    Test that ProductionRule.subgrammar defaults to None (common to every subgrammar).
    '''

    # Construct without specifying a subgrammar.
    rule = SimpleProductionRule(name='expression', spec='expression : term')

    # Assert the default is None.
    assert rule.subgrammar is None

# ** test: production_rule_subgrammar_settable
def test_production_rule_subgrammar_settable() -> None:
    '''
    Test that ProductionRule.subgrammar can be set to a specific subgrammar id.
    '''

    # Construct with a specific subgrammar tag.
    rule = SimpleProductionRule(
        name='attr_decl',
        spec='attr_decl : IDENTIFIER COLON attr_types EQUALS assign_rhs NEWLINE',
        subgrammar='domain',
    )

    # Assert the tag is set correctly.
    assert rule.subgrammar == 'domain'

# ** test: production_rule_names_may_repeat
def test_production_rule_names_may_repeat() -> None:
    '''
    Test that two ProductionRule instances may legitimately share a name,
    representing alternative specs for the same grammar symbol.
    '''

    # Construct two alternatives sharing the same name.
    first = SimpleProductionRule(name='expression', spec='expression : term')
    second = SimpleProductionRule(
        name='expression',
        spec='expression : expression PLUS term',
    )

    # Assert both constructed successfully with the shared name.
    assert first.name == second.name == 'expression'
    assert first.spec != second.spec
