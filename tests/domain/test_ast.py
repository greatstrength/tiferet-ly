"""Tiferet Ly AST Domain Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from typing import Any

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet import use_tester
from tiferet.domain.core import DomainObject
from tiferet_ly.domain import ast as ast_domain
from tiferet_ly.domain.ast import AstNode
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
    Keep the AST model free of a PLY import.
    '''

    # The domain module does not import ply.
    tree = ast.parse(Path(ast_domain.__file__).read_text())
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_ast_node
@use_tester(
    type='domain',
    target_cls=AstNode,
    sample_data={
        'kind': 'expr',
        'children': [],
        'value': 3,
        'lineno': 1,
        'lexpos': 0,
    },
    equality_fields=['kind', 'children', 'value', 'lineno', 'lexpos'],
)
class TestAstNode:
    '''
    Tests for the optional generic node.
    '''

    # * test: fields
    def test_fields(self, test_ctx, session):
        '''
        Keep exactly the five published node fields.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The model is a domain object with only the published fields.
        assert issubclass(AstNode, DomainObject)
        assert set(AstNode.model_fields) == {
            'kind',
            'children',
            'value',
            'lineno',
            'lexpos',
        }
        assert 'type' not in AstNode.model_fields
        assert 'format' not in AstNode.model_fields
        assert AstNode.model_fields['kind'].annotation is str
        assert AstNode.model_fields['children'].annotation is list
        assert AstNode.model_fields['value'].annotation == Any | None
        assert AstNode.model_fields['lineno'].annotation == int | None
        assert AstNode.model_fields['lexpos'].annotation == int | None
        assert all(
            field.annotation is not Lexeme
            for field in AstNode.model_fields.values()
        )
        test_ctx.assert_new()

    # * test: defaults
    def test_defaults(self, test_ctx, session):
        '''
        Default children to an empty list and value to None.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Omitted children and value take the published defaults.
        first = AstNode(kind='leaf')
        second = AstNode(kind='leaf')

        # Each node gets its own empty child list, and value is absent.
        assert first.children == []
        assert second.children == []
        assert first.children is not second.children
        assert first.value is None
        assert second.value is None
        assert AstNode.model_fields['children'].default_factory is list
        assert AstNode.model_fields['value'].default is None

    # * test: closed
    def test_closed(self, test_ctx, session):
        '''
        Reject a type field and a nested lexeme field.

        :param test_ctx: The bound domain tester context.
        :type test_ctx: DomainTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # type is not a declared field.
        with pytest.raises(ValidationError):
            AstNode(kind='expr', type='NUMBER')

        # A nested lexeme is not a declared field.
        with pytest.raises(ValidationError):
            AstNode(
                kind='expr',
                lexeme=Lexeme(
                    type='NUMBER',
                    value='3',
                    lineno=1,
                    lexpos=0,
                ),
            )
