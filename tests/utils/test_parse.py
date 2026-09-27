"""Tiferet Ly PlyParser Tests"""

# *** imports

# ** core
import ast
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# ** infra
import pytest

# ** app
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.reader import (
    PARSE_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.utils import parse as parse_utils
from tiferet_ly.utils.core import PlyReader
from tiferet_ly.utils.parse import PlyParser

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
