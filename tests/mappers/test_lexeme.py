"""Tiferet Ly Lexeme Mapper Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path

# ** app
from tiferet import (
    Aggregate,
    use_tester,
)
from tiferet_ly.domain import lexeme as lexeme_domain
from tiferet_ly.domain.lexeme import Lexeme
from tiferet_ly.mappers import lexeme as lexeme_mappers
from tiferet_ly.mappers.lexeme import LexemeAggregate

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

# *** tests

# ** test: modules_do_not_import_ply
def test_modules_do_not_import_ply():
    '''
    Keep the lexeme model and mapper free of a PLY import.
    '''

    # Neither published module imports ply.
    for module in (lexeme_domain, lexeme_mappers):
        tree = ast.parse(Path(module.__file__).read_text())
        for name in _imported_modules(tree):
            assert name != 'ply' and not name.startswith('ply.')

# *** testers

# ** tester: test_lexeme_aggregate
@use_tester(
    type='aggregate',
    target_cls=LexemeAggregate,
    sample_data={
        'type': 'NUMBER',
        'value': '3',
        'lineno': 1,
        'lexpos': 0,
    },
    equality_fields=['type', 'value', 'lineno', 'lexpos'],
)
class TestLexemeAggregate:
    '''
    Tests for the lexeme aggregate factory.
    '''

    # * test: bases_and_factory
    def test_bases_and_factory(self, test_ctx, session):
        '''
        Extend the lexeme model and expose a static four-field factory.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases and fields match the published boundary.
        assert LexemeAggregate.__bases__ == (Lexeme, Aggregate)
        assert set(LexemeAggregate.model_fields) == {
            'type',
            'value',
            'lineno',
            'lexpos',
        }
        assert isinstance(LexemeAggregate.__dict__['new'], staticmethod)

        # The factory signature is the four span fields.
        signature = inspect.signature(LexemeAggregate.new)
        assert list(signature.parameters) == ['type', 'value', 'lineno', 'lexpos']
        assert [
            parameter.annotation
            for parameter in signature.parameters.values()
        ] == [str, str, int, int]
        test_ctx.assert_new()

    # * test: new_returns_aggregate
    def test_new_returns_aggregate(self, test_ctx, session):
        '''
        Build a lexeme aggregate from the published sample call.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The factory returns an aggregate, not a PLY token.
        lexeme = LexemeAggregate.new('NUMBER', '3', 1, 0)
        assert type(lexeme) is LexemeAggregate
        assert isinstance(lexeme, LexemeAggregate)
        assert lexeme.type == 'NUMBER'
        assert lexeme.value == '3'
        assert lexeme.lineno == 1
        assert lexeme.lexpos == 0
        assert isinstance(lexeme.lineno, int)
        assert isinstance(lexeme.lexpos, int)
        assert lexeme.__class__.__module__ == 'tiferet_ly.mappers.lexeme'
        assert all(
            not base.__module__.startswith('ply')
            for base in type(lexeme).__mro__
        )
