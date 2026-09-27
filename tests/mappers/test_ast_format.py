"""Tiferet Ly AST Format Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path

# ** app
from tiferet import use_tester
from tiferet_ly.domain import ast as ast_domain
from tiferet_ly.domain.ast import AstNode
from tiferet_ly.mappers import ast as ast_mappers
from tiferet_ly.mappers.ast import (
    DEFAULT_FORMAT_INDENT,
    DEFAULT_FORMAT_INDENT_STEP,
    AstNodeAggregate,
)

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

# ** test: constants_and_domain_has_no_format
def test_constants_and_domain_has_no_format():
    '''
    Keep indent defaults on the mapper and presentation off the model.
    '''

    # The published defaults are the empty prefix and a two-space step.
    assert DEFAULT_FORMAT_INDENT == ''
    assert DEFAULT_FORMAT_INDENT_STEP == '  '
    signature = inspect.signature(AstNodeAggregate.format)
    assert list(signature.parameters) == ['self', 'indent', 'step']
    assert signature.parameters['indent'].default == DEFAULT_FORMAT_INDENT
    assert signature.parameters['step'].default == DEFAULT_FORMAT_INDENT_STEP
    assert signature.return_annotation is str

    # The domain model has no format method.
    assert 'format' not in AstNode.__dict__
    assert not hasattr(AstNode, 'format')
    domain_tree = ast.parse(Path(ast_domain.__file__).read_text())
    domain_defined = [
        node.name
        for node in ast.walk(domain_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert 'format' not in domain_defined

    # The mapper does not import ply.
    mapper_tree = ast.parse(Path(ast_mappers.__file__).read_text())
    for module in _imported_modules(mapper_tree):
        assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_ast_node_aggregate_format
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
class TestAstNodeAggregateFormat:
    '''
    Tests for deterministic tree rendering on the aggregate.
    '''

    # * test: leaf_formats_kind_and_value
    def test_leaf_formats_kind_and_value(self, test_ctx, session):
        '''
        Format a leaf to one string containing its kind and value.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The same leaf renders the same string, without its source span.
        leaf = AstNodeAggregate.leaf('number', 3, lineno=17, lexpos=23)
        rendered = leaf.format()
        assert rendered == 'number\n3'
        assert rendered == leaf.format()
        assert '17' not in rendered
        assert '23' not in rendered

    # * test: parent_formats_children_in_order
    def test_parent_formats_children_in_order(self, test_ctx, session):
        '''
        Format two children in stored order beneath the parent.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Insertion order is kept even when kind and value would sort otherwise.
        left = AstNodeAggregate.leaf('b', 2, lineno=11, lexpos=22)
        right = AstNodeAggregate.leaf('a', 1, lineno=33, lexpos=44)
        parent = AstNodeAggregate.new(
            'add',
            [left, right],
            lineno=55,
            lexpos=66,
        )
        rendered = parent.format()
        assert parent.value is None
        assert rendered == 'add\n  b\n  2\n  a\n  1'
        assert '11' not in rendered
        assert '22' not in rendered
        assert '33' not in rendered
        assert '44' not in rendered
        assert '55' not in rendered
        assert '66' not in rendered

    # * test: none_value_omits_value_line
    def test_none_value_omits_value_line(self, test_ctx, session):
        '''
        Omit the value line when value is None.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A valueless node is only its kind. None is not printed.
        node = AstNodeAggregate.new('stmt', value=None, lineno=9, lexpos=8)
        rendered = node.format()
        assert node.value is None
        assert rendered == 'stmt'
        assert '\n' not in rendered
        assert 'None' not in rendered
        assert '9' not in rendered
        assert '8' not in rendered

        # A valueless parent has no blank line before its child.
        parent = AstNodeAggregate.new(
            'add',
            [AstNodeAggregate.leaf('number', 1)],
            value=None,
        )
        assert parent.format() == 'add\n  number\n  1'
        assert '\n\n' not in parent.format()
