"""Tests for Tiferet-Ly Lex and Parse Domain Events"""

# *** imports

# ** core
import inspect
from unittest.mock import Mock

# ** infra
import pytest
from tiferet.assets.core import TiferetError
from tiferet.events.core import DomainEvent
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.interfaces.lexer import LexerService
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.events.lex import LexText
from tiferet_ly.events.parse import ParseText
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import SimpleProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate
from tiferet_ly.utils.core import PARSE_INPUT_INVALID_ID
from tiferet_ly.utils.parse import PlyParser

# *** functions

# ** function: catalogues
def catalogues() -> tuple:
    '''
    Construct a one-token, one-production arith catalogue.

    :return: The tokens, productions, and grammars.
    :rtype: tuple
    '''

    # NUMBER feeds expr directly.
    tokens = [SimpleTokenRuleAggregate(name='NUMBER', grammar_id='arith', pattern=r'\d+')]
    productions = [
        SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arith',
            spec='expr : NUMBER',
        ),
    ]
    grammars = [GrammarAggregate(id='arith', parent_ids=[], start='expr')]
    return tokens, productions, grammars

# *** classes

# ** class: shorthand
class Shorthand:
    '''
    A caller-supplied rewrite factory used for identity checks.
    '''

# *** tests

# ** test: lex_text_passes_catalogues_to_service
def test_lex_text_passes_catalogues_to_service() -> None:
    '''
    Test that LexText forwards collected catalogues to LexerService.
    '''

    # Handle LexText against a mocked lexer service.
    lexeme = LexemeAggregate(type='NUMBER', value=1, lineno=1, lexpos=0)
    lexer_service = Mock()
    lexer_service.tokenize.return_value = [lexeme]
    tokens = [SimpleTokenRuleAggregate(name='NUMBER', grammar_id='arith', pattern=r'\d+')]
    grammars = [GrammarAggregate(id='arith', parent_ids=[], start='expr')]
    result = DomainEvent.handle(
        LexText,
        dependencies={'lexer_service': lexer_service},
        grammar_id='arith',
        text='1',
        tokens=tokens,
        grammars=grammars,
    )

    # Assert the service was called with the collected catalogues.
    lexer_service.tokenize.assert_called_once_with(
        'arith',
        grammars,
        tokens,
        '1',
        rewrites=None,
    )
    assert result == [lexeme]


# ** test: parse_text_passes_catalogues_to_service
def test_parse_text_passes_catalogues_to_service() -> None:
    '''
    Test that ParseText forwards collected catalogues to ParserService.
    '''

    # Handle ParseText against a mocked parser service.
    parser_service = Mock()
    parser_service.parse.return_value = 3
    tokens = [SimpleTokenRuleAggregate(name='NUMBER', grammar_id='arith', pattern=r'\d+')]
    productions = [
        SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arith',
            spec='expr : NUMBER',
        ),
    ]
    grammars = [GrammarAggregate(id='arith', parent_ids=[], start='expr')]
    result = DomainEvent.handle(
        ParseText,
        dependencies={'parser_service': parser_service},
        grammar_id='arith',
        text='1',
        tokens=tokens,
        productions=productions,
        grammars=grammars,
    )

    # Assert the service was called with tokens, productions, and grammars.
    parser_service.parse.assert_called_once_with(
        'arith',
        grammars,
        tokens,
        productions,
        '1',
        lexemes=None,
        rewrites=None,
    )
    assert result == 3


# ** test: lex_text_keeps_text_second_and_forwards_rewrites
def test_lex_text_keeps_text_second_and_forwards_rewrites() -> None:
    '''
    Test that LexText keeps text as its second positional parameter and
    forwards the caller's rewrites mapping object by keyword.
    '''

    # Inspect the execute signature.
    params = inspect.signature(LexText.execute).parameters
    names = list(params)
    assert names[2] == 'text'
    assert params['text'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params['rewrites'].default is None

    # Handle LexText with a rewrites mapping.
    tokens, _productions, grammars = catalogues()
    rewrites = {'$sh': Shorthand}
    lexer_service = Mock()
    DomainEvent.handle(
        LexText,
        dependencies={'lexer_service': lexer_service},
        grammar_id='arith',
        text='1',
        tokens=tokens,
        grammars=grammars,
        rewrites=rewrites,
    )

    # Assert positional text and the same mapping object by keyword.
    args, kwargs = lexer_service.tokenize.call_args
    assert args == ('arith', grammars, tokens, '1')
    assert kwargs.keys() == {'rewrites'}
    assert kwargs['rewrites'] is rewrites
    assert list(inspect.signature(LexerService.tokenize).parameters) == [
        'self', 'grammar_id', 'grammars', 'tokens', 'text', 'rewrites',
    ]


# ** test: lex_text_still_requires_text
@pytest.mark.parametrize('text', [None, '', 'missing'])
def test_lex_text_still_requires_text(text) -> None:
    '''
    Test that LexText fails its required-parameter check for a missing,
    None, or blank text, and does not require rewrites.
    '''

    # Build keyword arguments without rewrites.
    tokens, _productions, grammars = catalogues()
    kwargs = dict(grammar_id='arith', tokens=tokens, grammars=grammars)
    if text != 'missing':
        kwargs['text'] = text
    lexer_service = Mock()

    # Handle LexText and expect the required-parameter failure.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            LexText,
            dependencies={'lexer_service': lexer_service},
            **kwargs,
        )

    # Assert the failure names text and the service was not called.
    assert 'text' in str(raised.value)
    assert 'rewrites' not in str(raised.value)
    lexer_service.tokenize.assert_not_called()


# ** test: parse_text_keeps_text_second_positionally
def test_parse_text_keeps_text_second_positionally() -> None:
    '''
    Test that ParseText keeps text second, binds a historical positional
    call as text, and a historical keyword call forwards lexemes=None and
    rewrites=None.
    '''

    # Inspect the execute signature.
    params = inspect.signature(ParseText.execute).parameters
    assert list(params)[2] == 'text'
    assert params['text'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD

    # A historical positional call binds its second argument as text.
    tokens, productions, grammars = catalogues()
    bound = inspect.signature(ParseText.execute).bind(
        None, 'arith', '1', tokens, productions, grammars,
    )
    assert bound.arguments['text'] == '1'
    assert bound.arguments['grammars'] is grammars

    # A historical keyword call with text and no lexemes.
    parser_service = Mock()
    DomainEvent.handle(
        ParseText,
        dependencies={'parser_service': parser_service},
        grammar_id='arith',
        text='1',
        tokens=tokens,
        productions=productions,
        grammars=grammars,
    )

    # Assert text stays in the positional slot.
    parser_service.parse.assert_called_once_with(
        'arith',
        grammars,
        tokens,
        productions,
        '1',
        lexemes=None,
        rewrites=None,
    )


# ** test: parse_text_forwards_lexemes_without_text
def test_parse_text_forwards_lexemes_without_text() -> None:
    '''
    Test that ParseText with lexemes and no text passes the required check
    and forwards text None and the same list object.
    '''

    # Handle ParseText with only a stream.
    tokens, productions, grammars = catalogues()
    stream = [LexemeAggregate(type='NUMBER', value='1', lineno=1, lexpos=0)]
    parser_service = Mock()
    DomainEvent.handle(
        ParseText,
        dependencies={'parser_service': parser_service},
        grammar_id='arith',
        tokens=tokens,
        productions=productions,
        grammars=grammars,
        lexemes=stream,
    )

    # Assert text None in the positional slot and the same list.
    args, kwargs = parser_service.parse.call_args
    assert args == ('arith', grammars, tokens, productions, None)
    assert kwargs['lexemes'] is stream
    assert kwargs['rewrites'] is None


# ** test: parse_text_leaves_exactly_one_to_service
@pytest.mark.parametrize('inputs, reason', [
    ({}, 'missing'),
    ({'text': '1', 'lexemes': []}, 'ambiguous'),
])
def test_parse_text_leaves_exactly_one_to_service(inputs, reason) -> None:
    '''
    Test that neither and both reach the service and fail there as
    PARSE_INPUT_INVALID, untranslated by the event.
    '''

    # Handle ParseText against the real parser service.
    tokens, productions, grammars = catalogues()
    with pytest.raises(ServiceError) as raised:
        DomainEvent.handle(
            ParseText,
            dependencies={'parser_service': PlyParser()},
            grammar_id='arith',
            tokens=tokens,
            productions=productions,
            grammars=grammars,
            **inputs,
        )

    # Assert the service's structured error and reason.
    assert raised.value.error_code == PARSE_INPUT_INVALID_ID
    assert raised.value.kwargs['reason'] == reason


# ** test: parse_text_forwards_rewrites_object
def test_parse_text_forwards_rewrites_object() -> None:
    '''
    Test that ParseText forwards the caller's rewrites mapping object.
    '''

    # Handle ParseText with text and rewrites.
    tokens, productions, grammars = catalogues()
    rewrites = {'$sh': Shorthand}
    parser_service = Mock()
    DomainEvent.handle(
        ParseText,
        dependencies={'parser_service': parser_service},
        grammar_id='arith',
        text='1',
        tokens=tokens,
        productions=productions,
        grammars=grammars,
        rewrites=rewrites,
    )

    # Assert the same object and an unchanged service signature.
    assert parser_service.parse.call_args.kwargs['rewrites'] is rewrites
    assert list(inspect.signature(ParserService.parse).parameters) == [
        'self', 'grammar_id', 'grammars', 'tokens', 'productions', 'text',
        'lexemes', 'rewrites',
    ]
