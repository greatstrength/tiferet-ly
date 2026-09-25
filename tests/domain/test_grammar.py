"""Tiferet Ly Grammar Domain Tests"""

# *** imports

# ** app
from tiferet import use_tester
from tiferet.domain.core import DomainObject
from tiferet_ly.domain import grammar as grammar_module
from tiferet_ly.domain.grammar import Grammar

# *** testers

# ** tester: test_grammar
@use_tester(
    type='domain',
    target_cls=Grammar,
    sample_data={
        'id': 'arith',
        'parent_ids': ['expr', 'factor'],
        'start': 'expr',
    },
    equality_fields=['id', 'parent_ids', 'start'],
)
class TestGrammar:
    '''
    Tests for the lean grammar model.
    '''

    # * test: new
    def test_new(self, test_ctx, session):
        '''
        Construct a grammar from its three declared fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the model is a domain object with exactly those fields.
        assert issubclass(Grammar, DomainObject)
        assert set(Grammar.model_fields) == {'id', 'parent_ids', 'start'}
        test_ctx.assert_new()

    # * test: empty_parent_ids
    def test_empty_parent_ids(self, test_ctx, session):
        '''
        Accept a root grammar that composes no parents.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An empty parent list is a valid root grammar.
        grammar = Grammar(
            id='expr',
            parent_ids=[],
            start='expr',
        )

        # The declared parent list is preserved.
        assert grammar.parent_ids == []

    # * test: unresolvable_parent
    def test_unresolvable_parent(self, test_ctx, session):
        '''
        Accept a parent identifier that names no grammar.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Parent existence is not checked at construction.
        grammar = Grammar(
            id='arith',
            parent_ids=['missing'],
            start='expr',
        )

        # The unresolved identifier is stored as declared.
        assert grammar.parent_ids == ['missing']

    # * test: self_referential_parent
    def test_self_referential_parent(self, test_ctx, session):
        '''
        Accept a grammar that lists itself as a parent.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Cycle detection is not performed at construction.
        grammar = Grammar(
            id='arith',
            parent_ids=['arith'],
            start='expr',
        )

        # The self-reference is stored as declared.
        assert grammar.parent_ids == ['arith']

    # * test: start_names_no_production
    def test_start_names_no_production(self, test_ctx, session):
        '''
        Accept a start name that names no production.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Start resolution is not performed at construction.
        grammar = Grammar(
            id='arith',
            parent_ids=[],
            start='missing',
        )

        # The unresolved start name is stored as declared.
        assert grammar.start == 'missing'

    # * test: retired_shape_absent
    def test_retired_shape_absent(self, test_ctx, session):
        '''
        Omit the retired container shape and its catalogue fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Catalogue and precedence fields are not declared.
        for name in (
            'token_rules',
            'production_rules',
            'subgrammars',
            'precedence',
            'associativity',
        ):
            assert name not in Grammar.model_fields

        # The retired container types are not part of the module.
        assert not hasattr(grammar_module, 'Subgrammar')
        assert not hasattr(grammar_module, 'GrammarDeclaration')
