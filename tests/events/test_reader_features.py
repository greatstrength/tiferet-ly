"""Tiferet Ly Reader Feature Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from unittest.mock import Mock, patch

# ** infra
import pytest

# ** app
import tiferet_ly.assets as assets
import tiferet_ly.events as events_package
from tiferet import DomainEvent, TiferetError
from tiferet.contexts.feature import FeatureContext
from tiferet.contexts.request import RequestContext
from tiferet.interfaces.core import ServiceError
from tiferet.repos.di import DIConfigRepository
from tiferet.repos.feature import FeatureConfigRepository
from tiferet_ly.assets.grammar import GRAMMAR_NOT_FOUND_ID
from tiferet_ly.events.grammar import ListGrammars
from tiferet_ly.events.reader import LexText, ParseText
from tiferet_ly.interfaces.lexer import LexerService
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import ComplexProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate
from tiferet_ly.utils.lex import PlyLexer
from tiferet_ly.utils.parse import PlyParser

# *** constants

# ** constant: assets_dir
_ASSETS = Path(assets.__file__).parent

# ** constant: feature_config
_FEATURE_YML = _ASSETS / 'feature.yml'

# ** constant: di_config
_DI_YML = _ASSETS / 'di.yml'

# ** constant: events_dir
_EVENTS = Path(events_package.__file__).parent

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

# ** function: catalogues
def _catalogues():
    '''
    Build an unsorted catalogue that can lex and parse ``1+2``.

    :return: Tokens, productions, and grammars in service order.
    :rtype: tuple
    '''

    # The later id is first so a sort would be visible to the reader call.
    grammars = [
        GrammarAggregate(id='z-later', parent_ids=[], start='expr'),
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

# ** function: run_feature
def _run_feature(
        feature_id: str,
        data: dict,
        tokens: list,
        productions: list,
        grammars: list,
        lexer,
        parser,
    ):
    '''
    Run a reader feature with catalogue services and the registered readers.

    :param feature_id: The feature identifier.
    :type feature_id: str
    :param data: The request data.
    :type data: dict
    :param tokens: The token catalogue returned by list.
    :type tokens: list
    :param productions: The production catalogue returned by list.
    :type productions: list
    :param grammars: The grammar catalogue returned by list.
    :type grammars: list
    :param lexer: The lexer service instance.
    :type lexer: LexerService
    :param parser: The parser service instance.
    :type parser: ParserService
    :return: The feature result.
    :rtype: object
    '''

    # Catalogue services answer list in the supplied order and nothing else.
    token_service = Mock()
    token_service.list.return_value = tokens
    production_service = Mock()
    production_service.list.return_value = productions
    grammar_service = Mock()
    grammar_service.list.return_value = grammars

    # Events come from the DI registration, wired to those services.
    wired = {
        'list_tokens_event': _registered('list_tokens_event')(token_service),
        'list_productions_event': _registered('list_productions_event')(production_service),
        'list_grammars_event': _registered('list_grammars_event')(grammar_service),
        'lex_text_event': _registered('lex_text_event')(lexer),
        'parse_text_event': _registered('parse_text_event')(parser),
        'render_result_event': _registered('render_result_event')(),
    }

    def get_dependency(service_id, *flags):
        # Flags do not select another reader. The registration is the binding.
        return wired[service_id]

    # Execute the loaded feature. The last step's return is the feature result.
    feature = _feature(feature_id)
    context = FeatureContext.from_domain(
        feature,
        get_dependency=get_dependency,
    )
    request = RequestContext(data=dict(data))
    context.execute_feature(request)
    return request.result

# ** function: record
def _record(service, method_name: str) -> dict:
    '''
    Wrap a reader method so the test can see the value it produced.

    :param service: The reader service instance.
    :type service: object
    :param method_name: The method to wrap.
    :type method_name: str
    :return: The recorded call and return value.
    :rtype: dict
    '''

    # Keep the real reader. The feature must return that call's value.
    original = getattr(service, method_name)
    recorded = {}

    def wrapper(*args, **kwargs):
        recorded['value'] = original(*args, **kwargs)
        recorded['args'] = args
        recorded['kwargs'] = kwargs
        return recorded['value']

    setattr(service, method_name, wrapper)
    return recorded

# *** tests

# ** test: list_grammars_returns_service_list_and_is_not_exported
def test_list_grammars_returns_service_list_and_is_not_exported():
    '''
    Return the grammar service list in that order, and do not export it.
    '''

    # Service order is not alphabetical. A sort would put ``a`` first.
    first = GrammarAggregate(id='z', parent_ids=[], start='start')
    second = GrammarAggregate(id='a', parent_ids=['z'], start='start')
    service = Mock()
    service.list.return_value = [first, second]

    result = DomainEvent.handle(
        ListGrammars,
        dependencies={'grammar_service': service},
        grammar_id='ignored',
    )

    # The event returns the service list. It does not copy or sort it.
    assert result == [first, second]
    assert [grammar.id for grammar in result] == ['z', 'a']
    service.list.assert_called_once_with()
    assert _registered('list_grammars_event') is ListGrammars

    # New events stay on their modules. The package does not re-export them.
    assert not hasattr(events_package, 'ListGrammars')
    assert not hasattr(events_package, 'LexText')
    assert not hasattr(events_package, 'ParseText')
    package_tree = ast.parse(Path(events_package.__file__).read_text())
    imported_names = [
        alias.name
        for node in ast.walk(package_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    assert 'ListGrammars' not in imported_names
    assert 'LexText' not in imported_names
    assert 'ParseText' not in imported_names

# ** test: features_collect_then_call_the_reader
def test_features_collect_then_call_the_reader():
    '''
    Collect through the three list events, then call the reader event.
    '''

    # Both features collect, then call the reader. Parse stores that value.
    for feature_id, reader_id, reader_data_key in (
        ('lex.default', 'lex_text_event', None),
        ('parse.default', 'parse_text_event', 'result'),
    ):
        feature = _feature(feature_id)
        assert feature.id == feature_id
        reader = next(step for step in feature.steps if step.service_id == reader_id)
        assert reader.data_key == reader_data_key
        assert reader.parameters == _READER_PARAMS
        assert 'rewrites' not in reader.parameters
        assert not any('grammar' in step.service_id and 'list_' not in step.service_id for step in feature.steps)
        assert not any(step.service_id == 'get_grammar_event' for step in feature.steps)

    # Lex still ends at the reader. Parse rendering is a later step.
    lex = _feature('lex.default')
    assert [(step.service_id, step.data_key) for step in lex.steps] == [
        *_COLLECT,
        ('lex_text_event', None),
    ]

    # DI names the concrete readers. Events stay behind those service ids.
    assert _registered('lexer_service') is PlyLexer
    assert _registered('parser_service') is PlyParser
    assert issubclass(PlyLexer, LexerService)
    assert issubclass(PlyParser, ParserService)
    assert _registered('lex_text_event') is LexText
    assert _registered('parse_text_event') is ParseText

# ** test: lex_default_returns_lexer_service_tokens
def test_lex_default_returns_lexer_service_tokens():
    '''
    Return the lexeme list produced by LexerService.tokenize.
    '''

    tokens, productions, grammars = _catalogues()
    rewrites = {'ignored': True}
    lexer = _registered('lexer_service')()
    parser = _registered('parser_service')()
    recorded = _record(lexer, 'tokenize')

    result = _run_feature(
        'lex.default',
        {
            'grammar_id': 'expr',
            'text': '1+2',
            'rewrites': rewrites,
        },
        tokens,
        productions,
        grammars,
        lexer,
        parser,
    )

    # The feature returns that call's list, not a copy or a parse value.
    assert result is recorded['value']
    assert all(isinstance(lexeme, LexemeAggregate) for lexeme in result)
    assert [(lexeme.type, lexeme.value) for lexeme in result] == [
        ('NUMBER', '1'),
        ('PLUS', '+'),
        ('NUMBER', '2'),
    ]
    assert recorded['args'] == ('expr', '1+2', tokens, productions, grammars)
    assert recorded['kwargs']['rewrites'] is rewrites

# ** test: parse_default_returns_parser_service_value
def test_parse_default_returns_parser_service_value():
    '''
    Return the Any value produced by ParserService.parse.
    '''

    tokens, productions, grammars = _catalogues()
    lexer = _registered('lexer_service')()
    parser = _registered('parser_service')()
    recorded = _record(parser, 'parse')

    result = _run_feature(
        'parse.default',
        {
            'grammar_id': 'expr',
            'text': '1+2',
        },
        tokens,
        productions,
        grammars,
        lexer,
        parser,
    )

    # The feature returns that call's value. It is not forced into a lexeme list.
    assert result is recorded['value']
    assert result == 3
    assert not isinstance(result, list)
    assert recorded['args'] == ('expr', '1+2', tokens, productions, grammars)
    assert recorded['kwargs']['rewrites'] is None

# ** test: unknown_grammar_raises_before_ply
def test_unknown_grammar_raises_before_ply():
    '''
    Raise GRAMMAR_NOT_FOUND_ID for an unknown grammar before PLY is called.
    '''

    tokens, productions, grammars = _catalogues()
    lexer = _registered('lexer_service')()
    parser = _registered('parser_service')()
    lexer_calls = []
    parser_calls = []
    lexer.tokenize = lambda *args, **kwargs: lexer_calls.append(args)
    parser.parse = lambda *args, **kwargs: parser_calls.append(args)

    # Patch both the names the readers call and the PLY modules themselves.
    with patch('tiferet_ly.utils.core.lex.lex') as lex_lex, \
            patch('tiferet_ly.utils.parse.yacc.yacc') as yacc_yacc, \
            patch('ply.lex.lex') as ply_lex, \
            patch('ply.yacc.yacc') as ply_yacc:
        for feature_id in ('lex.default', 'parse.default'):
            with pytest.raises((TiferetError, ServiceError)) as caught:
                _run_feature(
                    feature_id,
                    {
                        'grammar_id': 'missing',
                        'text': '1',
                    },
                    tokens,
                    productions,
                    grammars,
                    lexer,
                    parser,
                )
            assert caught.value.error_code == GRAMMAR_NOT_FOUND_ID
            assert caught.value.kwargs['grammar_id'] == 'missing'

        # The reader methods are not entered, so neither PLY builder runs.
        assert lexer_calls == []
        assert parser_calls == []
        lex_lex.assert_not_called()
        yacc_yacc.assert_not_called()
        ply_lex.assert_not_called()
        ply_yacc.assert_not_called()

# ** test: feature_and_event_modules_do_not_import_ply
def test_feature_and_event_modules_do_not_import_ply():
    '''
    Keep PLY out of the feature configuration and the event modules.
    '''

    # Scan every event module. A reader utility import would pull PLY in.
    for path in sorted(_EVENTS.glob('*.py')):
        modules = _imported_modules(ast.parse(path.read_text()))
        for module in modules:
            assert module != 'ply' and not module.startswith('ply.')
            assert module not in (
                'tiferet_ly.utils.lex',
                'tiferet_ly.utils.parse',
                'tiferet_ly.utils.core',
            )

    # The feature file is configuration. It does not import PLY.
    feature_text = _FEATURE_YML.read_text()
    assert 'import ply' not in feature_text
    assert 'ply.' not in feature_text
