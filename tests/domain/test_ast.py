"""Tests for Tiferet-Ly AST Domain Model"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.ast import AstNode

# *** tests

# ** test: ast_node_construct
def test_ast_node_construct() -> None:
    '''
    Test constructing an AstNode with kind, children, value, and span.
    '''

    # Construct a leaf and an internal node that holds it.
    leaf = AstNode(kind='num', value=1, lineno=1, lexpos=0)
    node = AstNode(
        kind='add',
        children=[leaf],
        lineno=1,
        lexpos=0,
    )

    # Assert the declared fields and the absence of retired ones.
    assert node.kind == 'add'
    assert node.children == [leaf]
    assert node.value is None
    assert node.lineno == 1
    assert node.lexpos == 0
    assert set(AstNode.model_fields) == {
        'kind',
        'children',
        'value',
        'lineno',
        'lexpos',
    }
    assert 'type' not in AstNode.model_fields
    assert 'col' not in AstNode.model_fields
    assert 'lexeme' not in AstNode.model_fields


# ** test: ast_node_defaults
def test_ast_node_defaults() -> None:
    '''
    Test that optional AstNode fields default to an empty child list and None.
    '''

    # Construct with only the required kind.
    node = AstNode(kind='expr')

    # Assert the optional defaults.
    assert node.children == []
    assert node.value is None
    assert node.lineno is None
    assert node.lexpos is None


# ** test: ast_node_requires_kind
def test_ast_node_requires_kind() -> None:
    '''
    Test that constructing an AstNode without kind raises ValidationError.
    '''

    # Missing kind raises ValidationError.
    with pytest.raises(ValidationError):
        AstNode()


# ** test: ast_node_forbids_extra_fields
def test_ast_node_forbids_extra_fields() -> None:
    '''
    Test that an unknown field raises ValidationError.
    '''

    # An unrecognized field is rejected.
    with pytest.raises(ValidationError):
        AstNode(kind='num', col=2)
