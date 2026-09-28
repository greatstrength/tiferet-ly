"""Tiferet Ly Result Renderer Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path

# ** app
from tiferet import use_tester
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.utils import render as render_utils
from tiferet_ly.utils.render import ResultRenderer

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

# *** classes

# ** class: foreign_node
class _ForeignNode:
    '''
    A non-aggregate that merely has kind and children.
    '''

    # * init
    def __init__(self) -> None:
        '''
        Build a node whose walk would be visible in its string.
        '''

        # A walked child must not appear in the rendered string.
        self.kind = 'add'
        self.children = [_ForeignChild()]

    # * method: format
    def format(self) -> str:
        '''
        Return the tree a mistaken walk would produce.

        :return: A tree string.
        :rtype: str
        '''

        # This is not an aggregate format.
        return 'add\n  walked-child'

    # * method: __str__
    def __str__(self) -> str:
        '''
        Return the ordinary string form.

        :return: The non-tree string.
        :rtype: str
        '''

        # Kind and children are not part of this string.
        return 'foreign-node'

# ** class: foreign_child
class _ForeignChild:
    '''
    A child that would appear only if the parent were walked.
    '''

    # * method: __str__
    def __str__(self) -> str:
        '''
        Return the marker a walk would include.

        :return: The walked marker.
        :rtype: str
        '''

        # The renderer must not reach this string.
        return 'walked-child'

# *** tests

# ** test: module_does_not_import_ply_or_domain
def test_module_does_not_import_ply_or_domain():
    '''
    Keep PLY and the domain package out of the renderer.
    '''

    # The published call is ResultRenderer.render(value) -> str.
    signature = inspect.signature(ResultRenderer.render)
    assert list(signature.parameters) == ['value']
    assert signature.return_annotation is str
    assert isinstance(
        inspect.getattr_static(ResultRenderer, 'render'),
        staticmethod,
    )

    # Scan the source. Do not rely on a successful import.
    tree = ast.parse(Path(render_utils.__file__).read_text())
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')
        assert (
            module != 'tiferet_ly.domain'
            and not module.startswith('tiferet_ly.domain.')
        )

    # A relative domain import is also out of scope.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level:
            module = node.module or ''
            assert module != 'domain' and not module.startswith('domain.')

# *** testers

# ** tester: test_result_renderer
@use_tester(
    type='generic',
    target_cls=ResultRenderer,
)
class TestResultRenderer:
    '''
    Tests for turning a value into a string without walking foreign trees.
    '''

    # * test: string_passes_through
    def test_string_passes_through(self, test_ctx, session):
        '''
        Return a string unchanged.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The same object is returned. It is not quoted or copied.
        value = 'already'
        rendered = ResultRenderer.render(value)
        assert rendered == 'already'
        assert rendered is value

    # * test: aggregate_uses_format
    def test_aggregate_uses_format(self, test_ctx, session):
        '''
        Format an aggregate through its own format method.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The renderer delegates. It does not rebuild the tree string.
        node = AstNodeAggregate.leaf('number', 3, lineno=17, lexpos=23)
        assert node.format() != str(node)
        assert ResultRenderer.render(node) == node.format()

    # * test: other_value_uses_str
    def test_other_value_uses_str(self, test_ctx, session):
        '''
        Use str for a value that is neither a string nor an aggregate.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An integer is not walked and is not returned as itself.
        rendered = ResultRenderer.render(3)
        assert rendered == '3'
        assert type(rendered) is str

    # * test: foreign_kind_and_children_are_not_walked
    def test_foreign_kind_and_children_are_not_walked(self, test_ctx, session):
        '''
        Use str for a non-aggregate that has kind and children.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Kind, children, and format are present. None of them is used.
        value = _ForeignNode()
        rendered = ResultRenderer.render(value)
        assert rendered == 'foreign-node'
        assert rendered == str(value)
        assert rendered != value.format()
        assert 'walked-child' not in rendered
        assert 'add' not in rendered
