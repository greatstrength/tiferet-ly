"""Tests for Tiferet-Ly AST Mappers"""

# *** imports

# ** app
from tiferet_ly.mappers.ast import AstNodeAggregate

# *** tests

# ** test: ast_node_aggregate_new_and_leaf
def test_ast_node_aggregate_new_and_leaf() -> None:
    '''
    Test the language-facing new and leaf factories.
    '''

    # Construct a leaf and an internal node through the factories.
    left = AstNodeAggregate.leaf('num', 1, lineno=1, lexpos=0)
    right = AstNodeAggregate.leaf('num', 2, lineno=1, lexpos=2)
    node = AstNodeAggregate.new(
        'add',
        children=[left, right],
        lineno=1,
        lexpos=0,
    )

    # Assert factory construction and default empty children.
    assert isinstance(left, AstNodeAggregate)
    assert left.kind == 'num'
    assert left.value == 1
    assert left.children == []
    assert node.kind == 'add'
    assert node.children == [left, right]
    assert AstNodeAggregate.new('expr').children == []


# ** test: ast_node_aggregate_mutators
def test_ast_node_aggregate_mutators() -> None:
    '''
    Test add_child and set_value on AstNodeAggregate.
    '''

    # Mutate a newly constructed node.
    node = AstNodeAggregate.new('add')
    child = AstNodeAggregate.leaf('num', 3)
    node.add_child(child)
    node.set_value('kept')

    # Assert the mutators updated the fields.
    assert node.children == [child]
    assert node.value == 'kept'


# ** test: no_ast_alias_or_persistence_surface
def test_no_ast_alias_or_persistence_surface() -> None:
    '''
    Test that there is no Ast alias and no ConfigObject, repository, or Service.
    '''

    # Import the public packages this type is exported from.
    import tiferet_ly
    import tiferet_ly.domain as domain
    import tiferet_ly.mappers as mappers

    # Assert the Python name is AstNodeAggregate and Ast is not exported.
    assert 'Ast' not in dir(tiferet_ly)
    assert 'Ast' not in domain.__all__
    assert 'Ast' not in mappers.__all__
    assert 'AstNodeAggregate' in mappers.__all__
    assert not hasattr(mappers, 'AstNodeConfigObject')
    assert not hasattr(tiferet_ly, 'AstNodeConfigObject')
