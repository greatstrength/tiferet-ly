"""Tiferet Ly AST Export Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** app
from tiferet_ly import domain
from tiferet_ly.domain.ast import AstNode
from tiferet_ly.mappers.ast import AstNodeAggregate

# *** tests

# ** test: ast_node_is_exported
def test_ast_node_is_exported():
    '''
    Export the domain node under its public name and no short alias.
    '''

    # The package attribute is the domain class, not a second type.
    assert domain.AstNode is AstNode
    assert not hasattr(domain, 'Ast')

    # The aggregate stays on the mapper module.
    assert AstNodeAggregate.__module__ == 'tiferet_ly.mappers.ast'

# ** test: export_test_imports_neither_ply_nor_repository
def test_export_test_imports_neither_ply_nor_repository():
    '''
    Keep PLY and repositories out of this export test.
    '''

    # Parse this file without importing those modules.
    tree = ast.parse(Path(__file__).read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    # No PLY import and no repository import.
    assert not any(name == 'ply' or name.startswith('ply.') for name in modules)
    assert not any('repos' in name for name in modules)
