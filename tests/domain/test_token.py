"""Tiferet Ly Token Domain Tests"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet import use_tester
from tiferet.domain.core import DomainObject
from tiferet_ly.domain.token import (
    ComplexTokenRule,
    SimpleTokenRule,
    TokenRule,
)

# *** testers

# ** tester: test_token_rule
@use_tester(
    type='domain',
    target_cls=TokenRule,
    sample_data={
        'name': 'NUMBER',
        'grammar_id': 'arith',
    },
    equality_fields=['name', 'grammar_id'],
)
class TestTokenRule:
    '''
    Tests for the shared token-rule base.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a token rule from its required fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the base is a domain object and matches the sample.
        assert issubclass(TokenRule, DomainObject)
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a token rule constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            TokenRule(name='NUMBER')

    # * test: retired_fields_absent
    def test_retired_fields_absent(self, test_ctx, session):
        '''
        Keep retired and out-of-scope fields off the token-rule base.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of the retired field names are declared.
        for name in ('subgrammar', 't_error', 'precedence', 'associativity'):
            assert name not in TokenRule.model_fields

# ** tester: test_simple_token_rule
@use_tester(
    type='domain',
    target_cls=SimpleTokenRule,
    sample_data={
        'name': 'NUMBER',
        'grammar_id': 'arith',
        'pattern': '[0-9]+',
    },
    equality_fields=['name', 'grammar_id', 'pattern'],
)
class TestSimpleTokenRule:
    '''
    Tests for a token rule that declares a pattern only.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a simple token rule from name, grammar, and pattern.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the variant is a domain object and stores no action.
        assert issubclass(SimpleTokenRule, DomainObject)
        assert 'action' not in SimpleTokenRule.model_fields
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a simple token rule constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            SimpleTokenRule(
                name='NUMBER',
                pattern='[0-9]+',
            )

# ** tester: test_complex_token_rule
@use_tester(
    type='domain',
    target_cls=ComplexTokenRule,
    sample_data={
        'name': 'NUMBER',
        'grammar_id': 'arith',
        'pattern': '[0-9]+',
        'action': 't.value = int(t.value)',
    },
    equality_fields=['name', 'grammar_id', 'pattern', 'action'],
)
class TestComplexTokenRule:
    '''
    Tests for a token rule that declares pattern and action source.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a complex token rule from pattern and action source.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the variant is a domain object and stores action source.
        assert issubclass(ComplexTokenRule, DomainObject)
        assert 'action' in ComplexTokenRule.model_fields
        test_ctx.assert_new()

    # * test: grammar_id_required
    def test_grammar_id_required(self, test_ctx, session):
        '''
        Reject a complex token rule constructed without grammar membership.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without grammar_id fails validation.
        with pytest.raises(ValidationError):
            ComplexTokenRule(
                name='NUMBER',
                pattern='[0-9]+',
                action='t.value = int(t.value)',
            )

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session):
        '''
        Allow the same token name under two different grammars.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Two same-named rules with different grammar ids both construct.
        arith = ComplexTokenRule(
            name='NUMBER',
            grammar_id='arith',
            pattern='[0-9]+',
            action='t.value = int(t.value)',
        )
        expr = SimpleTokenRule(
            name='NUMBER',
            grammar_id='expr',
            pattern='[0-9]+',
        )

        # Each rule keeps the grammar it was declared under.
        assert arith.grammar_id == 'arith'
        assert expr.grammar_id == 'expr'
