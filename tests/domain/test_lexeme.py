"""Tiferet Ly Lexeme Domain Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from typing import Any

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import use_tester
from tiferet.domain.core import DomainObject

# ** app
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

        # The payload is optional and untyped. The span fields stay required.
        assert Lexeme.model_fields['value'].annotation == Any | None
        assert not Lexeme.model_fields['value'].is_required()
        assert Lexeme.model_fields['value'].default is None
        assert Lexeme.model_fields['lineno'].annotation is int
        assert Lexeme.model_fields['lineno'].is_required()
        assert Lexeme.model_fields['lexpos'].annotation is int
        assert Lexeme.model_fields['lexpos'].is_required()
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

        # The type, line, and position are required.
        with pytest.raises(ValidationError):
            Lexeme(value='3', lineno=1, lexpos=0)
        with pytest.raises(ValidationError):
            Lexeme(type='NUMBER', value='3', lexpos=0)
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

    # * test: text_and_absent_payload
    def test_text_and_absent_payload(self, test_ctx, session):
        '''
        Store matched text, empty text, and an absent payload.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A recognized text token keeps its matched text.
        text = Lexeme(type='NUMBER', value='3', lineno=1, lexpos=0)
        assert text.value == '3'
        assert type(text.value) is str
        assert text.lineno == 1
        assert text.lexpos == 0

        # Empty text is present, not absent.
        empty = Lexeme(type='NUMBER', value='', lineno=1, lexpos=0)
        assert empty.value == ''

        # An omitted payload is stored as None.
        omitted = Lexeme(type='INDENT', lineno=2, lexpos=4)
        assert omitted.value is None
        assert omitted.type == 'INDENT'
        assert omitted.lineno == 2
        assert omitted.lexpos == 4

        # An explicit None payload is stored as None.
        explicit = Lexeme(type='DEDENT', value=None, lineno=2, lexpos=4)
        assert explicit.value is None

    # * test: payload_is_not_coerced_to_text
    def test_payload_is_not_coerced_to_text(self, test_ctx, session):
        '''
        Keep a non-string payload as assigned.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An int payload stays an int.
        lexeme = Lexeme(type='NUMBER', value=3, lineno=1, lexpos=0)
        assert lexeme.value == 3
        assert type(lexeme.value) is int
        assert lexeme.value != '3'
