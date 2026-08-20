"""Tests for Tiferet-Ly Render Domain Events"""

# *** imports

# ** core
from pathlib import Path
from typing import Any, get_type_hints

# ** infra
import yaml

# ** app
from tiferet.events.core import DomainEvent
from tiferet.mappers.cli import CliCommandConfigObject
from tiferet_ly.events.render import RenderResult
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.ast import AstNodeAggregate

# *** tests

# ** test: render_result_returns_string
def test_render_result_returns_string() -> None:
    '''
    Test that RenderResult returns a str via DomainEvent.handle.
    '''

    # Handle RenderResult with the flag on against an int and a tree.
    node = AstNodeAggregate.leaf('num', 1)
    as_int = DomainEvent.handle(RenderResult, result=3, render_result=True)
    as_node = DomainEvent.handle(RenderResult, result=node, render_result=True)

    # Assert both arms return strings.
    assert as_int == '3'
    assert isinstance(as_int, str)
    assert as_node == node.format()
    assert isinstance(as_node, str)


# ** test: render_result_is_passthrough_when_flag_off
def test_render_result_is_passthrough_when_flag_off() -> None:
    '''
    Test that RenderResult returns its result unchanged when the flag is off.
    '''

    # Handle RenderResult with the flag off or omitted.
    node = AstNodeAggregate.leaf('num', 1)
    omitted = DomainEvent.handle(RenderResult, result=3)
    flagged_off = DomainEvent.handle(RenderResult, result=node, render_result=False)

    # Assert the values are the original objects.
    assert omitted == 3
    assert type(omitted) is int
    assert flagged_off is node


# ** test: render_events_do_not_import_ply_or_write
def test_render_events_do_not_import_ply_or_write() -> None:
    '''
    Test that render events import neither ply nor write methods.
    '''

    # Import the event module and inspect its surface.
    import tiferet_ly.events.render as render_events

    # Assert ply is absent and the events have no save or delete.
    assert 'ply' not in render_events.__dict__
    assert not hasattr(RenderResult, 'save')
    assert not hasattr(RenderResult, 'delete')
    assert not hasattr(render_events, 'ReturnResult')


# ** test: parse_feature_wires_render_result_step
def test_parse_feature_wires_render_result_step() -> None:
    '''
    Test that parse.default stores parse_text under result and ends on RenderResult.
    '''

    # Load the landed Feature YAML.
    assets = Path(__file__).resolve().parents[2] / 'tiferet_ly' / 'assets'
    data = yaml.safe_load((assets / 'feature.yml').read_text(encoding='utf-8'))
    parse = data['features']['parse']['default']
    lex = data['features']['lex']['default']
    steps = parse['steps']

    # Assert the request schema and the flagged terminal step.
    assert parse['params_schema']['grammar_id'] == 'str'
    assert parse['params_schema']['text'] == 'str'
    assert parse['params_schema']['render_result'] == {
        'type': 'bool',
        'required': False,
        'default': False,
    }
    assert steps[-2]['service_id'] == 'parse_text'
    assert steps[-2]['data_key'] == 'result'
    assert steps[-1]['service_id'] == 'render_result'
    assert 'condition' not in steps[-1]
    assert 'data_key' not in steps[-1]
    assert steps[-1]['parameters'] == {
        'result': '$r.result',
        'render_result': '$r.render_result',
    }
    assert 'return_result' not in {
        step.get('service_id')
        for step in steps
    }

    # Assert lex is unchanged and parse still returns Any.
    assert lex['steps'][-1]['service_id'] == 'lex_text'
    assert 'data_key' not in lex['steps'][-1]
    assert 'render_result' not in lex
    assert get_type_hints(ParserService.parse)['return'] is Any


# ** test: parse_cli_render_result_dests_to_flag
def test_parse_cli_render_result_dests_to_flag() -> None:
    '''
    Test that --render-result is a store_true flag dested to render_result.
    '''

    # Load the minimum CLI command.
    assets = Path(__file__).resolve().parents[2] / 'tiferet_ly' / 'assets'
    data = yaml.safe_load((assets / 'cli.yml').read_text(encoding='utf-8'))
    command = CliCommandConfigObject.model_validate({
        **data['cli']['cmds']['parse']['default'],
        'id': 'parse.default',
    }).map()
    flag = next(
        argument
        for argument in command.arguments
        if '--render-result' in argument.name_or_flags
    )

    # Assert dest and argparse action.
    assert flag.type == 'bool'
    assert flag.get_dest() == 'render_result'
    assert flag.to_argparse_kwargs()['action'] == 'store_true'
