"""Tiferet Ly Lexeme Mapper Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path
from typing import Any

# ** infra
from tiferet import (
    Aggregate,
    use_tester,
)

# ** app
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

    # * test: synthesize_constructs_directly
    def test_synthesize_constructs_directly(self, test_ctx, session):
        '''
        Build a lexeme aggregate with no token and no payload.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The factory is static, ordered type, lineno, lexpos, value, and only value defaults.
        assert isinstance(LexemeAggregate.__dict__['synthesize'], staticmethod)
        signature = inspect.signature(LexemeAggregate.synthesize)
        assert list(signature.parameters) == ['type', 'lineno', 'lexpos', 'value']
        assert [
            parameter.annotation
            for parameter in signature.parameters.values()
        ] == [str, int, int, Any | None]
        assert signature.parameters['value'].default is None
        assert 'from_ply_token' not in LexemeAggregate.__dict__

        # The positional call binds 3 as lineno and 12 as lexpos, with no payload.
        lexeme = LexemeAggregate.synthesize('INDENT', 3, 12)
        assert type(lexeme) is LexemeAggregate
        assert lexeme.type == 'INDENT'
        assert lexeme.value is None
        assert lexeme.lineno == 3
        assert isinstance(lexeme.lineno, int)
        assert lexeme.lexpos == 12
        assert isinstance(lexeme.lexpos, int)
        assert lexeme.__class__.__module__ == 'tiferet_ly.mappers.lexeme'
        assert all(
            not base.__module__.startswith('ply')
            for base in type(lexeme).__mro__
        )

    # * test: synthesize_keeps_explicit_payload
    def test_synthesize_keeps_explicit_payload(self, test_ctx, session):
        '''
        Store an explicit payload as given, without coercing it to text.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The keyword payload is stored as an int, not as '3'.
        lexeme = LexemeAggregate.synthesize('NUMBER', lineno=1, lexpos=0, value=3)
        assert type(lexeme) is LexemeAggregate
        assert lexeme.type == 'NUMBER'
        assert lexeme.lineno == 1
        assert lexeme.lexpos == 0
        assert lexeme.value == 3
        assert type(lexeme.value) is int
        assert lexeme.value != '3'
