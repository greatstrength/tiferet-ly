"""Tests for Tiferet-Ly Feature Reader Access (Lex and Parse Features)"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import pytest
import yaml
from tiferet import App
from tiferet.assets.core import TiferetAPIError
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils.lex import PlyLexer
from tiferet_ly.utils.parse import PlyParser

# *** constants

# ** constant: assets
ASSETS = Path(__file__).resolve().parents[2] / 'tiferet_ly' / 'assets'

# ** constant: configs
CONFIGS = Path(__file__).resolve().parents[2] / 'configs'

# *** functions

# ** function: build_app
def build_app(tmp_path, monkeypatch) -> App:
    '''
    Wire an App session whose DI points at a tmp_path arith catalogue.

    :param tmp_path: The pytest temporary directory.
    :type tmp_path: Path
    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :return: The wired app.
    :rtype: App
    '''

    # Write the arithmetic catalogues.
    tokens_path = tmp_path / 'tokens.yml'
    productions_path = tmp_path / 'productions.yml'
    grammars_path = tmp_path / 'grammars.yml'
    tokens_path.write_text(
        yaml.safe_dump({
            'tokens': [
                {'NUMBER': {
                    'grammar_id': 'arith',
                    'pattern': r'\d+',
                    'action': 't.value = int(t.value)\nreturn t',
                }},
                {'PLUS': {
                    'grammar_id': 'arith',
                    'pattern': r'\+',
                }},
            ],
        }),
        encoding='utf-8',
    )
    productions_path.write_text(
        yaml.safe_dump({
            'production_rules': [
                {'expr': {
                    'grammar_id': 'arith',
                    'spec': 'expr : expr PLUS term',
                    'action': 'p[0] = p[1] + p[3]',
                }},
                {'expr': {
                    'grammar_id': 'arith',
                    'spec': 'expr : term',
                }},
                {'term': {
                    'grammar_id': 'arith',
                    'spec': 'term : NUMBER',
                }},
            ],
        }),
        encoding='utf-8',
    )
    grammars_path.write_text(
        yaml.safe_dump({
            'grammars': {
                'arith': {
                    'parent_ids': [],
                    'start': 'expr',
                },
            },
        }),
        encoding='utf-8',
    )

    # Point DI catalogue paths and the app session at the temporary files.
    di_path = tmp_path / 'di.yml'
    di_path.write_text(
        (ASSETS / 'di.yml').read_text(encoding='utf-8')
        .replace('token_config: tokens.yml', f'token_config: {tokens_path}')
        .replace(
            'production_config: productions.yml',
            f'production_config: {productions_path}',
        )
        .replace('grammar_config: grammars.yml', f'grammar_config: {grammars_path}'),
        encoding='utf-8',
    )
    app_path = tmp_path / 'app.yml'
    app_path.write_text(
        (ASSETS / 'app.yml').read_text(encoding='utf-8')
        .replace(
            'logging_config: tiferet_ly/assets/app.yml',
            f'logging_config: {ASSETS / "app.yml"}',
        )
        .replace(
            'di_config: tiferet_ly/assets/di.yml',
            f'di_config: {di_path}',
        )
        .replace(
            'error_config: tiferet_ly/assets/error.yml',
            f'error_config: {ASSETS / "error.yml"}',
        )
        .replace(
            'feature_config: tiferet_ly/assets/feature.yml',
            f'feature_config: {ASSETS / "feature.yml"}',
        ),
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)

    # Return the wired app.
    return App('tiferet_ly', app_config=str(app_path))


# ** function: spy
def spy(monkeypatch, cls, method_name: str) -> list:
    '''
    Record each call to a reader method and delegate to the original.

    :param monkeypatch: The pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param cls: The reader class.
    :type cls: type
    :param method_name: The method to wrap.
    :type method_name: str
    :return: The list receiving (args, kwargs) per call.
    :rtype: list
    '''

    # Wrap the original method.
    calls = []
    original = getattr(cls, method_name)

    def wrapper(self, *args, **kwargs):
        calls.append((args, kwargs))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(cls, method_name, wrapper)
    return calls


# ** function: number
def number(value):
    '''
    A caller-supplied rewrite factory: the identity on a token value.

    :param value: The token value.
    :type value: Any
    :return: The value as given.
    :rtype: Any
    '''

    # Return the value unchanged.
    return value

# *** classes

# ** class: num
class Num(int):
    '''
    A caller-supplied rewrite class used for identity checks.
    '''

# *** tests

# ** test: feature_catalogues_name_reader_inputs
def test_feature_catalogues_name_reader_inputs() -> None:
    '''
    Test both feature catalogues: byte-identical, optional rewrites on lex
    and parse, optional parse text, no lexemes key, and the parse
    description naming lexemes.
    '''

    # Load both catalogues.
    assets_text = (ASSETS / 'feature.yml').read_bytes()
    configs_text = (CONFIGS / 'feature.yml').read_bytes()
    assert assets_text == configs_text
    data = yaml.safe_load(assets_text)
    lex = data['features']['lex']['default']
    parse = data['features']['parse']['default']

    # Assert the request schemas.
    optional_dict = {'type': 'dict', 'required': False}
    assert lex['params_schema'] == {'rewrites': optional_dict}
    assert parse['params_schema'] == {
        'grammar_id': 'str',
        'text': {'type': 'str', 'required': False},
        'render_result': {'type': 'bool', 'required': False, 'default': False},
        'rewrites': optional_dict,
    }

    # Assert descriptions.
    assert parse['description'] == (
        'Parse text, or a recognized lexeme stream supplied as lexemes, '
        'against a declared grammar.'
    )
    assert lex['description'] == 'Tokenize text against a declared grammar.'

    # Assert steps gain no parameters and render stays wired.
    for feature, step_id in ((lex, 'lex_text'), (parse, 'parse_text')):
        step = next(step for step in feature['steps'] if step['service_id'] == step_id)
        assert 'parameters' not in step
    assert parse['steps'][-2]['service_id'] == 'parse_text'
    assert parse['steps'][-2]['data_key'] == 'result'
    assert parse['steps'][-1] == {
        'service_id': 'render_result',
        'name': 'Render parse result',
        'parameters': {
            'result': '$r.result',
            'render_result': '$r.render_result',
        },
    }


# ** test: parse_feature_accepts_lexeme_stream
def test_parse_feature_accepts_lexeme_stream(tmp_path, monkeypatch) -> None:
    '''
    Test that parse.default with lexemes and no text passes request
    validation and the same list reaches the parser service.
    '''

    # Wire the app and spy on the parser.
    app = build_app(tmp_path, monkeypatch)
    calls = spy(monkeypatch, PlyParser, 'parse')
    stream = [
        LexemeAggregate(type='NUMBER', value=1, lineno=1, lexpos=0),
        LexemeAggregate(type='PLUS', value='+', lineno=1, lexpos=1),
        LexemeAggregate(type='NUMBER', value=2, lineno=1, lexpos=2),
    ]

    # Parse from the stream, raw and rendered.
    value = app.run('parse.default', data={'grammar_id': 'arith', 'lexemes': stream})
    rendered = app.run(
        'parse.default',
        data={'grammar_id': 'arith', 'lexemes': stream, 'render_result': True},
    )

    # Assert the same list object, text None, and the usual results.
    args, kwargs = calls[0]
    assert args[4] is None
    assert kwargs['lexemes'] is stream
    assert all(isinstance(lexeme, LexemeAggregate) for lexeme in kwargs['lexemes'])
    assert value == 3
    assert rendered == '3'


# ** test: parse_feature_without_text_or_lexemes_fails_in_service
def test_parse_feature_without_text_or_lexemes_fails_in_service(tmp_path, monkeypatch) -> None:
    '''
    Test that parse.default with neither text nor lexemes passes request
    validation and fails in the service as PARSE_INPUT_INVALID (missing).
    '''

    # Wire the app and spy on the parser.
    app = build_app(tmp_path, monkeypatch)
    calls = spy(monkeypatch, PlyParser, 'parse')

    # Run with only the grammar id.
    with pytest.raises(ServiceError) as raised:
        app.run('parse.default', data={'grammar_id': 'arith'})

    # Assert the service rule, not request validation, rejected it.
    assert len(calls) == 1
    assert raised.value.error_code == 'PARSE_INPUT_INVALID'
    assert raised.value.kwargs['reason'] == 'missing'


# ** test: features_pass_rewrite_factories_through
def test_features_pass_rewrite_factories_through(tmp_path, monkeypatch) -> None:
    '''
    Test that lex and parse pass each rewrite class or callable through
    as the same object.
    '''

    # Wire the app and spy on both readers.
    app = build_app(tmp_path, monkeypatch)
    lex_calls = spy(monkeypatch, PlyLexer, 'tokenize')
    parse_calls = spy(monkeypatch, PlyParser, 'parse')
    rewrites = {'$num': Num, '$number': number}

    # Run both features with rewrites.
    lexemes = app.run(
        'lex.default',
        data={'grammar_id': 'arith', 'text': '1+2', 'rewrites': rewrites},
    )
    value = app.run(
        'parse.default',
        data={'grammar_id': 'arith', 'text': '1+2', 'rewrites': rewrites},
    )

    # Assert each factory is the caller's object.
    for calls in (lex_calls, parse_calls):
        received = calls[0][1]['rewrites']
        assert received.keys() == rewrites.keys()
        assert received['$num'] is Num
        assert received['$number'] is number
    assert [lexeme.type for lexeme in lexemes] == ['NUMBER', 'PLUS', 'NUMBER']
    assert value == 3


# ** test: features_reject_non_dict_rewrites
@pytest.mark.parametrize('feature_id', ['lex.default', 'parse.default'])
def test_features_reject_non_dict_rewrites(tmp_path, monkeypatch, feature_id) -> None:
    '''
    Test that a non-dict rewrites fails request validation before any step.
    '''

    # Wire the app and spy on the first catalogue step's reader.
    app = build_app(tmp_path, monkeypatch)
    lex_calls = spy(monkeypatch, PlyLexer, 'tokenize')
    parse_calls = spy(monkeypatch, PlyParser, 'parse')

    # Run with a list as rewrites.
    with pytest.raises(TiferetAPIError) as raised:
        app.run(
            feature_id,
            data={'grammar_id': 'arith', 'text': '1', 'rewrites': ['not', 'a', 'dict']},
        )

    # Assert request validation failed on rewrites and no reader ran.
    assert raised.value.error_code == 'REQUEST_VALIDATION_FAILED'
    assert [violation['field'] for violation in raised.value.kwargs['violations']] == ['rewrites']
    assert lex_calls == []
    assert parse_calls == []


# ** test: text_features_are_unchanged
def test_text_features_are_unchanged(tmp_path, monkeypatch) -> None:
    '''
    Test that text-only lex and parse return what they returned before.
    '''

    # Wire the app.
    app = build_app(tmp_path, monkeypatch)

    # Run the historical calls.
    lexemes = app.run('lex.default', data={'grammar_id': 'arith', 'text': '1+2'})
    value = app.run('parse.default', data={'grammar_id': 'arith', 'text': '1+2'})
    rendered = app.run(
        'parse.default',
        data={'grammar_id': 'arith', 'text': '1+2', 'render_result': True},
    )

    # Assert the historical results.
    assert [lexeme.type for lexeme in lexemes] == ['NUMBER', 'PLUS', 'NUMBER']
    assert [lexeme.value for lexeme in lexemes] == [1, '+', 2]
    assert value == 3
    assert type(value) is int
    assert rendered == '3'
