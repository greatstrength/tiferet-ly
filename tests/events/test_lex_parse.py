"""Tests for Tiferet-Ly Lex and Parse Domain Events"""

# *** imports

# ** core
from unittest.mock import Mock

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.events.lex import LexText
from tiferet_ly.events.parse import ParseText
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import SimpleProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate

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
    lexer_service.tokenize.assert_called_once_with('arith', grammars, tokens, '1')
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
    )
    assert result == 3
