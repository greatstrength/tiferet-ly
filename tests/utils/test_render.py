"""Tests for Tiferet-Ly Result Rendering Utility"""

# *** imports

# ** app
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.utils.render import ResultRenderer

# *** tests

# ** test: render_string_is_identity
def test_render_string_is_identity() -> None:
    '''
    Test that an already-string value is returned unchanged.
    '''

    # Render a string that should not be re-quoted.
    result = ResultRenderer.render('already')

    # Assert identity, not a repr.
    assert result == 'already'
    assert result != "'already'"


# ** test: render_ast_node_aggregate_uses_format
def test_render_ast_node_aggregate_uses_format() -> None:
    '''
    Test that an AstNodeAggregate renders as its format string.
    '''

    # Render a parent node with two children.
    node = AstNodeAggregate.new(
        'add',
        children=[
            AstNodeAggregate.leaf('num', 1),
            AstNodeAggregate.leaf('num', 2),
        ],
    )

    # Assert the renderer matches the aggregate query.
    assert ResultRenderer.render(node) == node.format()


# ** test: render_int_falls_back_to_str
def test_render_int_falls_back_to_str() -> None:
    '''
    Test that a non-tree value becomes str(value).
    '''

    # Render the arithmetic parse result.
    result = ResultRenderer.render(3)

    # Assert the CLI-printable string.
    assert result == '3'


# ** test: render_does_not_walk_foreign_tree
def test_render_does_not_walk_foreign_tree() -> None:
    '''
    Test that a foreign object with kind and children is not walked.
    '''

    # A takwin-shaped stand-in that is not an AstNodeAggregate.
    class Foreign:
        def __init__(self) -> None:
            self.kind = 'add'
            self.children = ['left', 'right']
            self.value = None

        def __str__(self) -> str:
            return 'Foreign()'

    foreign = Foreign()

    # Assert str(value), not a tree walk of kind/children.
    assert ResultRenderer.render(foreign) == 'Foreign()'
    assert ResultRenderer.render(foreign) != 'add'


# ** test: render_module_does_not_import_domain_or_ply
def test_render_module_does_not_import_domain_or_ply() -> None:
    '''
    Test that the renderer imports neither ply nor tiferet_ly.domain.
    '''

    # Import the module under test and inspect its globals.
    import tiferet_ly.utils.render as render

    # Assert ply and domain stay out of the util module.
    assert 'ply' not in render.__dict__
    assert not any(
        name == 'tiferet_ly.domain' or name.startswith('tiferet_ly.domain.')
        for name in render.__dict__
    )
