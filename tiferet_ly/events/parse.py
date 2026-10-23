"""Tiferet-Ly Parse Domain Events"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional

# ** infra
from tiferet.events.core import DomainEvent

# ** app
from ..interfaces.parser import ParserService
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate
from .core import parameters_required

# *** events

# ** event: parse_text
class ParseText(DomainEvent):
    '''
    Thin Feature step that hands collected catalogues to ParserService.
    '''

    # * attribute: parser_service
    parser_service: ParserService

    # * init
    def __init__(self, parser_service: ParserService):
        '''
        Initialize with the parser service.

        :param parser_service: The parser service dependency.
        :type parser_service: ParserService
        '''

        # Set the parser service dependency.
        self.parser_service = parser_service

    # * method: execute
    @parameters_required([
        'grammar_id',
        'tokens',
        'productions',
        'grammars',
    ])
    def execute(self,
            grammar_id: str,
            text: Optional[str] = None,
            tokens: Optional[List[TokenRuleAggregate]] = None,
            productions: Optional[List[ProductionRuleAggregate]] = None,
            grammars: Optional[List[GrammarAggregate]] = None,
            lexemes: Optional[List[LexemeAggregate]] = None,
            rewrites: Optional[Dict[str, type]] = None,
            **kwargs) -> Any:
        '''
        Parse text, or a recognized lexeme stream, through the parser service.

        Exactly one of text or lexemes is the service's rule, not this
        event's; both are forwarded as given.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param text: The source text to parse, or None for a lexeme stream.
        :type text: Optional[str]
        :param tokens: The collected token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The collected production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param grammars: The collected grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param lexemes: Optional recognized lexeme stream, forwarded as given.
        :type lexemes: Optional[List[LexemeAggregate]]
        :param rewrites: Optional action shorthand bindings, forwarded as given.
        :type rewrites: Optional[Dict[str, type]]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: Whatever the start-symbol action left in p[0].
        :rtype: Any
        '''

        # Pass the already-collected catalogues through; do not select here.
        return self.parser_service.parse(
            grammar_id,
            grammars,
            tokens,
            productions,
            text,
            lexemes=lexemes,
            rewrites=rewrites,
        )
