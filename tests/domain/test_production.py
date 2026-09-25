"""Tiferet Ly Production Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet import use_tester
from tiferet.domain.core import DomainObject
from tiferet_ly.domain.production import (
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)

# *** testers

# ** tester: test_production_rule
@use_tester(
    type='domain',
    target_cls=ProductionRule,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arith',
    },
    equality_fields=['name', 'grammar_id'],
)
class TestProductionRule:
    '''
    Tests for the shared production-rule base.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a production rule from its required fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the base is a domain object and matches the sample.
        assert issubclass(ProductionRule, DomainObject)
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a production constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            ProductionRule(name='expr')

    # * test: retired_fields_absent
    def test_retired_fields_absent(self, test_ctx, session):
        '''
        Keep retired and out-of-scope fields off the production-rule base.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of the retired field names are declared.
        for name in ('subgrammar', 'p_error', 'precedence', 'associativity'):
            assert name not in ProductionRule.model_fields

# ** tester: test_simple_production_rule
@use_tester(
    type='domain',
    target_cls=SimpleProductionRule,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arith',
        'spec': 'term',
    },
    equality_fields=['name', 'grammar_id', 'spec'],
)
class TestSimpleProductionRule:
    '''
    Tests for a production that declares a specification only.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a simple production from name, grammar, and spec.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the variant is a domain object and stores no action.
        assert issubclass(SimpleProductionRule, DomainObject)
        assert 'action' not in SimpleProductionRule.model_fields
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a simple production constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            SimpleProductionRule(
                name='expr',
                spec='term',
            )

    # * test: repeated_name_alternatives
    def test_repeated_name_alternatives(self, test_ctx, session):
        '''
        Allow two alternatives that share a name and grammar.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Same name and grammar, different specs, both construct.
        first = SimpleProductionRule(
            name='expr',
            grammar_id='arith',
            spec='expr PLUS term',
        )
        second = SimpleProductionRule(
            name='expr',
            grammar_id='arith',
            spec='term',
        )

        # The alternatives remain distinct specifications.
        assert first.spec == 'expr PLUS term'
        assert second.spec == 'term'

# ** tester: test_complex_production_rule
@use_tester(
    type='domain',
    target_cls=ComplexProductionRule,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arith',
        'spec': 'expr PLUS term',
        'action': 'p[0] = p[1]',
    },
    equality_fields=['name', 'grammar_id', 'spec', 'action'],
)
class TestComplexProductionRule:
    '''
    Tests for a production that declares specification and action source.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a complex production from spec and action source.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the variant is a domain object and stores action source.
        assert issubclass(ComplexProductionRule, DomainObject)
        assert 'action' in ComplexProductionRule.model_fields
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a complex production constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            ComplexProductionRule(
                name='expr',
                spec='expr PLUS term',
                action='p[0] = p[1]',
            )

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session):
        '''
        Allow the same production name under two different grammars.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Two same-named productions with different grammar ids both construct.
        arith = ComplexProductionRule(
            name='expr',
            grammar_id='arith',
            spec='expr PLUS term',
            action='p[0] = p[1]',
        )
        expr = SimpleProductionRule(
            name='expr',
            grammar_id='expr',
            spec='term',
        )

        # Each production keeps the grammar it was declared under.
        assert arith.grammar_id == 'arith'
        assert expr.grammar_id == 'expr'
