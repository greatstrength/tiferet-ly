"""Tiferet Ly PlyParser Tests"""

# *** imports

# ** core
import ast
import inspect
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

# ** infra
import ply.yacc as yacc
import pytest
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.assets.grammar import GRAMMAR_NOT_FOUND_ID
from tiferet_ly.assets.reader import (
    ACTION_EXECUTION_FAILED_ID,
    PARSE_ERROR_ID,
    PARSE_INPUT_INVALID_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.assets.translation import RULE_PATTERN_INVALID_ID
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    SyntheticTokenRuleAggregate,
)
from tiferet_ly.utils import parse as parse_utils
from tiferet_ly.utils.core import PlyReader
from tiferet_ly.utils.parse import PlyParser
from tiferet_ly.utils.translation import RuleTranslator

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
def _grammar() -> GrammarAggregate:
    '''
    Build the expression grammar used by the parser tests.

    :return: A grammar whose start symbol is ``expr``.
    :rtype: GrammarAggregate
    '''

    # Start is the shared production name, not a separate wrapper rule.
    return GrammarAggregate(
        id='expr',
        parent_ids=[],
        start='expr',
    )

# ** function: tokens
def _tokens() -> list[SimpleTokenRuleAggregate]:
    '''
    Build the token catalogue for the expression grammar.

    :return: Number, plus, and minus tokens.
    :rtype: list[SimpleTokenRuleAggregate]
    '''

    # Patterns are the reader text. Actions stay on the productions.
    return [
        SimpleTokenRuleAggregate(
            name='NUMBER',
            grammar_id='expr',
            pattern=r'[0-9]+',
        ),
        SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='expr',
            pattern=r'\+',
        ),
        SimpleTokenRuleAggregate(
            name='MINUS',
            grammar_id='expr',
            pattern=r'-',
        ),
    ]

# ** function: productions
def _productions() -> list[ComplexProductionRuleAggregate]:
    '''
    Build three same-named alternatives, in installation order.

    :return: The base, addition, and negation productions.
    :rtype: list[ComplexProductionRuleAggregate]
    '''

    # The first two are both required to read ``1+2``. The third proves ``_3``.
    return [
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action='p[0] = int(p[1])',
        ),
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : expr PLUS NUMBER',
            action='p[0] = p[1] + int(p[3])',
        ),
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : MINUS NUMBER',
            action='p[0] = -int(p[2])',
        ),
    ]

# ** function: production_attributes
def _production_attributes(module) -> list[str]:
    '''
    Collect installed production attribute names.

    :param module: The parser module passed to PLY.
    :type module: object
    :return: Production attribute names, excluding the error handler.
    :rtype: list[str]
    '''

    # ``p_error`` is the syntax-error hook, not a production.
    return [
        name
        for name in dir(module)
        if name.startswith('p_') and name != 'p_error' and callable(getattr(module, name))
    ]

# *** tests

# ** test: interfaces_do_not_import_ply
def test_interfaces_do_not_import_ply():
    '''
    Keep PLY out of the interface package, and allow it only as ``ply.yacc`` here.
    '''

    # Scan the interface package without importing it again.
    root = Path(parse_utils.__file__).parents[1] / 'interfaces'
    for path in sorted(root.glob('*.py')):
        modules = _imported_modules(ast.parse(path.read_text()))
        for module in modules:
            assert module != 'ply' and not module.startswith('ply.')

    # The parser utility may import ply.yacc and must not import the lexer utility.
    parser_modules = _imported_modules(ast.parse(Path(parse_utils.__file__).read_text()))
    assert 'ply.yacc' in parser_modules
    assert 'tiferet_ly.utils.lex' not in parser_modules
    assert 'ply.lex' not in parser_modules
    assert PlyParser.__bases__ == (PlyReader, ParserService)

# *** testers

# ** tester: test_ply_parser
@use_tester(
    type='generic',
    target_cls=PlyParser,
)
class TestPlyParser:
    '''
    Tests for parser installation, tables, and syntax errors.
    '''

    # * test: same_named_alternatives_require_both
    def test_same_named_alternatives_require_both(self, test_ctx, session):
        '''
        Succeed at ``1+2`` only when both same-named alternatives are installed.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Both alternatives participate. The third alternative is not required.
        parser = PlyParser()
        grammars = [_grammar()]
        tokens = _tokens()
        productions = _productions()
        assert parser.parse('expr', '1+2', tokens, productions, grammars) == 3
        assert parser.parse('expr', '1', tokens, productions, grammars) == 1
        assert parser.parse('expr', '-2', tokens, productions, grammars) == -2

        # The base alternative alone can read a number, not an addition.
        base_only = [productions[0]]
        assert parser.parse('expr', '1', tokens, base_only, grammars) == 1
        with pytest.raises(ServiceError) as raised:
            parser.parse('expr', '1+2', tokens, base_only, grammars)

        # The missing alternative is a syntax error, not a successful value.
        assert raised.value.error_code == PARSE_ERROR_ID
        assert raised.value.kwargs['grammar_id'] == 'expr'

        # The recursive alternative alone cannot be built into a successful parse.
        with pytest.raises(ServiceError) as raised_build:
            parser.parse('expr', '1+2', tokens, [productions[1]], grammars)
        assert raised_build.value.error_code == READER_BUILD_FAILED_ID

    # * test: installed_attribute_names_are_unique
    def test_installed_attribute_names_are_unique(self, test_ctx, session):
        '''
        Install each same-named alternative once, without renaming the production.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Capture the module PLY actually receives, then build the real parser.
        captured = {}
        real_yacc = parse_utils.yacc.yacc

        def wrapped(*args, **kwargs):
            captured['module'] = kwargs['module']
            return real_yacc(*args, **kwargs)

        ignored = SimpleProductionRuleAggregate(
            name='other',
            grammar_id='other',
            spec='other : NUMBER',
        )
        with patch('tiferet_ly.utils.parse.yacc.yacc', side_effect=wrapped):
            result = PlyParser().parse(
                'expr',
                '1+2',
                _tokens(),
                _productions() + [ignored],
                [_grammar()],
            )

        # The live build used both required alternatives and a third suffix.
        assert result == 3
        module = captured['module']
        names = _production_attributes(module)
        assert len(names) == len(set(names))
        assert set(names) == {'p_expr', 'p_expr_2', 'p_expr_3'}
        assert not hasattr(module, 'p_other')
        assert module.p_expr.__name__ == 'expr'
        assert module.p_expr.__doc__ == 'expr : NUMBER'
        assert module.p_expr_2.__name__ == 'expr'
        assert module.p_expr_2.__doc__ == 'expr : expr PLUS NUMBER'
        assert module.p_expr_3.__name__ == 'expr'
        assert module.p_expr_3.__doc__ == 'expr : MINUS NUMBER'

        # A taken ``p_expr_2`` is skipped. The production name stays ``expr``.
        colliding = [
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : NUMBER',
            ),
            SimpleProductionRuleAggregate(
                name='expr_2',
                grammar_id='expr',
                spec='expr_2 : NUMBER',
            ),
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : NUMBER',
            ),
        ]
        installed = PlyParser.install_productions(colliding)
        colliding_names = _production_attributes(installed)
        assert len(colliding_names) == len(set(colliding_names)) == 3
        assert installed.p_expr.__name__ == 'expr'
        assert installed.p_expr_2.__name__ == 'expr_2'
        disambiguated = [
            name for name in colliding_names
            if name not in ('p_expr', 'p_expr_2')
        ]
        assert len(disambiguated) == 1
        assert getattr(installed, disambiguated[0]).__name__ == 'expr'
        assert getattr(installed, disambiguated[0]).__doc__ == 'expr : NUMBER'

    # * test: parse_writes_no_tables
    def test_parse_writes_no_tables(self, test_ctx, session):
        '''
        Call ``yacc`` without tables and leave the working directory clean.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Record the build flags, then let PLY build for real.
        calls = []
        real_yacc = parse_utils.yacc.yacc

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_yacc(*args, **kwargs)

        # Parse from a fresh working directory so a dirty checkout cannot hide a write.
        origin = os.getcwd()
        package = Path(parse_utils.__file__).parent
        with tempfile.TemporaryDirectory() as temporary:
            os.chdir(temporary)
            try:
                with patch('tiferet_ly.utils.parse.yacc.yacc', side_effect=wrapped):
                    first = PlyParser().parse(
                        'expr',
                        '1+2',
                        _tokens(),
                        _productions(),
                        [_grammar()],
                    )
                    second = PlyParser().parse(
                        'expr',
                        '1+2',
                        _tokens(),
                        _productions(),
                        [_grammar()],
                    )
                assert first == 3
                assert second == 3
                assert not (Path(temporary) / 'parsetab.py').exists()
                assert not (Path(temporary) / 'lextab.py').exists()
                assert not (Path(temporary) / 'parser.out').exists()
            finally:
                os.chdir(origin)

        # Tables are not written beside the utility either.
        assert len(calls) == 2
        assert all(call['write_tables'] is False for call in calls)
        assert all(call['debug'] is False for call in calls)
        assert all(call['start'] == 'expr' for call in calls)
        assert not (package / 'parsetab.py').exists()
        assert not (package / 'lextab.py').exists()
        assert not (package / 'parser.out').exists()
        assert not (Path.cwd() / 'parsetab.py').exists()
        assert not (Path.cwd() / 'lextab.py').exists()

    # * test: syntax_error_carries_span
    def test_syntax_error_carries_span(self, test_ctx, session):
        '''
        Raise ``PARSE_ERROR_ID`` with the span keys when a token is in hand.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A leading operator is a token the grammar cannot shift.
        with pytest.raises(ServiceError) as raised:
            PlyParser().parse(
                'expr',
                '+',
                _tokens(),
                _productions(),
                [_grammar()],
            )

        # The four span keys ride with the grammar identifier.
        error = raised.value
        assert error.error_code == PARSE_ERROR_ID
        assert error.kwargs['grammar_id'] == 'expr'
        assert error.kwargs['type'] == 'PLUS'
        assert error.kwargs['value'] == '+'
        assert error.kwargs['lineno'] == 1
        assert error.kwargs['lexpos'] == 0

    # * test: compiled_token_action_is_bound_for_the_build
    def test_compiled_token_action_is_bound_for_the_build(self, test_ctx, session):
        '''
        Bind a module-less compiled token for the build, then restore the builder.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The complex token converts the matched text before the production runs.
        original = parse_utils.reader_core.lex.lex
        tokens = [
            ComplexTokenRuleAggregate(
                name='NUMBER',
                grammar_id='expr',
                pattern=r'[0-9]+',
                action='t.value = int(t.value)\nreturn t',
            ),
            SimpleTokenRuleAggregate(
                name='PLUS',
                grammar_id='expr',
                pattern=r'\+',
            ),
        ]
        productions = [
            ComplexProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : NUMBER',
                action='p[0] = p[1]',
            ),
            ComplexProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : expr PLUS NUMBER',
                action='p[0] = p[1] + p[3]',
            ),
        ]
        assert PlyParser().parse(
            'expr',
            '1+2',
            tokens,
            productions,
            [_grammar()],
        ) == 3

        # A failed build still restores the shared reader.
        with pytest.raises(ServiceError) as raised:
            PlyParser().parse('expr', '1', [], [], [_grammar()])
        assert raised.value.error_code == READER_BUILD_FAILED_ID
        assert parse_utils.reader_core.lex.lex is original

    # * test: caller_rewrite_bindings_used_by_complex_production
    def test_caller_rewrite_bindings_used_by_complex_production(self, test_ctx, session):
        '''
        Prove one caller table reaches a token action and a production action.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The three bindings stay distinct. The closure closes over a label.
        class BoundClass:
            pass

        def bound_function(value):
            return ('function', value)

        label = 'closed'

        def bound_closure(value):
            return (label, value)

        assert BoundClass.__name__ != bound_function.__name__
        assert bound_function.__name__ != bound_closure.__name__
        assert BoundClass.__name__ != bound_closure.__name__

        # The token action uses $fn. The production action uses $cls and $clos.
        token = ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='expr',
            pattern=r'[0-9]+',
            action='t.value = $fn(int(t.value))\nreturn t',
        )
        production = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action='p[0] = ($cls, p[1], $clos(p[1][1]))',
        )
        rewrites = {
            '$cls': BoundClass,
            '$fn': bound_function,
            '$clos': bound_closure,
        }
        result = PlyParser().parse(
            'expr',
            '7',
            [token],
            [production],
            [_grammar()],
            rewrites=rewrites,
        )

        # The class, function, and closure all came from the caller table.
        assert result[0] is BoundClass
        assert result[1] == ('function', 7)
        assert result[2] == ('closed', 7)

    # * test: production_action_exception_is_structured_and_attributed
    def test_production_action_exception_is_structured_and_attributed(self, test_ctx, session):
        '''
        Wrap a production action exception as an attributed action failure.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The production raises before it can assign a value.
        tokens = [
            SimpleTokenRuleAggregate(
                name='NUMBER',
                grammar_id='expr',
                pattern=r'[0-9]+',
            ),
        ]
        production = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action="raise ValueError('boom')",
        )
        with pytest.raises(ServiceError) as raised:
            PlyParser().parse(
                'expr',
                '1',
                tokens,
                [production],
                [_grammar()],
            )

        # The failure names the grammar, the compiled rule, and the cause.
        assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
        assert raised.value.message == 'boom'
        assert raised.value.kwargs['grammar_id'] == 'expr'
        assert raised.value.kwargs['rule_name'] == 'expr'
        assert 'rule_name' in raised.value.kwargs
        assert isinstance(raised.value.__cause__, ValueError)
        assert raised.value.__cause__.args == ('boom',)

    # * test: syntax_error_remains_parse_error
    def test_syntax_error_remains_parse_error(self, test_ctx, session):
        '''
        Keep a syntax error as ``PARSE_ERROR_ID`` when rewrites are supplied.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The marker is unused. A leading operator is still a syntax error.
        class BoundMarker:
            pass

        with pytest.raises(ServiceError) as raised:
            PlyParser().parse(
                'expr',
                '+',
                _tokens(),
                _productions(),
                [_grammar()],
                rewrites={'$marker': BoundMarker},
            )

        # The span stays a parse error. It is not recast as an action failure.
        assert raised.value.error_code == PARSE_ERROR_ID
        assert raised.value.error_code != ACTION_EXECUTION_FAILED_ID
        assert raised.value.kwargs['grammar_id'] == 'expr'
        assert raised.value.kwargs['type'] == 'PLUS'
        assert raised.value.kwargs['value'] == '+'
        assert raised.value.kwargs['lineno'] == 1
        assert raised.value.kwargs['lexpos'] == 0

    # * test: positional_signature_keeps_text_callers
    def test_positional_signature_keeps_text_callers(self, test_ctx, session):
        '''
        Keep the published positional prefix on both parse signatures, with lexemes last.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Both signatures list the same parameters in the same order.
        expected = [
            'self',
            'grammar_id',
            'text',
            'tokens',
            'productions',
            'grammars',
            'rewrites',
            'lexemes',
        ]
        implementation = inspect.signature(PlyParser.parse)
        interface = inspect.signature(ParserService.parse)
        assert list(implementation.parameters) == expected
        assert list(interface.parameters) == expected

        # Text is optional by value only. Rewrites and lexemes default to None.
        for signature in (implementation, interface):
            assert signature.parameters['text'].annotation == str | None
            assert signature.parameters['rewrites'].default is None
            assert signature.parameters['lexemes'].default is None
        assert interface.return_annotation is Any

        # Names, annotations, and defaults match between the two.
        def shape(signature):
            return [
                (name, parameter.annotation, parameter.default)
                for name, parameter in signature.parameters.items()
            ]

        # The interface and implementation agree on every parameter shape.
        assert shape(interface) == shape(implementation)

        # A positional text call still reads. The sixth positional argument is rewrites.
        class UnusedMarker:
            pass

        assert PlyParser().parse('expr', '1+2', _tokens(), _productions(), [_grammar()]) == 3
        assert PlyParser().parse(
            'expr',
            '1+2',
            _tokens(),
            _productions(),
            [_grammar()],
            {'$unused': UnusedMarker},
        ) == 3

    # * test: missing_or_ambiguous_input_raises_before_ply
    def test_missing_or_ambiguous_input_raises_before_ply(self, test_ctx, session):
        '''
        Raise ``PARSE_INPUT_INVALID_ID`` for a missing or ambiguous input before any lookup or PLY call.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Either PLY step would fail loudly. The grammar id would not resolve.
        with patch(
            'tiferet_ly.utils.parse.yacc.yacc',
            side_effect=AssertionError('yacc'),
        ) as built, patch.object(
            PlyParser,
            '_build_lexer',
            side_effect=AssertionError('lexer'),
        ) as lexed:
            with pytest.raises(ServiceError) as missing:
                PlyParser().parse(
                    'missing',
                    None,
                    _tokens(),
                    _productions(),
                    [_grammar()],
                )
            with pytest.raises(ServiceError) as ambiguous:
                PlyParser().parse(
                    'missing',
                    '1',
                    _tokens(),
                    _productions(),
                    [_grammar()],
                    lexemes=[
                        LexemeAggregate.new('NUMBER', '1', 1, 0),
                    ],
                )

        # Both None is missing. The message names the grammar and the reason.
        assert missing.value.error_code == PARSE_INPUT_INVALID_ID
        assert missing.value.kwargs['reason'] == 'missing'
        assert missing.value.kwargs['grammar_id'] == 'missing'
        assert missing.value.message == (
            'Exactly one of text or lexemes must be supplied for grammar missing (missing).'
        )

        # Both supplied is ambiguous, and the grammar lookup never ran.
        assert ambiguous.value.error_code == PARSE_INPUT_INVALID_ID
        assert ambiguous.value.error_code != GRAMMAR_NOT_FOUND_ID
        assert ambiguous.value.kwargs['reason'] == 'ambiguous'
        assert ambiguous.value.message.endswith('(ambiguous).')
        assert not built.called
        assert not lexed.called

    # * test: empty_text_and_empty_lexemes_are_supplied
    def test_empty_text_and_empty_lexemes_are_supplied(self, test_ctx, session):
        '''
        Treat empty text and an empty lexeme list as supplied inputs.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Empty text takes the text path and builds a lexer.
        with patch.object(
            PlyParser,
            '_build_lexer',
            wraps=PlyParser._build_lexer,
        ) as lexed:
            with pytest.raises(ServiceError) as empty_text:
                PlyParser().parse(
                    'expr',
                    '',
                    _tokens(),
                    _productions(),
                    [_grammar()],
                )
        assert empty_text.value.error_code != PARSE_INPUT_INVALID_ID
        assert lexed.called

        # An empty list takes the lexeme path and ends at input without a span.
        with patch.object(
            PlyParser,
            '_build_lexer',
            wraps=PlyParser._build_lexer,
        ) as lexed:
            with pytest.raises(ServiceError) as empty_lexemes:
                PlyParser().parse(
                    'expr',
                    None,
                    _tokens(),
                    _productions(),
                    [_grammar()],
                    lexemes=[],
                )
        error = empty_lexemes.value
        assert error.error_code != PARSE_INPUT_INVALID_ID
        assert error.error_code == PARSE_ERROR_ID
        assert error.kwargs['grammar_id'] == 'expr'
        for key in ('type', 'value', 'lineno', 'lexpos'):
            assert key not in error.kwargs
        assert not lexed.called

    # * test: lexemes_preserve_order_payload_and_span
    def test_lexemes_preserve_order_payload_and_span(self, test_ctx, session):
        '''
        Read lexemes in list order, keep each payload, and carry each span into a syntax error.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Record the build flags, then let PLY build for real.
        calls = []
        real_yacc = parse_utils.yacc.yacc

        def wrapped(*args, **kwargs):
            calls.append(kwargs)
            return real_yacc(*args, **kwargs)

        # The lexpos values are out of order. List order still wins.
        lexemes = [
            LexemeAggregate.new('NUMBER', '1', 2, 10),
            LexemeAggregate.new('PLUS', '+', 2, 0),
            LexemeAggregate.new('NUMBER', '2', 3, 5),
        ]
        with patch('tiferet_ly.utils.parse.yacc.yacc', side_effect=wrapped):
            result = PlyParser().parse(
                'expr',
                None,
                _tokens(),
                _productions(),
                [_grammar()],
                lexemes=lexemes,
            )
        assert result == 3
        assert len(calls) == 1
        assert calls[0]['write_tables'] is False
        assert calls[0]['debug'] is False
        assert calls[0]['start'] == 'expr'
        assert isinstance(calls[0]['errorlog'], yacc.NullLogger)

        # The payload reaches the action unchanged. No text is re-read.
        passthrough = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action='p[0] = p[1]',
        )
        assert PlyParser().parse(
            'expr',
            None,
            _tokens(),
            [passthrough],
            [_grammar()],
            lexemes=[
                LexemeAggregate.new('NUMBER', 'kept', 1, 0),
            ],
        ) == 'kept'

        # A lexeme the grammar cannot shift carries its own span.
        with pytest.raises(ServiceError) as raised:
            PlyParser().parse(
                'expr',
                None,
                _tokens(),
                _productions(),
                [_grammar()],
                lexemes=[
                    LexemeAggregate.new('PLUS', '+', 4, 9),
                ],
            )
        assert raised.value.error_code == PARSE_ERROR_ID
        assert raised.value.kwargs['grammar_id'] == 'expr'
        assert raised.value.kwargs['type'] == 'PLUS'
        assert raised.value.kwargs['value'] == '+'
        assert raised.value.kwargs['lineno'] == 4
        assert raised.value.kwargs['lexpos'] == 9

    # * test: lexemes_do_not_lex_translate_or_apply_layout
    def test_lexemes_do_not_lex_translate_or_apply_layout(self, test_ctx, session):
        '''
        Skip the lexer build, token install, and token translation on the lexeme path.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The token pattern is invalid. Translating it would raise.
        tokens = [
            ComplexTokenRuleAggregate(
                name='NUMBER',
                grammar_id='expr',
                pattern='[',
                action='return t',
            ),
        ]
        productions = [
            ComplexProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : NUMBER',
                action='p[0] = p[1]',
            ),
        ]
        lexemes = [
            LexemeAggregate.new('NUMBER', 'kept', 1, 0),
        ]

        # Record the list the stream receives and delegate to the real adapter.
        received = []
        real_stream = parse_utils.LexemeStream

        def stream(value):
            received.append(value)
            return real_stream(value)

        # Any lexer, install, or translation call fails loudly.
        with patch.object(
            PlyParser,
            '_build_lexer',
            side_effect=AssertionError('lexer'),
        ) as lexed, patch.object(
            PlyReader,
            'install_tokens',
            side_effect=AssertionError('install'),
        ) as installed, patch.object(
            RuleTranslator,
            'translate_token_rule',
            side_effect=AssertionError('translate'),
        ) as translated, patch(
            'tiferet_ly.utils.core.lex.lex',
            side_effect=AssertionError('lex'),
        ) as built, patch(
            'tiferet_ly.utils.parse.LexemeStream',
            side_effect=stream,
        ):
            try:
                result = PlyParser().parse(
                    'expr',
                    None,
                    tokens,
                    productions,
                    [_grammar()],
                    lexemes=lexemes,
                )
            except ServiceError as error:
                assert error.error_code not in (
                    PARSE_INPUT_INVALID_ID,
                    RULE_PATTERN_INVALID_ID,
                )
                raise

        # The payload came back and none of the four ran.
        assert result == 'kept'
        assert not lexed.called
        assert not installed.called
        assert not translated.called
        assert not built.called
        assert len(received) == 1
        assert received[0] is lexemes

        # The utility calls the shared helper and does not inline or reapply anything.
        source = Path(parse_utils.__file__).read_text()
        assert 'PlyReader.select_token_names' in source
        for forbidden in (
            'derive_tokens',
            'select_tokens',
            'layout',
            'LayoutFilter',
            'grammar.ignore',
        ):
            assert forbidden not in source

    # * test: lexemes_accept_synthetic_name
    def test_lexemes_accept_synthetic_name(self, test_ctx, session):
        '''
        Accept a synthetic token name from lexemes without a pattern or a token attribute.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # END has a name and a grammar only.
        tokens = [
            _tokens()[0],
            SyntheticTokenRuleAggregate(
                name='END',
                grammar_id='expr',
            ),
        ]
        productions = [
            ComplexProductionRuleAggregate(
                name='expr',
                grammar_id='expr',
                spec='expr : NUMBER END',
                action='p[0] = int(p[1])',
            ),
        ]
        lexemes = [
            LexemeAggregate.new('NUMBER', '42', 1, 0),
            LexemeAggregate.new('END', '', 1, 2),
        ]

        # Capture the module PLY receives. Translation fails loudly.
        captured = {}
        real_yacc = parse_utils.yacc.yacc

        def wrapped(*args, **kwargs):
            captured['module'] = kwargs['module']
            return real_yacc(*args, **kwargs)

        with patch(
            'tiferet_ly.utils.parse.yacc.yacc',
            side_effect=wrapped,
        ), patch.object(
            RuleTranslator,
            'translate_token_rule',
            side_effect=AssertionError('translate'),
        ) as translated:
            result = PlyParser().parse(
                'expr',
                None,
                tokens,
                productions,
                [_grammar()],
                lexemes=lexemes,
            )

        # The parser token list is the helper's names, synthetic included.
        module = captured['module']
        assert result == 42
        assert not translated.called
        assert module.tokens == PlyReader.select_token_names(
            _grammar(),
            [_grammar()],
            tokens,
        )
        assert 'END' in module.tokens
        assert 'NUMBER' in module.tokens
        assert not hasattr(module, 't_END')

    # * test: lexemes_forward_caller_rewrites
    def test_lexemes_forward_caller_rewrites(self, test_ctx, session):
        '''
        Forward the caller rewrite table to productions on the lexeme path without running token actions.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The token action would convert the value if it ran.
        class BoundClass:
            pass

        token = ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='expr',
            pattern=r'[0-9]+',
            action='t.value = int(t.value)\nreturn t',
        )
        production = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action='p[0] = ($cls, p[1])',
        )
        result = PlyParser().parse(
            'expr',
            None,
            [token],
            [production],
            [_grammar()],
            rewrites={'$cls': BoundClass},
            lexemes=[
                LexemeAggregate.new('NUMBER', '7', 1, 0),
            ],
        )

        # The production saw the caller class. The value stayed text.
        assert result[0] is BoundClass
        assert result[1] == '7'
        assert result[1] != 7

    # * test: lexemes_production_exception_uses_existing_wrap
    def test_lexemes_production_exception_uses_existing_wrap(self, test_ctx, session):
        '''
        Wrap a production action exception on the lexeme path as the same attributed action failure.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The production raises before it can assign a value.
        tokens = [
            SimpleTokenRuleAggregate(
                name='NUMBER',
                grammar_id='expr',
                pattern=r'[0-9]+',
            ),
        ]
        production = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action="raise ValueError('boom')",
        )
        with pytest.raises(ServiceError) as raised:
            PlyParser().parse(
                'expr',
                None,
                tokens,
                [production],
                [_grammar()],
                lexemes=[
                    LexemeAggregate.new('NUMBER', '1', 1, 0),
                ],
            )

        # The failure names the grammar, the compiled rule, and the cause.
        assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
        assert raised.value.message == 'boom'
        assert raised.value.kwargs['grammar_id'] == 'expr'
        assert raised.value.kwargs['rule_name'] == 'expr'
        assert isinstance(raised.value.__cause__, ValueError)
        assert raised.value.__cause__.args == ('boom',)
