"""Tiferet Ly Action Rewrite Tests"""

# *** imports

# ** infra
import pytest

# ** app
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.translation import ACTION_COMPILATION_FAILED_ID
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.utils.translation import RuleTranslator

# *** testers

# ** tester: test_ast_rewrite
@use_tester(
    type='generic',
    target_cls=RuleTranslator,
)
class TestAstRewrite:
    '''
    Tests for optional ``$ast`` rewriting in the shared action compiler.
    '''

    # * test: ast_new_returns_aggregate
    def test_ast_new_returns_aggregate(self, test_ctx, session):
        '''
        Rewrite ``$ast.new`` into an aggregate with the given children.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile the published add action through the production translator.
        rule = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : expr PLUS expr',
            action="p[0] = $ast.new('add', [p[1], p[3]])",
        )
        _, compiled = RuleTranslator.translate_production_rule(rule)
        values = [None, 'left', '+', 'right']
        compiled(values)

        # The result is an aggregate, not the raw action text.
        node = values[0]
        assert isinstance(node, AstNodeAggregate)
        assert node.kind == 'add'
        assert node.children == ['left', 'right']

    # * test: compiled_source_has_no_ast_token
    def test_compiled_source_has_no_ast_token(self, test_ctx, session):
        '''
        Keep the declared ``$ast`` token out of the compiled function.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile an action that uses the default rewrite.
        compiled = RuleTranslator._compile_action(
            'expr',
            'expr : expr PLUS expr',
            "p[0] = $ast.new('add', [p[1], p[3]])",
        )

        # Neither names nor constants still spell the declared token.
        assert '$ast' not in compiled.__code__.co_names
        assert not any(
            isinstance(item, str) and '$ast' in item
            for item in compiled.__code__.co_consts
        )

    # * test: plain_action_returns_int
    def test_plain_action_returns_int(self, test_ctx, session):
        '''
        Leave an action with no rewrite token as ordinary Python.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile an action that does not name ``$ast``.
        compiled = RuleTranslator._compile_action(
            'number',
            r'\d+',
            'p[0] = int(p[1])',
        )
        values = [None, '3']
        compiled(values)

        # The result is the integer, not a node.
        assert values[0] == 3
        assert type(values[0]) is int

    # * test: simple_production_is_not_wrapped
    def test_simple_production_is_not_wrapped(self, test_ctx, session):
        '''
        Keep a one-symbol simple production as a pass-through.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Manufacture the pass-through. Do not compile an action.
        rule = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : term',
        )
        _, compiled = RuleTranslator.translate_production_rule(rule)
        values = [None, 'term-value']
        compiled(values)

        # The value is copied and is not an aggregate.
        assert values[0] == 'term-value'
        assert not isinstance(values[0], AstNodeAggregate)

    # * test: subclass_rewrite_constructs_subclass
    def test_subclass_rewrite_constructs_subclass(self, test_ctx, session):
        '''
        Let a caller replace ``$ast`` with a subclass factory.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A subclass receiver must construct that subclass.
        class Subclass(AstNodeAggregate):
            '''A test subclass used as the ``$ast`` binding.'''

        compiled = RuleTranslator._compile_action(
            'expr',
            'expr : expr PLUS expr',
            "p[0] = $ast.new('add', [p[1], p[3]])",
            rewrites={'$ast': Subclass},
        )
        values = [None, 'left', '+', 'right']
        compiled(values)

        # The node is the subclass, not the default aggregate class.
        assert type(values[0]) is Subclass
        assert values[0].kind == 'add'

    # * test: longer_rewrite_key_wins
    def test_longer_rewrite_key_wins(self, test_ctx, session):
        '''
        Do not let ``$stmt`` consume the prefix of ``$stmt_list``.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Distinct classes so the compiled name shows which key won.
        class Stmt:
            '''The short rewrite binding.'''

        class StmtList:
            '''The longer rewrite binding.'''

        compiled = RuleTranslator._compile_action(
            'stmt',
            'stmt : stmt_list',
            'p[0] = $stmt_list',
            rewrites={
                '$stmt': Stmt,
                '$stmt_list': StmtList,
            },
        )
        values = [None]
        compiled(values)

        # The longer key is the value. The short class is not constructed.
        assert values[0] is StmtList
        assert 'StmtList' in compiled.__code__.co_names
        assert 'Stmt' not in compiled.__code__.co_names

    # * test: duplicate_binding_name_fails
    def test_duplicate_binding_name_fails(self, test_ctx, session):
        '''
        Reject two rewrite values that would bind the same name.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Force a second class to share the default aggregate name.
        class Other:
            '''A colliding rewrite binding.'''

        Other.__name__ = AstNodeAggregate.__name__
        with pytest.raises(ServiceError) as raised:
            RuleTranslator._compile_action(
                'expr',
                'expr : expr',
                'p[0] = $other',
                rewrites={'$other': Other},
            )

        # The failure is the published compilation error.
        error = raised.value
        assert error.error_code == ACTION_COMPILATION_FAILED_ID
        assert error.kwargs['rewrite_name'] == AstNodeAggregate.__name__
