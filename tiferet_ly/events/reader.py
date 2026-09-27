"""Tiferet Ly Reader Events"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.interfaces.lexer import LexerService
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.lexeme import LexemeAggregate
from .. import assets as a

# *** events

# ** event: lex_text
class LexText(DomainEvent):
    '''
    Read declared text as lexeme aggregates from the collected catalogues.

    An unknown grammar fails before the reader runs. Optional rewrites are
    forwarded when supplied.
    '''

    # * attribute: lexer_service
    lexer_service: LexerService

    # * init
    def __init__(self, lexer_service: LexerService) -> None:
        '''
        Initialize with the lexer service.

        :param lexer_service: The lexer service.
        :type lexer_service: LexerService
        '''

        # Set the lexer service dependency.
        self.lexer_service = lexer_service

    # * method: execute
    @DomainEvent.parameters_required(['grammar_id', 'text'])
    def execute(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
            **kwargs,
        ) -> list[LexemeAggregate]:
        '''
        Tokenize declared text with the collected catalogues.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read.
        :type text: str
        :param tokens: The collected token catalogue.
        :type tokens: list
        :param productions: The collected production catalogue.
        :type productions: list
        :param grammars: The collected grammar catalogue.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None.
        :type rewrites: dict | None
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The lexeme aggregates from the lexer service.
        :rtype: list[LexemeAggregate]
        '''

        # A grammar absent from the collected catalogue never reaches the reader.
        self.verify(
            any(grammar.id == grammar_id for grammar in grammars),
            a.grammar.GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar {grammar_id} was not found.',
            grammar_id=grammar_id,
        )

        # Forward the collected catalogues. Rewrites stay optional.
        return self.lexer_service.tokenize(
            grammar_id,
            text,
            tokens,
            productions,
            grammars,
            rewrites=rewrites,
        )

# ** event: parse_text
class ParseText(DomainEvent):
    '''
    Read declared text into the parser result from the collected catalogues.

    An unknown grammar fails before the reader runs. The result stays
    untyped so a later reader can return a tree without this event naming one.
    '''

    # * attribute: parser_service
    parser_service: ParserService

    # * init
    def __init__(self, parser_service: ParserService) -> None:
        '''
        Initialize with the parser service.

        :param parser_service: The parser service.
        :type parser_service: ParserService
        '''

        # Set the parser service dependency.
        self.parser_service = parser_service

    # * method: execute
    @DomainEvent.parameters_required(['grammar_id', 'text'])
    def execute(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
            **kwargs,
        ) -> Any:
        '''
        Parse declared text with the collected catalogues.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read.
        :type text: str
        :param tokens: The collected token catalogue.
        :type tokens: list
        :param productions: The collected production catalogue.
        :type productions: list
        :param grammars: The collected grammar catalogue.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None.
        :type rewrites: dict | None
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The untyped value from the parser service.
        :rtype: Any
        '''

        # A grammar absent from the collected catalogue never reaches the reader.
        self.verify(
            any(grammar.id == grammar_id for grammar in grammars),
            a.grammar.GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar {grammar_id} was not found.',
            grammar_id=grammar_id,
        )

        # Forward the collected catalogues. Rewrites stay optional.
        return self.parser_service.parse(
            grammar_id,
            text,
            tokens,
            productions,
            grammars,
            rewrites=rewrites,
        )
