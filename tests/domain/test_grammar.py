"""Tiferet Ly Grammar Domain Tests"""

# *** imports

# ** core
from typing import Optional

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.domain.core import DomainObject

# ** app
from tiferet_ly.domain import grammar as grammar_module
from tiferet_ly.domain.grammar import Grammar
from tiferet_ly.domain.layout import LayoutProfile

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
        Construct a grammar from its declared fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Assert the model is a domain object with exactly those fields, in order.
        assert issubclass(Grammar, DomainObject)
        assert list(Grammar.model_fields) == ['id', 'parent_ids', 'start', 'ignore', 'layout']
        assert set(Grammar.model_fields) == {'id', 'parent_ids', 'start', 'ignore', 'layout'}

        # Assert ignore is an optional string that defaults to None.
        ignore = Grammar.model_fields['ignore']
        assert ignore.annotation == Optional[str]
        assert ignore.default is None
        assert ignore.is_required() is False
        assert ignore.description == (
            'A bare regular-expression character class PLY skips before attempting any '
            'token rule, installed as the literal t_ignore module attribute PLY\'s own '
            'convention expects. Grammar-own, like start: not composed across parent_ids.'
        )

        # Assert layout follows ignore as an optional profile that defaults to None.
        names = list(Grammar.model_fields)
        assert names.index('layout') == names.index('ignore') + 1
        layout = Grammar.model_fields['layout']
        assert layout.annotation == LayoutProfile | None
        assert layout.default is None
        assert layout.is_required() is False
        assert layout.description == (
            'The declared indentation/delimiter layout policy a LayoutFilter applies to '
            'this grammar\'s lexeme stream. Grammar-own, like start and ignore: not '
            'composed across parent_ids.'
        )

        # Assert construction from the unchanged sample data.
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

    # * test: ignore_defaults_to_none
    def test_ignore_defaults_to_none(self, test_ctx, session):
        '''
        Store no ignore pattern when ignore is omitted or None.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Omitting ignore stores None.
        grammar = Grammar(
            id='expr',
            parent_ids=[],
            start='expr',
        )
        assert grammar.ignore is None

        # Passing ignore=None stores None.
        grammar = Grammar(
            id='expr',
            parent_ids=[],
            start='expr',
            ignore=None,
        )
        assert grammar.ignore is None

    # * test: ignore_stores_declared_string
    def test_ignore_stores_declared_string(self, test_ctx, session):
        '''
        Store a declared ignore string unchanged, without compiling it.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Each declared string, including an invalid character class, is stored as given.
        for value in (' \t', '', '['):
            grammar = Grammar(
                id='expr',
                parent_ids=[],
                start='expr',
                ignore=value,
            )
            assert grammar.ignore == value
            assert type(grammar.ignore) is str

    # * test: ignore_is_not_composed_across_parent_ids
    def test_ignore_is_not_composed_across_parent_ids(self, test_ctx, session):
        '''
        Keep ignore grammar-own: a child does not receive a parent's pattern.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A parent grammar declares its own ignore pattern.
        parent = Grammar(
            id='expr',
            parent_ids=[],
            start='expr',
            ignore=' \t',
        )
        assert parent.ignore == ' \t'

        # A child that lists that parent does not inherit the pattern.
        child = Grammar(
            id='arith',
            parent_ids=['expr', 'factor'],
            start='expr',
        )
        assert child.parent_ids == ['expr', 'factor']
        assert child.ignore is None

    # * test: layout_defaults_to_none
    def test_layout_defaults_to_none(self, test_ctx, session):
        '''
        Store no layout profile when layout is omitted or None.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Omitting layout stores None.
        grammar = Grammar(
            id='arith',
            start='expr',
        )
        assert grammar.layout is None
        assert grammar.parent_ids == []

        # Passing layout=None stores None, even with parents.
        grammar = Grammar(
            id='arith',
            parent_ids=['expr', 'factor'],
            start='expr',
            layout=None,
        )
        assert grammar.layout is None
        assert grammar.parent_ids == ['expr', 'factor']

    # * test: layout_construct
    def test_layout_construct(self, test_ctx, session):
        '''
        Store a declared profile by identity and validate a profile mapping.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A profile instance is stored by identity, and parents do not clear it.
        profile = LayoutProfile(
            indent_token='INDENT',
            dedent_token='DEDENT',
        )
        grammar = Grammar(
            id='arith',
            parent_ids=['expr'],
            start='expr',
            layout=profile,
        )
        assert grammar.layout is profile
        assert grammar.layout.indent_token == 'INDENT'
        assert grammar.layout.dedent_token == 'DEDENT'
        assert grammar.parent_ids == ['expr']

        # A mapping of profile fields is validated as a profile, not stored as a dict.
        grammar = Grammar(
            id='arith',
            parent_ids=[],
            start='expr',
            layout={'indent_token': 'INDENT', 'dedent_token': 'DEDENT'},
        )
        assert isinstance(grammar.layout, LayoutProfile)
        assert not isinstance(grammar.layout, dict)
        assert grammar.layout.indent_token == 'INDENT'
        assert grammar.layout.dedent_token == 'DEDENT'

    # * test: layout_rejects_non_profile
    def test_layout_rejects_non_profile(self, test_ctx, session):
        '''
        Reject a layout value that is not a profile.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A bare string is not a layout profile.
        with pytest.raises(ValidationError):
            Grammar(
                id='arith',
                parent_ids=[],
                start='expr',
                layout='INDENT',
            )

    # * test: layout_not_inherited_through_parent_ids
    def test_layout_not_inherited_through_parent_ids(self, test_ctx, session):
        '''
        Keep layout grammar-own: a child does not receive a parent's profile.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A parent grammar declares its own layout profile.
        declared = Grammar(
            id='expr',
            parent_ids=[],
            start='expr',
            layout=LayoutProfile(
                indent_token='INDENT',
                dedent_token='DEDENT',
            ),
        )
        assert declared.layout is not None

        # A child that lists that parent does not inherit the profile.
        child = Grammar(
            id='arith',
            parent_ids=['expr'],
            start='expr',
        )
        assert child.layout is None
        assert child.layout is not declared.layout
        assert child.parent_ids == ['expr']
