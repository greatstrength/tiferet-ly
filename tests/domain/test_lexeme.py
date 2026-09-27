"""Tiferet Ly Lexeme Domain Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet import use_tester
from tiferet.domain.core import DomainObject
from tiferet_ly.domain import lexeme as lexeme_domain
from tiferet_ly.domain.lexeme import Lexeme

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

# ** test: module_does_not_import_ply
def test_module_does_not_import_ply():
    '''
    Keep the lexeme model free of a PLY import.
    '''

    # The domain module does not import ply.
    tree = ast.parse(Path(lexeme_domain.__file__).read_text())
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_lexeme
@use_tester(
    type='domain',
    target_cls=Lexeme,
    sample_data={
        'type': 'NUMBER',
        'value': '3',
        'lineno': 1,
        'lexpos': 0,
    },
    equality_fields=['type', 'value', 'lineno', 'lexpos'],
)
class TestLexeme:
    '''
    Tests for the recognized-word span.
    '''

    # * test: fields
    def test_fields(self, test_ctx, session):
        '''
        Keep exactly the four published span fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The model is a domain object with only the published fields.
        assert issubclass(Lexeme, DomainObject)
        assert set(Lexeme.model_fields) == {'type', 'value', 'lineno', 'lexpos'}
        assert Lexeme.model_fields['type'].annotation is str
        assert Lexeme.model_fields['value'].annotation is str
        assert Lexeme.model_fields['lineno'].annotation is int
        assert Lexeme.model_fields['lexpos'].annotation is int
        test_ctx.assert_new()

    # * test: required_and_closed
    def test_required_and_closed(self, test_ctx, session):
        '''
        Reject a missing span field and an undeclared field.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Every published field is required.
        with pytest.raises(ValidationError):
            Lexeme(type='NUMBER', value='3', lineno=1)

        # An undeclared field is not part of the span.
        with pytest.raises(ValidationError):
            Lexeme(
                type='NUMBER',
                value='3',
                lineno=1,
                lexpos=0,
                unused=True,
            )
