"""Tiferet Ly Ply Lexer Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from unittest.mock import patch

# ** infra
import pytest

# ** app
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.reader import (
    LEX_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.utils import core as core_utils
from tiferet_ly.utils import lex as lex_utils
from tiferet_ly.utils.lex import PlyLexer

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

    # Start is required by construction and is not a lexer input.
    return GrammarAggregate(
        id=grammar_id,
        parent_ids=list(parent_ids or []),
        start='start',
    )

# ** function: spans
def _spans(lexemes: list[LexemeAggregate]) -> list[tuple]:
    '''
    Return the four published lexeme fields in order.

    :param lexemes: The lexeme aggregates from one read.
    :type lexemes: list[LexemeAggregate]
    :return: Type, value, line, and offset for each lexeme.
    :rtype: list[tuple]
    '''

    # Keep the field order of LexemeAggregate.new.
    return [
        (lexeme.type, lexeme.value, lexeme.lineno, lexeme.lexpos)
        for lexeme in lexemes
    ]

# *** tests

# ** test: interfaces_do_not_import_ply
def test_interfaces_do_not_import_ply():
    '''
    Keep PLY out of the interface package.
    '''

    # Scan the package without importing it again.
    root = Path(lex_utils.__file__).parents[1] / 'interfaces'
    for path in sorted(root.glob('*.py')):
        modules = _imported_modules(ast.parse(path.read_text()))
        for module in modules:
            assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_ply_lexer
@use_tester(
    type='generic',
    target_cls=PlyLexer,
)
class TestPlyLexer:
    '''
    Tests for reading a selected token set into lexeme aggregates.
    '''

    # * test: selected_token_drops_ancestor
    def test_selected_token_drops_ancestor(self, test_ctx, session):
        '''
        Return the selected token, not a same-named ancestor token.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The child token is earlier in input. Last-write would keep the ancestor.
        base = _grammar('base')
        expr = _grammar('expr', ['base'])
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='new',
            ),
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='base',
                pattern='old',
            ),
        ]
        lexer = PlyLexer()
        lexemes = lexer.tokenize(
            'expr',
            'new',
            tokens,
            ['not-a-production'],
            [base, expr],
            rewrites={'ignored': True},
        )
        again = lexer.tokenize(
            'expr',
            'new',
            tokens,
            [],
            [base, expr],
        )

        # The selected pattern matched. The result is an aggregate.
        assert _spans(lexemes) == [('WORD', 'new', 1, 0)]
        assert _spans(again) == _spans(lexemes)
        assert type(lexemes[0]) is LexemeAggregate
        assert lexemes[0].__class__.__module__ == 'tiferet_ly.mappers.lexeme'

        # The ancestor pattern is not installed, so its text is unmatched.
        with pytest.raises(ServiceError) as raised:
            lexer.tokenize('expr', 'old', tokens, [], [base, expr])
        assert raised.value.error_code == LEX_ERROR_ID
        assert raised.value.kwargs['value'] == 'old'

    # * test: later_simple_token_is_not_reordered
    def test_later_simple_token_is_not_reordered(self, test_ctx, session):
        '''
        Keep an earlier complex token ahead of a later simple token.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # LETTER can match the same text. It must not be tried first.
        expr = _grammar('expr')
        tokens = [
            ComplexTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[a-z]+',
                action='t.value = "complex:" + t.value\nreturn t',
            ),
            SimpleTokenRuleAggregate(
                name='LETTER',
                grammar_id='expr',
                pattern='[a-z]',
            ),
            SimpleTokenRuleAggregate(
                name='MARK',
                grammar_id='expr',
                pattern='X',
            ),
        ]
        calls = []
        real_lex = core_utils.lex.lex

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_lex(*args, **kwargs)

        # One build. The later simple token stays after the complex match.
        with patch('tiferet_ly.utils.core.lex.lex', side_effect=wrapped):
            lexemes = PlyLexer().tokenize(
                'expr',
                'abX',
                tokens,
                [],
                [expr],
            )

        assert _spans(lexemes) == [
            ('WORD', 'complex:ab', 1, 0),
            ('MARK', 'X', 1, 2),
        ]
        assert all(type(lexeme) is LexemeAggregate for lexeme in lexemes)
        assert all(
            not base.__module__.startswith('ply')
            for lexeme in lexemes
            for base in type(lexeme).__mro__
        )
        assert len(calls) == 1
        assert calls[0]['optimize'] == 0
        package = Path(core_utils.__file__).parent
        assert not (package / 'lextab.py').exists()
        assert not (Path.cwd() / 'lextab.py').exists()

    # * test: unmatched_character_carries_span
    def test_unmatched_character_carries_span(self, test_ctx, session):
        '''
        Raise a lexical error carrying the four span values.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The word matches. The following character does not.
        expr = _grammar('expr')
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Z]+',
            ),
        ]
        with pytest.raises(ServiceError) as raised:
            PlyLexer().tokenize('expr', 'AB@', tokens, [], [expr])

        # The error names the grammar and the unmatched character's span.
        error = raised.value
        assert error.error_code == LEX_ERROR_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['lineno'] == 1
        assert error.kwargs['lexpos'] == 2
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
            PlyLexer().tokenize('expr', 'x', [], [], [_grammar('expr')])

        # The failure names the grammar and is not a raw PLY error.
        error = raised.value
        assert error.error_code == READER_BUILD_FAILED_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert isinstance(error.__cause__, SyntaxError)
