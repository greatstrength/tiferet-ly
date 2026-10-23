"""Tiferet Ly PlyReader Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from unittest.mock import patch

# ** infra
import pytest
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.assets.grammar import GRAMMAR_NOT_FOUND_ID
from tiferet_ly.assets.reader import (
    LEX_ERROR_ID,
    PARSE_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    SyntheticTokenRuleAggregate,
)
from tiferet_ly.utils import core as core_utils
from tiferet_ly.utils.core import PlyReader

# *** functions

# ** function: imported_modules
def _imported_modules(tree: ast.AST) -> list[str]:
    '''
    Collect imported module names from a parsed module.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Imported module names.
    :rtype: list[str]
    '''

    # Walk import and import-from nodes only.
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

# ** function: grammar
def _grammar(grammar_id: str, parent_ids: list[str] | None = None) -> GrammarAggregate:
    '''
    Build a lean grammar aggregate.

    :param grammar_id: The grammar identifier.
    :type grammar_id: str
    :param parent_ids: The ordered parent identifiers.
    :type parent_ids: list[str] | None
    :return: A grammar aggregate.
    :rtype: GrammarAggregate
    '''

    # Start is required by construction and is not a reader input.
    return GrammarAggregate(
        id=grammar_id,
        parent_ids=list(parent_ids or []),
        start='start',
    )

# *** tests

# ** test: interfaces_do_not_import_ply
def test_interfaces_do_not_import_ply():
    '''
    Keep PLY out of the interface package.
    '''

    # Scan the package without importing it again.
    root = Path(core_utils.__file__).parents[1] / 'interfaces'
    for path in sorted(root.glob('*.py')):
        modules = _imported_modules(ast.parse(path.read_text()))
        for module in modules:
            assert module != 'ply' and not module.startswith('ply.')

# ** test: events_do_not_import_ply
def test_events_do_not_import_ply():
    '''
    Keep PLY out of the event package.
    '''

    # Scan the package without importing it again.
    root = Path(core_utils.__file__).parents[1] / 'events'
    for path in sorted(root.glob('*.py')):
        modules = _imported_modules(ast.parse(path.read_text()))
        for module in modules:
            assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_ply_reader
@use_tester(
    type='generic',
    target_cls=PlyReader,
)
class TestPlyReader:
    '''
    Tests for shared reader assembly.
    '''

    # * test: error_constants
    def test_error_constants(self, test_ctx, session):
        '''
        Keep the three published reader error identifiers.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The identifiers are the published strings, not aliases.
        assert LEX_ERROR_ID == 'LEX_ERROR'
        assert PARSE_ERROR_ID == 'PARSE_ERROR'
        assert READER_BUILD_FAILED_ID == 'READER_BUILD_FAILED'
        assert not hasattr(PlyReader, 'tokenize')
        assert not hasattr(PlyReader, 'parse')

    # * test: unknown_grammar_does_not_call_lex
    def test_unknown_grammar_does_not_call_lex(self, test_ctx, session):
        '''
        Raise before PLY when the grammar identifier is absent.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A known neighbour is not a substitute for the missing id.
        grammars = [_grammar('expr')]
        with patch('tiferet_ly.utils.core.lex.lex') as lex_lex:
            with pytest.raises(ServiceError) as raised:
                PlyReader.build_lexer('missing', grammars, [])

        # The error is the grammar error, and the lexer was not built.
        assert raised.value.error_code == GRAMMAR_NOT_FOUND_ID
        assert raised.value.kwargs['grammar_id'] == 'missing'
        lex_lex.assert_not_called()

    # * test: resolve_grammar_returns_match
    def test_resolve_grammar_returns_match(self, test_ctx, session):
        '''
        Return the matching aggregate and leave the catalogue unchanged.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The second grammar is the match.
        first = _grammar('base')
        second = _grammar('expr', ['base'])
        found = PlyReader.resolve_grammar('expr', [first, second])

        # Identity is preserved. The list is not rewritten.
        assert found is second
        assert [grammar.id for grammar in (first, second)] == ['base', 'expr']

    # * test: install_tokens_preserves_selected_order
    def test_install_tokens_preserves_selected_order(self, test_ctx, session):
        '''
        Keep a later simple token after an earlier complex token.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The child redefines ZZZ. AAA is a later simple token.
        base = _grammar('base')
        expr = _grammar('expr', ['base'])
        tokens = [
            SimpleTokenRuleAggregate(
                name='ZZZ',
                grammar_id='base',
                pattern='z',
            ),
            ComplexTokenRuleAggregate(
                name='ZZZ',
                grammar_id='expr',
                pattern='z+',
                action='return t',
            ),
            SimpleTokenRuleAggregate(
                name='AAA',
                grammar_id='expr',
                pattern='a',
            ),
            SimpleTokenRuleAggregate(
                name='MMM',
                grammar_id='other',
                pattern='m',
            ),
        ]
        installed = PlyReader.install_tokens(expr, [base, expr], tokens)

        # Selected order wins over name sort and over simple-token-first.
        assert installed.tokens == ['ZZZ', 'AAA']
        assert callable(installed.t_ZZZ)
        assert installed.t_ZZZ.__doc__ == 'z+'
        assert installed.t_AAA == 'a'
        assert not hasattr(installed, 't_MMM')

    # * test: lex_error_carries_span
    def test_lex_error_carries_span(self, test_ctx, session):
        '''
        Carry grammar, line, offset, and unmatched text on the error.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The helper raises. It does not skip the character.
        with pytest.raises(ServiceError) as raised:
            PlyReader.raise_lex_error('expr', 2, 4, '@')

        # The four published span keys are on the error.
        error = raised.value
        assert error.error_code == LEX_ERROR_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['lineno'] == 2
        assert error.kwargs['lexpos'] == 4
        assert error.kwargs['value'] == '@'

    # * test: build_lexer_rebuilds_without_a_table
    def test_build_lexer_rebuilds_without_a_table(self, test_ctx, session):
        '''
        Call PLY on every build and do not write a lexer table.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # One simple token is enough for PLY to accept the module.
        grammar = _grammar('expr')
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Za-z]+',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        # Two builds both reach PLY. Neither writes lextab.py.
        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            first = PlyReader.build_lexer('expr', [grammar], tokens)
            second = PlyReader.build_lexer('expr', [grammar], tokens)

        assert first is not second
        assert len(calls) == 2
        assert all(call['optimize'] == 0 for call in calls)
        package = Path(core_utils.__file__).parent
        assert not (package / 'lextab.py').exists()
        assert not (Path.cwd() / 'lextab.py').exists()

        # An unmatched character uses the span-bearing helper.
        first.input('@')
        with pytest.raises(ServiceError) as raised:
            first.token()
        error = raised.value
        assert error.error_code == LEX_ERROR_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['lineno'] == 1
        assert error.kwargs['lexpos'] == 0
        assert error.kwargs['value'] == '@'

    # * test: build_failure_raises_reader_error
    def test_build_failure_raises_reader_error(self, test_ctx, session):
        '''
        Turn a PLY build failure into the reader build error.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An empty token list is not a lexer.
        with pytest.raises(ServiceError) as raised:
            PlyReader.build_lexer('expr', [_grammar('expr')], [])

        # The failure names the grammar and is not a raw PLY error.
        error = raised.value
        assert error.error_code == READER_BUILD_FAILED_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert isinstance(error.__cause__, SyntaxError)

    # * test: install_tokens_keeps_synthetic_name_without_attribute
    def test_install_tokens_keeps_synthetic_name_without_attribute(self, test_ctx, session):
        '''
        Keep a synthetic name in selected order without a t_ attribute.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A closer complex token, a synthetic token, then a later simple token.
        base = _grammar('base')
        expr = _grammar('expr', ['base'])
        tokens = [
            SimpleTokenRuleAggregate(
                name='ZZZ',
                grammar_id='base',
                pattern='z',
            ),
            ComplexTokenRuleAggregate(
                name='ZZZ',
                grammar_id='expr',
                pattern='z+',
                action='return t',
            ),
            SyntheticTokenRuleAggregate(
                name='INDENT',
                grammar_id='expr',
            ),
            SimpleTokenRuleAggregate(
                name='AAA',
                grammar_id='expr',
                pattern='a',
            ),
            SimpleTokenRuleAggregate(
                name='MMM',
                grammar_id='other',
                pattern='m',
            ),
        ]
        with patch('tiferet_ly.utils.core.lex.lex') as lex_lex:
            installed = PlyReader.install_tokens(expr, [base, expr], tokens)

        # The synthetic name keeps its place and installs no attribute.
        assert installed.tokens == ['ZZZ', 'INDENT', 'AAA']
        assert callable(installed.t_ZZZ)
        assert installed.t_ZZZ.__doc__ == 'z+'
        assert not hasattr(installed, 't_INDENT')
        assert installed.t_AAA == 'a'
        assert not hasattr(installed, 't_MMM')
        lex_lex.assert_not_called()

        # The lexer-free name list matches the installed list.
        names = PlyReader.select_token_names(expr, [base, expr], tokens)
        assert names == ['ZZZ', 'INDENT', 'AAA']

    # * test: closer_synthetic_replaces_farther_token
    def test_closer_synthetic_replaces_farther_token(self, test_ctx, session):
        '''
        Let a closer synthetic rule win the name without installing a pattern.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The parent declares a real INDENT. The child declares it synthetic.
        base = _grammar('base')
        expr = _grammar('expr', ['base'])
        tokens = [
            SimpleTokenRuleAggregate(
                name='INDENT',
                grammar_id='base',
                pattern=' ',
            ),
            SyntheticTokenRuleAggregate(
                name='INDENT',
                grammar_id='expr',
            ),
        ]
        installed = PlyReader.install_tokens(expr, [base, expr], tokens)

        # The name is kept. The farther pattern is not installed under it.
        assert installed.tokens == ['INDENT']
        assert not hasattr(installed, 't_INDENT')
        names = PlyReader.select_token_names(expr, [base, expr], tokens)
        assert names == ['INDENT']

    # * test: select_token_names_does_not_build_a_lexer
    def test_select_token_names_does_not_build_a_lexer(self, test_ctx, session):
        '''
        Derive selected names without translating or calling PLY.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The target declares an ignore string that name selection does not use.
        base = _grammar('base')
        expr = GrammarAggregate(
            id='expr',
            parent_ids=['base'],
            start='start',
            ignore=' \t',
        )
        tokens = [
            SimpleTokenRuleAggregate(
                name='ZZZ',
                grammar_id='base',
                pattern='z',
            ),
            ComplexTokenRuleAggregate(
                name='ZZZ',
                grammar_id='expr',
                pattern='z+',
                action='return t',
            ),
            SyntheticTokenRuleAggregate(
                name='INDENT',
                grammar_id='expr',
            ),
            SimpleTokenRuleAggregate(
                name='AAA',
                grammar_id='expr',
                pattern='a',
            ),
            SimpleTokenRuleAggregate(
                name='MMM',
                grammar_id='other',
                pattern='m',
            ),
        ]
        translate_path = 'tiferet_ly.utils.core.RuleTranslator.translate_token_rule'
        with patch('tiferet_ly.utils.core.lex.lex') as lex_lex:
            with patch(translate_path) as translate:
                names = PlyReader.select_token_names(expr, [base, expr], tokens)

        # A plain list of names, with no translation and no lexer build.
        assert isinstance(names, list)
        assert all(isinstance(name, str) for name in names)
        assert names == ['ZZZ', 'INDENT', 'AAA']
        lex_lex.assert_not_called()
        translate.assert_not_called()

    # * test: build_lexer_installs_exact_ignore
    def test_build_lexer_installs_exact_ignore(self, test_ctx, session):
        '''
        Install the grammar's own ignore string exactly, including an empty string.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # One word token. The grammar ignores spaces and tabs.
        grammar = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='start',
            ignore=' \t',
        )
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Za-z]+',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            lexer = PlyReader.build_lexer('expr', [grammar], tokens)

        # The exact string reaches PLY. The lex.lex keywords are unchanged.
        kwargs = calls[0]
        assert kwargs['object'].t_ignore == ' \t'
        assert 'reflags' not in kwargs
        assert kwargs['optimize'] == 0
        assert kwargs['debug'] is False
        assert 'module' not in kwargs

        # Spaces and tabs are skipped between words.
        lexer.input('a \tb')
        first = lexer.token()
        second = lexer.token()
        assert (first.value, first.lexpos, first.lineno) == ('a', 0, 1)
        assert (second.value, second.lexpos, second.lineno) == ('b', 3, 1)
        assert lexer.token() is None

        # An empty ignore string is installed, not treated as unset.
        empty = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='start',
            ignore='',
        )
        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            lexer = PlyReader.build_lexer('expr', [empty], tokens)
        assert calls[1]['object'].t_ignore == ''
        lexer.input('ab')
        token = lexer.token()
        assert (token.type, token.value) == ('WORD', 'ab')

    # * test: build_lexer_omits_ignore_when_unset
    def test_build_lexer_omits_ignore_when_unset(self, test_ctx, session):
        '''
        Omit t_ignore when the grammar declares no ignore string.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Build an ignoring grammar first, then the unset grammar.
        ignoring = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='start',
            ignore=' \t',
        )
        unset = _grammar('expr')
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Za-z]+',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            PlyReader.build_lexer('expr', [ignoring], tokens)
            lexer = PlyReader.build_lexer('expr', [unset], tokens)

        # The fresh module does not keep the earlier string.
        captured = calls[1]['object']
        assert not hasattr(captured, 't_ignore')

        # A space is now unmatched text.
        lexer.input('a b')
        assert lexer.token().value == 'a'
        with pytest.raises(ServiceError) as raised:
            lexer.token()
        assert raised.value.error_code == LEX_ERROR_ID
        assert raised.value.kwargs['grammar_id'] == 'expr'

    # * test: ignore_does_not_follow_parent_ids
    def test_ignore_does_not_follow_parent_ids(self, test_ctx, session):
        '''
        Read ignore only on the resolved grammar, never through its parents.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The parent ignores a space. One child is unset, one ignores a tab.
        parent = GrammarAggregate(
            id='base',
            parent_ids=[],
            start='start',
            ignore=' ',
        )
        child = GrammarAggregate(
            id='expr',
            parent_ids=['base'],
            start='start',
        )
        tab_child = GrammarAggregate(
            id='expr',
            parent_ids=['base'],
            start='start',
            ignore='\t',
        )
        parent_tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='base',
                pattern='[A-Za-z]+',
            ),
        ]
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Za-z]+',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            PlyReader.build_lexer('base', [parent], parent_tokens)
            unset_lexer = PlyReader.build_lexer('expr', [parent, child], tokens)
            tab_lexer = PlyReader.build_lexer('expr', [parent, tab_child], tokens)

        # Each module carries only its own grammar's ignore.
        assert calls[0]['object'].t_ignore == ' '
        assert not hasattr(calls[1]['object'], 't_ignore')
        assert calls[2]['object'].t_ignore == '\t'

        # The unset child did not receive the parent's space.
        unset_lexer.input('a b')
        unset_lexer.token()
        with pytest.raises(ServiceError) as raised:
            unset_lexer.token()
        assert raised.value.error_code == LEX_ERROR_ID

        # The tab child skips a tab and not a space.
        tab_lexer.input('a\tb')
        assert [tab_lexer.token().value, tab_lexer.token().value] == ['a', 'b']
        tab_lexer.input('a b')
        tab_lexer.token()
        with pytest.raises(ServiceError) as raised:
            tab_lexer.token()
        assert raised.value.error_code == LEX_ERROR_ID

    # * test: synthetic_token_does_not_block_lexer_build
    def test_synthetic_token_does_not_block_lexer_build(self, test_ctx, session):
        '''
        Build a lexer from one real token and one synthetic token.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The synthetic name is declared after a real token.
        grammar = _grammar('expr')
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Za-z]+',
            ),
            SyntheticTokenRuleAggregate(
                name='INDENT',
                grammar_id='expr',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        with patch('tiferet_ly.utils.core.lex.lex', wraps=wrapped):
            lexer = PlyReader.build_lexer('expr', [grammar], tokens)

        # The name reaches PLY without an attribute, and the build succeeds.
        module = calls[0]['object']
        assert module.tokens == ['WORD', 'INDENT']
        assert not hasattr(module, 't_INDENT')
        lexer.input('ab')
        token = lexer.token()
        assert (token.type, token.value) == ('WORD', 'ab')
        assert lexer.token() is None
