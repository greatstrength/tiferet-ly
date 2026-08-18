"""Tiferet-Ly Parse Domain Events"""

# *** imports

# ** core
from typing import Any, List

# ** app
from tiferet.events.core import DomainEvent
from ..interfaces.parser import ParserService
from ..mappers.grammar import GrammarAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate

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
    @DomainEvent.parameters_required([
        'grammar_id',
        'text',
        'tokens',
        'productions',
        'grammars',
    ])
    def execute(self,
            grammar_id: str,
            text: str,
            tokens: List[TokenRuleAggregate],
            productions: List[ProductionRuleAggregate],
            grammars: List[GrammarAggregate],
            **kwargs) -> Any:
        '''
        Parse text through the injected parser service.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param text: The source text to parse.
        :type text: str
        :param tokens: The collected token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The collected production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param grammars: The collected grammar catalogue.
        :type grammars: List[GrammarAggregate]
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
        )
