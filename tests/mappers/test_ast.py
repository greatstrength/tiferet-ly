"""Tiferet Ly AST Mapper Tests"""

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
from tiferet_ly.domain.ast import AstNode
from tiferet_ly.mappers import ast as ast_mappers
from tiferet_ly.mappers.ast import AstNodeAggregate

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

# ** test: module_does_not_define_format_or_import_ply
def test_module_does_not_define_format_or_import_ply():
    '''
    Keep the aggregate factory free of format and PLY.
    '''

    # The mapper defines the aggregate and neither format nor a config object.
    tree = ast.parse(Path(ast_mappers.__file__).read_text())
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    assert defined == ['AstNodeAggregate', 'new', 'leaf', 'add_child', 'set_value']
    assert 'format' not in defined
    assert 'format' not in AstNodeAggregate.__dict__
    assert 'format' not in AstNodeAggregate.model_fields

    # The module does not import ply.
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_ast_node_aggregate
@use_tester(
    type='aggregate',
    target_cls=AstNodeAggregate,
    sample_data={
        'kind': 'add',
        'children': [],
        'value': None,
        'lineno': 1,
        'lexpos': 0,
    },
    equality_fields=['kind', 'children', 'value', 'lineno', 'lexpos'],
)
class TestAstNodeAggregate:
    '''
    Tests for the optional node aggregate factory.
    '''

    # * test: bases_and_factories
    def test_bases_and_factories(self, test_ctx, session):
        '''
        Extend the node model and expose class factories.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases and fields match the published node, with no format field.
        assert AstNodeAggregate.__bases__ == (AstNode, Aggregate)
        assert set(AstNodeAggregate.model_fields) == {
            'kind',
            'children',
            'value',
            'lineno',
            'lexpos',
        }
        assert 'format' not in AstNodeAggregate.model_fields
        assert isinstance(AstNodeAggregate.__dict__['new'], classmethod)
        assert isinstance(AstNodeAggregate.__dict__['leaf'], classmethod)

        # new takes the published fields. Omitted children mean None here.
        new_signature = inspect.signature(AstNodeAggregate.new)
        assert list(new_signature.parameters) == [
            'kind',
            'children',
            'value',
            'lineno',
            'lexpos',
        ]
        assert new_signature.parameters['children'].default is None
        assert new_signature.parameters['value'].default is None
        assert new_signature.parameters['lineno'].default is None
        assert new_signature.parameters['lexpos'].default is None

        # leaf requires a value and does not take children.
        leaf_signature = inspect.signature(AstNodeAggregate.leaf)
        assert list(leaf_signature.parameters) == [
            'kind',
            'value',
            'lineno',
            'lexpos',
        ]
        assert leaf_signature.parameters['lineno'].default is None
        assert leaf_signature.parameters['lexpos'].default is None
        test_ctx.assert_new()

    # * test: new_returns_parent
    def test_new_returns_parent(self, test_ctx, session):
        '''
        Return a node whose kind and children are the supplied objects.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The published call keeps those two child objects.
        left = object()
        right = object()
        node = AstNodeAggregate.new('add', [left, right])
        assert type(node) is AstNodeAggregate
        assert node.kind == 'add'
        assert node.children == [left, right]
        assert node.children[0] is left
        assert node.children[1] is right

        # Omitted children are a new empty list, not a shared default.
        first = AstNodeAggregate.new('add')
        second = AstNodeAggregate.new('add')
        assert first.children == []
        assert second.children == []
        assert first.children is not second.children
        assert first.value is None
        assert second.value is None

    # * test: leaf_returns_value
    def test_leaf_returns_value(self, test_ctx, session):
        '''
        Return a leaf whose value is kept and whose children are empty.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The published call stores the number and no children.
        leaf = AstNodeAggregate.leaf('number', 3)
        assert type(leaf) is AstNodeAggregate
        assert leaf.kind == 'number'
        assert leaf.value == 3
        assert leaf.children == []

        # Each leaf owns a distinct empty child list.
        other = AstNodeAggregate.leaf('number', 3, lineno=2, lexpos=4)
        assert other.value == 3
        assert other.children == []
        assert other.children is not leaf.children
        assert other.lineno == 2
        assert other.lexpos == 4

    # * test: add_child_and_set_value
    def test_add_child_and_set_value(self, test_ctx, session):
        '''
        Mutate children and value and return None.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Appending keeps the existing child and returns None.
        left = object()
        right = object()
        node = AstNodeAggregate.new('add', [left])
        assert node.add_child(right) is None
        assert node.children[0] is left
        assert node.children[1] is right

        # Assigning the value returns None and stores it.
        assert node.set_value(3) is None
        assert node.value == 3

    # * test: subclass_factory
    def test_subclass_factory(self, test_ctx, session):
        '''
        Construct the receiving class from new and leaf.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A subclass factory does not fall back to the base aggregate.
        class SubAst(AstNodeAggregate):
            '''Receiver used only to prove factory dispatch.'''

        parent = SubAst.new('add', [object()])
        leaf = SubAst.leaf('number', 3)
        assert type(parent) is SubAst
        assert type(leaf) is SubAst
        assert isinstance(parent, AstNodeAggregate)
        assert isinstance(leaf, AstNodeAggregate)
