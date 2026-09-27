"""Tiferet Ly Parse Rendering Tests"""

# *** imports

# ** core
import argparse
import inspect
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

# ** app
import tiferet_ly.assets as assets
from tiferet.contexts.feature import FeatureContext
from tiferet.contexts.request import RequestContext
from tiferet.repos.cli import CliConfigRepository
from tiferet.repos.di import DIConfigRepository
from tiferet.repos.feature import FeatureConfigRepository
from tiferet_ly.events.render import RenderResult
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ComplexProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate
from tiferet_ly.utils.parse import PlyParser

# *** constants

# ** constant: assets_dir
_ASSETS = Path(assets.__file__).parent

# ** constant: feature_config
_FEATURE_YML = _ASSETS / 'feature.yml'

# ** constant: di_config
_DI_YML = _ASSETS / 'di.yml'

# ** constant: cli_config
_CLI_YML = _ASSETS / 'cli.yml'

# ** constant: collect_steps
_COLLECT = (
    ('list_tokens_event', 'tokens'),
    ('list_productions_event', 'productions'),
    ('list_grammars_event', 'grammars'),
)

# ** constant: reader_params
_READER_PARAMS = {
    'grammar_id': '$r.grammar_id',
    'text': '$r.text',
    'tokens': '$r.tokens',
    'productions': '$r.productions',
    'grammars': '$r.grammars',
}

# ** constant: render_params
_RENDER_PARAMS = {
    'result': '$r.result',
    'render_result': '$r.render_result',
}

# *** functions

# ** function: registered
def _registered(service_id: str) -> type:
    '''
    Import the class registered for a service id.

    :param service_id: The DI registration identifier.
    :type service_id: str
    :return: The registered class.
    :rtype: type
    '''

    # The package registration is the source of the class, not a local import.
    registration = DIConfigRepository(str(_DI_YML)).get_registration(service_id)
    assert registration is not None
    return registration.get_service_type()

# ** function: feature
def _feature(feature_id: str):
    '''
    Load one feature from the package feature configuration.

    :param feature_id: The feature identifier.
    :type feature_id: str
    :return: The loaded feature aggregate.
    :rtype: object
    '''

    # Load through the framework repository so the YAML schema is the contract.
    feature = FeatureConfigRepository(str(_FEATURE_YML)).get(feature_id)
    assert feature is not None
    return feature

# ** function: int_catalogues
def _int_catalogues():
    '''
    Build a catalogue whose start action returns the integer ``3`` for ``1+2``.

    :return: Tokens, productions, and grammars.
    :rtype: tuple
    '''

    # One grammar. The start action's p[0] is the sum.
    grammars = [
        GrammarAggregate(id='expr', parent_ids=[], start='expr'),
    ]
    tokens = [
        SimpleTokenRuleAggregate(
            name='NUMBER',
            grammar_id='expr',
            pattern=r'[0-9]+',
        ),
        SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='expr',
            pattern=r'\+',
        ),
    ]
    productions = [
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action='p[0] = int(p[1])',
        ),
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : expr PLUS NUMBER',
            action='p[0] = p[1] + int(p[3])',
        ),
    ]
    return tokens, productions, grammars

# ** function: node_catalogues
def _node_catalogues():
    '''
    Build a catalogue whose start action returns an aggregate leaf.

    :return: Tokens, productions, and grammars.
    :rtype: tuple
    '''

    # ``$ast`` is the translator default. The feature does not pass rewrites.
    grammars = [
        GrammarAggregate(id='expr', parent_ids=[], start='expr'),
    ]
    tokens = [
        SimpleTokenRuleAggregate(
            name='NUMBER',
            grammar_id='expr',
            pattern=r'[0-9]+',
        ),
    ]
    productions = [
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='expr',
            spec='expr : NUMBER',
            action="p[0] = $ast.leaf('number', int(p[1]))",
        ),
    ]
    return tokens, productions, grammars

# ** function: run_parse
def _run_parse(
        data: dict,
        tokens: list,
        productions: list,
        grammars: list,
        parser,
    ):
    '''
    Run ``parse.default`` with catalogue services and the registered parser.

    :param data: The request data.
    :type data: dict
    :param tokens: The token catalogue returned by list.
    :type tokens: list
    :param productions: The production catalogue returned by list.
    :type productions: list
    :param grammars: The grammar catalogue returned by list.
    :type grammars: list
    :param parser: The parser service instance.
    :type parser: ParserService
    :return: The feature result.
    :rtype: object
    '''

    # Catalogue services answer list and nothing else.
    token_service = Mock()
    token_service.list.return_value = tokens
    production_service = Mock()
    production_service.list.return_value = productions
    grammar_service = Mock()
    grammar_service.list.return_value = grammars

    # The render step has no constructor dependency.
    wired = {
        'list_tokens_event': _registered('list_tokens_event')(token_service),
        'list_productions_event': _registered('list_productions_event')(production_service),
        'list_grammars_event': _registered('list_grammars_event')(grammar_service),
        'parse_text_event': _registered('parse_text_event')(parser),
        'render_result_event': _registered('render_result_event')(),
    }

    def get_dependency(service_id, *flags):
        # Flags do not select another event. The registration is the binding.
        return wired[service_id]

    # The last step's return is the feature result.
    context = FeatureContext.from_domain(
        _feature('parse.default'),
        get_dependency=get_dependency,
    )
    request = RequestContext(data=dict(data))
    context.execute_feature(request)
    return request.result

# ** function: record_parse
def _record_parse(parser) -> dict:
    '''
    Wrap ``parse`` so the test can see the value it produced.

    :param parser: The parser service instance.
    :type parser: ParserService
    :return: The recorded call and return value.
    :rtype: dict
    '''

    # Keep the real parser. The feature must return that call's value when off.
    original = parser.parse
    recorded = {}

    def wrapper(*args, **kwargs):
        recorded['value'] = original(*args, **kwargs)
        return recorded['value']

    parser.parse = wrapper
    return recorded

# *** tests

# ** test: parse_default_has_one_terminal_render_step
def test_parse_default_has_one_terminal_render_step():
    '''
    End parse at one unconditional render step, and do not add ReturnResult.
    '''

    # The reader stores p[0]. The next step is the only render step.
    feature = _feature('parse.default')
    assert [(step.service_id, step.data_key) for step in feature.steps] == [
        *_COLLECT,
        ('parse_text_event', 'result'),
        ('render_result_event', None),
    ]
    assert feature.steps[-2].parameters == _READER_PARAMS
    assert feature.steps[-1].parameters == _RENDER_PARAMS
    assert feature.steps[-1].condition is None
    assert all(step.condition is None for step in feature.steps)
    assert sum(step.service_id == 'render_result_event' for step in feature.steps) == 1
    assert _registered('render_result_event') is RenderResult

    # The flag is an optional schema parameter, not a request key or a condition.
    schema = feature.params_schema
    assert schema is not None
    assert [param.name for param in schema.parameters] == ['render_result']
    param = schema.parameters[0]
    assert param.type == 'bool'
    assert param.required is False
    assert param.default is False
    assert schema.coerce({})['render_result'] is False
    assert schema.coerce({'render_result': False})['render_result'] is False
    assert schema.coerce({'render_result': True})['render_result'] is True

    # Configuration does not name ReturnResult or import PLY.
    feature_text = _FEATURE_YML.read_text()
    di_text = _DI_YML.read_text()
    assert 'ReturnResult' not in feature_text
    assert 'ReturnResult' not in di_text
    assert 'condition:' not in feature_text
    assert 'request:' not in feature_text
    assert 'import ply' not in feature_text
    assert 'ply.' not in feature_text
    assert di_text.count('class_name: RenderResult') == 1

# ** test: omitted_or_false_returns_raw_value
def test_omitted_or_false_returns_raw_value():
    '''
    Return the raw p[0] when the flag is omitted or false.
    '''

    tokens, productions, grammars = _int_catalogues()

    def once(data):
        # A fresh parser so each path is compared to its own p[0].
        parser = _registered('parser_service')()
        recorded = _record_parse(parser)
        result = _run_parse(
            data,
            tokens,
            productions,
            grammars,
            parser,
        )
        return result, recorded['value']

    # Omitted uses the schema default. False is explicit. Neither renders.
    with patch('tiferet_ly.events.render.ResultRenderer.render') as render:
        omitted, omitted_raw = once({
            'grammar_id': 'expr',
            'text': '1+2',
        })
        explicit, explicit_raw = once({
            'grammar_id': 'expr',
            'text': '1+2',
            'render_result': False,
        })
    render.assert_not_called()

    # Each path returns that call's object, not a copy or a string.
    assert omitted is omitted_raw
    assert explicit is explicit_raw
    assert omitted == 3
    assert explicit == 3
    assert type(omitted) is int
    assert type(explicit) is int

# ** test: true_returns_string_and_formats_aggregate
def test_true_returns_string_and_formats_aggregate():
    '''
    Return a string when the flag is true, formatting an aggregate.
    '''

    # A non-aggregate uses its ordinary string form, not format().
    tokens, productions, grammars = _int_catalogues()
    parser = _registered('parser_service')()
    with patch.object(AstNodeAggregate, 'format') as format_node:
        rendered = _run_parse(
            {
                'grammar_id': 'expr',
                'text': '1+2',
                'render_result': True,
            },
            tokens,
            productions,
            grammars,
            parser,
        )
    format_node.assert_not_called()
    assert rendered == '3'
    assert type(rendered) is str

    # An aggregate p[0] is rendered with format(), not str(node).
    tokens, productions, grammars = _node_catalogues()
    parser = _registered('parser_service')()
    recorded = _record_parse(parser)
    raw = _run_parse(
        {
            'grammar_id': 'expr',
            'text': '7',
        },
        tokens,
        productions,
        grammars,
        parser,
    )
    assert raw is recorded['value']
    assert isinstance(raw, AstNodeAggregate)
    expected = raw.format()

    # Spy on the instance method. An unbound wrap would drop self.
    calls = []
    original = AstNodeAggregate.format

    def spy(self, *args, **kwargs):
        calls.append(self)
        return original(self, *args, **kwargs)

    with patch.object(AstNodeAggregate, 'format', spy):
        rendered = _run_parse(
            {
                'grammar_id': 'expr',
                'text': '7',
                'render_result': True,
            },
            tokens,
            productions,
            grammars,
            parser,
        )
    assert rendered == expected
    assert type(rendered) is str
    assert rendered != str(raw)
    assert calls

# ** test: parser_service_parse_remains_any
def test_parser_service_parse_remains_any():
    '''
    Keep the parser contract untyped.
    '''

    # Rendering is a feature step. It does not narrow the service contract.
    assert inspect.signature(ParserService.parse).return_annotation is Any
    assert inspect.signature(PlyParser.parse).return_annotation is Any

# ** test: lex_default_is_unchanged
def test_lex_default_is_unchanged():
    '''
    Leave the lex feature without a render step or schema.
    '''

    # The reader is still terminal, and the flag is not declared here.
    lex = _feature('lex.default')
    assert lex.params_schema is None
    assert [(step.service_id, step.data_key) for step in lex.steps] == [
        *_COLLECT,
        ('lex_text_event', None),
    ]
    assert lex.steps[-1].parameters == _READER_PARAMS
    assert all(step.condition is None for step in lex.steps)
    assert not any(step.service_id == 'render_result_event' for step in lex.steps)

# ** test: cli_render_result_is_store_true
def test_cli_render_result_is_store_true():
    '''
    Expose ``--render-result`` as a store_true flag with dest ``render_result``.
    '''

    # The command id is the feature id. The flag is the only argument.
    command = CliConfigRepository(str(_CLI_YML)).get('parse.default')
    assert command is not None
    assert command.id == 'parse.default'
    assert len(command.arguments) == 1
    argument = command.arguments[0]
    assert argument.name_or_flags == ['--render-result']
    assert argument.type == 'bool'
    assert argument.get_dest() == 'render_result'
    assert argument.to_argparse_kwargs()['action'] == 'store_true'

    # Absent is false. Present is true. No value is consumed.
    parser = argparse.ArgumentParser()
    parser.add_argument(*argument.name_or_flags, **argument.to_argparse_kwargs())
    assert parser.parse_args([]).render_result is False
    assert parser.parse_args(['--render-result']).render_result is True
    assert 'import ply' not in _CLI_YML.read_text()
