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
    Test constructing a SimpleProductionRule with a name, grammar_id, and
    a bare spec.
    '''

    # Construct the simple production rule.
    rule = SimpleProductionRule(name='expression', grammar_id='arithmetic', spec='expression : term')

    # Assert the fields are set correctly.
    assert isinstance(rule, ProductionRule)
    assert rule.name == 'expression'
    assert rule.grammar_id == 'arithmetic'
    assert rule.spec == 'expression : term'

# ** test: complex_production_rule_construct
def test_complex_production_rule_construct() -> None:
    '''
    Test constructing a ComplexProductionRule with a name, grammar_id,
    spec, and action.
    '''

    # Construct the complex production rule.
    rule = ComplexProductionRule(
        name='expression',
        grammar_id='arithmetic',
        spec='expression : expression PLUS term',
        action='p[0] = p[1] + p[3]',
    )

    # Assert the fields are set correctly.
    assert isinstance(rule, ProductionRule)
    assert rule.name == 'expression'
    assert rule.grammar_id == 'arithmetic'
    assert rule.spec == 'expression : expression PLUS term'
    assert rule.action == 'p[0] = p[1] + p[3]'

# ** test: production_rule_base_has_no_spec
def test_production_rule_base_has_no_spec() -> None:
    '''
    Test that the ProductionRule base has no spec field of its own.
    '''

    # Assert spec is not declared on the base class.
    assert 'spec' not in ProductionRule.model_fields

# ** test: production_rule_has_no_subgrammar_field
def test_production_rule_has_no_subgrammar_field() -> None:
    '''
    Test that no ProductionRule variant carries the retired subgrammar field.
    '''

    # Assert subgrammar is not declared on any ProductionRule variant.
    assert 'subgrammar' not in ProductionRule.model_fields
    assert 'subgrammar' not in SimpleProductionRule.model_fields
    assert 'subgrammar' not in ComplexProductionRule.model_fields

# ** test: simple_production_rule_requires_spec
def test_simple_production_rule_requires_spec() -> None:
    '''
    Test that constructing a SimpleProductionRule without a spec raises ValidationError.
    '''

    # Missing spec raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleProductionRule(name='expression', grammar_id='arithmetic')

# ** test: complex_production_rule_requires_action
def test_complex_production_rule_requires_action() -> None:
    '''
    Test that constructing a ComplexProductionRule without an action raises ValidationError.
    '''

    # Missing action raises ValidationError.
    with pytest.raises(ValidationError):
        ComplexProductionRule(name='expression', grammar_id='arithmetic', spec='expression : term')

# ** test: production_rule_requires_grammar_id
def test_production_rule_requires_grammar_id() -> None:
    '''
    Test that constructing a ProductionRule variant without grammar_id
    raises ValidationError, since grammar_id is required rather than
    optional.
    '''

    # Missing grammar_id raises ValidationError.
    with pytest.raises(ValidationError):
        SimpleProductionRule(name='expression', spec='expression : term')

# ** test: production_rule_names_may_repeat
def test_production_rule_names_may_repeat() -> None:
    '''
    Test that two ProductionRule instances may legitimately share a name
    within the same grammar, representing alternative specs for the same
    grammar symbol.
    '''

    # Construct two alternatives sharing the same name and grammar_id.
    first = SimpleProductionRule(name='expression', grammar_id='arithmetic', spec='expression : term')
    second = SimpleProductionRule(
        name='expression',
        grammar_id='arithmetic',
        spec='expression : expression PLUS term',
    )

    # Assert both constructed successfully with the shared name.
    assert first.name == second.name == 'expression'
    assert first.spec != second.spec

# ** test: production_rules_may_share_name_across_different_grammar_ids
def test_production_rules_may_share_name_across_different_grammar_ids() -> None:
    '''
    Test that two ProductionRule instances sharing a name but declared
    under different grammar_id values may both be constructed without
    either raising. Name uniqueness scoped to a grammar_id is not a check
    either ProductionRule or its Simple/Complex variants perform in
    isolation — each rule is constructed independently, with no shared
    registry to collide against.
    '''

    # Construct two production rules sharing a name under different grammars.
    first = SimpleProductionRule(name='expression', grammar_id='arithmetic', spec='expression : term')
    second = SimpleProductionRule(name='expression', grammar_id='algebra', spec='expression : factor')

    # Assert both constructed successfully with the shared name.
    assert first.name == second.name == 'expression'
    assert first.grammar_id != second.grammar_id
