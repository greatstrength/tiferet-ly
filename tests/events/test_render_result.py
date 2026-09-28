"""Tiferet Ly Render Result Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path
from unittest.mock import patch

# ** app
import tiferet_ly.events as events_package
from tiferet import DomainEvent
from tiferet_ly.events import render as render_events
from tiferet_ly.events.render import RenderResult
from tiferet_ly.mappers.ast import AstNodeAggregate
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

# ** function: called_names
def _called_names(tree: ast.AST) -> list[str]:
    '''
    Collect called function and method names.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Called names.
    :rtype: list[str]
    '''

    # Attribute calls contribute the attribute. Bare calls contribute the name.
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
        elif isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return names

# *** tests

# ** test: module_does_not_import_ply
def test_module_does_not_import_ply():
    '''
    Keep PLY, persistence, and the package export off this event.
    '''

    # The published signature defaults the flag to false.
    signature = inspect.signature(RenderResult.execute)
    assert list(signature.parameters) == [
        'self',
        'result',
        'render_result',
        'kwargs',
    ]
    assert signature.parameters['result'].default is inspect.Parameter.empty
    assert signature.parameters['render_result'].default is False
    assert RenderResult.__module__ == 'tiferet_ly.events.render'
    assert not hasattr(RenderResult, 'save')
    assert not hasattr(RenderResult, 'delete')

    # Scan the source. Do not rely on a successful import.
    tree = ast.parse(Path(render_events.__file__).read_text())
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')
    assert 'save' not in _called_names(tree)
    assert 'delete' not in _called_names(tree)
    assert 'ReturnResult' not in Path(render_events.__file__).read_text()

    # The events package does not export this event.
    assert not hasattr(events_package, 'RenderResult')
    assert not hasattr(events_package, 'ReturnResult')
    package_tree = ast.parse(Path(events_package.__file__).read_text())
    package_names = [
        alias.name
        for node in ast.walk(package_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    assert 'RenderResult' not in package_names
    assert 'ReturnResult' not in package_names
    for module in _imported_modules(package_tree):
        assert not module.endswith('render')
        assert '.render' not in module

# ** test: true_renders_result
def test_true_renders_result():
    '''
    Render when the flag is true.
    '''

    # The published call returns the rendered string, not the integer.
    rendered = DomainEvent.handle(
        RenderResult,
        result=3,
        render_result=True,
    )
    assert rendered == '3'
    assert type(rendered) is str

    # The true path is the renderer, not a special case for 3.
    node = AstNodeAggregate.leaf('number', 3, lineno=17, lexpos=23)
    with patch.object(ResultRenderer, 'render', wraps=ResultRenderer.render) as render:
        assert DomainEvent.handle(
            RenderResult,
            result=node,
            render_result=True,
        ) == node.format()
    render.assert_called_once_with(node)

# ** test: false_and_omitted_return_original
def test_false_and_omitted_return_original():
    '''
    Return the same result object when the flag is false or omitted.
    '''

    # False does not render, copy, or replace the object.
    original = object()
    with patch.object(ResultRenderer, 'render') as render:
        assert DomainEvent.handle(
            RenderResult,
            result=original,
            render_result=False,
        ) is original
        assert DomainEvent.handle(
            RenderResult,
            result=original,
        ) is original
    render.assert_not_called()

    # The integer from the published call stays an integer on both paths.
    result = 3
    assert DomainEvent.handle(
        RenderResult,
        result=result,
        render_result=False,
    ) is result
    assert DomainEvent.handle(
        RenderResult,
        result=result,
    ) is result
