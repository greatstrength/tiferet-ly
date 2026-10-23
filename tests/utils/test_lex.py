"""Tiferet Ly Ply Lexer Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from typing import Callable
from unittest.mock import patch

# ** infra
import pytest
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.assets.reader import (
    ACTION_EXECUTION_FAILED_ID,
    LEX_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.utils import core as core_utils
from tiferet_ly.utils import lex as lex_utils
from tiferet_ly.utils.layout import LayoutFilter
from tiferet_ly.utils.lex import PlyLexer

# *** constants

# ** constant: layout_text
_LAYOUT_TEXT = '@ x:\n    y'

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

# ** function: layout_tokens
def _layout_tokens() -> list:
    '''
    Build the shared block, identifier, colon, and newline tokens.

    :return: The token aggregates, in input order, all owned by expr.
    :rtype: list
    '''

    # Keep the input order. NEWLINE advances the line and returns its token.
    return [
        SimpleTokenRuleAggregate(
            name='BLOCK',
            grammar_id='expr',
            pattern='@',
        ),
        ComplexTokenRuleAggregate(
            name='IDENTIFIER',
            grammar_id='expr',
            pattern='[a-zA-Z_]+',
            action='return t',
        ),
        SimpleTokenRuleAggregate(
            name='COLON',
            grammar_id='expr',
            pattern=':',
        ),
        ComplexTokenRuleAggregate(
            name='NEWLINE',
            grammar_id='expr',
            pattern=r'\n',
            action='t.lexer.lineno += 1\nreturn t',
        ),
    ]

# ** function: layout_profile
def _layout_profile(indent_token: str = 'INDENT', dedent_token: str = 'DEDENT') -> LayoutProfile:
    '''
    Build the shared layout profile, or the parent decoy with other names.

    :param indent_token: The synthetic indent name.
    :type indent_token: str
    :param dedent_token: The synthetic dedent name.
    :type dedent_token: str
    :return: The layout profile.
    :rtype: LayoutProfile
    '''

    # Only the synthetic names differ between the target and the decoy.
    return LayoutProfile(
        block_tokens=['BLOCK'],
        open_delimiters=[],
        close_delimiters=[],
        newline_token='NEWLINE',
        suppress_newline_in_delimiters=True,
        indent_token=indent_token,
        dedent_token=dedent_token,
        tab_size=4,
    )

# ** function: recording_apply
def _recording_apply(returned: list) -> Callable:
    '''
    Wrap the real LayoutFilter.apply so each list it returns is recorded.

    :param returned: The list that receives each value apply returns, in call order.
    :type returned: list
    :return: A callable with the apply signature, for use as a patch wraps target.
    :rtype: Callable
    '''

    # Capture the real filter now, before a patch replaces the class attribute.
    real_apply = LayoutFilter.apply

    # Record each returned list, then hand back that same object.
    def record(*args):
        returned.append(real_apply(*args))
        return returned[-1]

    # Return the wrapper for patch to call in place of apply.
    return record

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

    # * test: caller_rewrite_changes_complex_token_action
    def test_caller_rewrite_changes_complex_token_action(self, test_ctx, session):
        '''
        Apply a caller string binding to a complex token action.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The functions are only the caller binding. The lexeme value stays text.
        def mark_a(value):
            return 'a:' + value

        def mark_b(value):
            return 'b:' + value

        # The action marks the matched text through the caller binding.
        expr = _grammar('expr')
        tokens = [
            ComplexTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[a-z]+',
                action='t.value = $mark(t.value)\nreturn t',
            ),
        ]
        marked_a = PlyLexer().tokenize(
            'expr',
            'ab',
            tokens,
            [],
            [expr],
            rewrites={'$mark': mark_a},
        )
        marked_b = PlyLexer().tokenize(
            'expr',
            'ab',
            tokens,
            [],
            [expr],
            rewrites={'$mark': mark_b},
        )

        # The two results differ only because the caller table changed.
        assert marked_a[0].type == 'WORD'
        assert marked_a[0].value == 'a:ab'
        assert type(marked_a[0].value) is str
        assert marked_b[0].type == 'WORD'
        assert marked_b[0].value == 'b:ab'
        assert type(marked_b[0].value) is str

    # * test: action_exception_raises_action_execution_failed
    def test_action_exception_raises_action_execution_failed(self, test_ctx, session):
        '''
        Wrap an action exception as an attributed action failure.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The action raises before it can return the token.
        expr = _grammar('expr')
        tokens = [
            ComplexTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[a-z]+',
                action='raise ValueError(\'action failed\')\nreturn t',
            ),
        ]
        with pytest.raises(ServiceError) as raised:
            PlyLexer().tokenize('expr', 'ab', tokens, [], [expr])

        # The failure names the grammar, the compiled rule, and the cause.
        error = raised.value
        assert error.error_code == ACTION_EXECUTION_FAILED_ID
        assert error.message == 'action failed'
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['rule_name'] == 'WORD'
        assert type(error.__cause__) is ValueError
        assert str(error.__cause__) == 'action failed'

    # * test: lex_error_passes_through
    def test_lex_error_passes_through(self, test_ctx, session):
        '''
        Let a lexical error pass through the action-failure wrap.

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

        # The span stays a lexical error. It is not recast as an action failure.
        error = raised.value
        assert error.error_code == LEX_ERROR_ID
        assert (error.error_code == ACTION_EXECUTION_FAILED_ID) is False
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['lineno'] == 1
        assert error.kwargs['lexpos'] == 2
        assert error.kwargs['value'] == '@'
        assert 'rule_name' not in error.kwargs

    # * test: declared_layout_is_applied
    def test_declared_layout_is_applied(self, test_ctx, session):
        '''
        Apply the target grammar's own profile, not a parent's.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The parent carries a decoy profile. The target carries its own.
        base = _grammar('base')
        base.layout = _layout_profile(
            indent_token='PARENT_INDENT',
            dedent_token='PARENT_DEDENT',
        )
        expr = _grammar('expr', ['base'])
        expr.ignore = ' '
        expr.layout = _layout_profile()

        # Wrap the filter so the call and its returned list are both observed.
        returned = []
        recording_apply = _recording_apply(returned)
        with patch('tiferet_ly.utils.lex.LayoutFilter.apply', wraps=recording_apply) as apply:
            result = PlyLexer().tokenize('expr', _LAYOUT_TEXT, _layout_tokens(), [], [base, expr])

        # The filter is called once with the recognized list, the target profile, and the text.
        assert apply.call_count == 1
        lexemes, profile, text = apply.call_args.args
        assert [lexeme.type for lexeme in lexemes] == [
            'BLOCK',
            'IDENTIFIER',
            'COLON',
            'NEWLINE',
            'IDENTIFIER',
        ]
        assert [lexeme.value for lexeme in lexemes] == ['@', 'x', ':', '\n', 'y']
        assert profile is expr.layout
        assert text == _LAYOUT_TEXT
        assert result is returned[0]

        # Indent and dedent come from the target profile and carry no value.
        types = [lexeme.type for lexeme in result]
        assert 'INDENT' in types
        assert 'DEDENT' in types
        assert all(
            lexeme.value is None
            for lexeme in result
            if lexeme.type in ('INDENT', 'DEDENT')
        )
        assert ('PARENT_INDENT' in types or 'PARENT_DEDENT' in types) is False

        # Every returned object is a lexeme aggregate with no PLY base.
        assert all(type(lexeme) is LexemeAggregate for lexeme in result)
        assert all(lexeme.__class__.__module__ == 'tiferet_ly.mappers.lexeme' for lexeme in result)
        assert all(
            not base_cls.__module__.startswith('ply')
            for lexeme in result
            for base_cls in type(lexeme).__mro__
        )

    # * test: absent_layout_is_unchanged
    def test_absent_layout_is_unchanged(self, test_ctx, session):
        '''
        Return the unfiltered stream when the target has no profile.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Only the parent carries a profile. The target's layout stays None.
        base = _grammar('base')
        base.layout = _layout_profile(
            indent_token='PARENT_INDENT',
            dedent_token='PARENT_DEDENT',
        )
        expr = _grammar('expr', ['base'])
        expr.ignore = ' '
        with patch('tiferet_ly.utils.lex.LayoutFilter.apply') as apply:
            result = PlyLexer().tokenize('expr', _LAYOUT_TEXT, _layout_tokens(), [], [base, expr])

        # The filter is not called, and the recognized stream is returned as read.
        apply.assert_not_called()
        types = [lexeme.type for lexeme in result]
        assert types == ['BLOCK', 'IDENTIFIER', 'COLON', 'NEWLINE', 'IDENTIFIER']
        assert [lexeme.value for lexeme in result] == ['@', 'x', ':', '\n', 'y']
        for name in ('INDENT', 'DEDENT', 'PARENT_INDENT', 'PARENT_DEDENT'):
            assert name not in types

        # Every returned object is a lexeme aggregate with no PLY base.
        assert all(type(lexeme) is LexemeAggregate for lexeme in result)
        assert all(lexeme.__class__.__module__ == 'tiferet_ly.mappers.lexeme' for lexeme in result)
        assert all(
            not base_cls.__module__.startswith('ply')
            for lexeme in result
            for base_cls in type(lexeme).__mro__
        )

    # * test: empty_read_with_layout_still_applies
    def test_empty_read_with_layout_still_applies(self, test_ctx, session):
        '''
        Call the filter on an empty successful read when a profile is present.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The target has a profile and no parent. The text is empty.
        expr = _grammar('expr')
        expr.layout = _layout_profile()
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Z]+',
            ),
        ]

        # Wrap the filter so the call and its returned list are both observed.
        returned = []
        recording_apply = _recording_apply(returned)
        with patch('tiferet_ly.utils.lex.LayoutFilter.apply', wraps=recording_apply) as apply:
            result = PlyLexer().tokenize('expr', '', tokens, [], [expr])

        # The empty list, the target profile, and the empty text reach the filter.
        assert apply.call_count == 1
        lexemes, profile, text = apply.call_args.args
        assert lexemes == []
        assert profile is expr.layout
        assert text == ''
        assert result is returned[0]

    # * test: layout_is_not_applied_when_tokenization_fails
    def test_layout_is_not_applied_when_tokenization_fails(self, test_ctx, session):
        '''
        Leave the layout step unreached when the read raises a lexical error.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The word matches. The following character does not.
        expr = _grammar('expr')
        expr.layout = _layout_profile()
        tokens = [
            SimpleTokenRuleAggregate(
                name='WORD',
                grammar_id='expr',
                pattern='[A-Z]+',
            ),
        ]
        with patch('tiferet_ly.utils.lex.LayoutFilter.apply') as apply:
            with pytest.raises(ServiceError) as raised:
                PlyLexer().tokenize('expr', 'AB@', tokens, [], [expr])

        # The lexical error propagates, and the filter is never called.
        assert raised.value.error_code == LEX_ERROR_ID
        apply.assert_not_called()
