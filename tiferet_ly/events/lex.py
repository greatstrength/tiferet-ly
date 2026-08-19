"""Tiferet-Ly Lex Domain Events"""

# *** imports

# ** core
from typing import List

# ** app
from tiferet.events.core import DomainEvent
from ..interfaces.lexer import LexerService
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.token import TokenRuleAggregate

# *** events

# ** event: lex_text
class LexText(DomainEvent):
    '''
    Thin Feature step that hands collected catalogues to LexerService.
    '''

    # * attribute: lexer_service
    lexer_service: LexerService

    # * init
    def __init__(self, lexer_service: LexerService):
        '''
        Initialize with the lexer service.

        :param lexer_service: The lexer service dependency.
        :type lexer_service: LexerService
        '''

        # Set the lexer service dependency.
        self.lexer_service = lexer_service

    # * method: execute
    @DomainEvent.parameters_required(['grammar_id', 'text', 'tokens', 'grammars'])
    def execute(self,
            grammar_id: str,
            text: str,
            tokens: List[TokenRuleAggregate],
            grammars: List[GrammarAggregate],
            **kwargs) -> List[LexemeAggregate]:
        '''
        Tokenize text through the injected lexer service.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param text: The source text to tokenize.
        :type text: str
        :param tokens: The collected token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param grammars: The collected grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The recognized lexemes.
        :rtype: List[LexemeAggregate]
        '''

        # Pass the already-collected catalogues through; do not select here.
        return self.lexer_service.tokenize(
            grammar_id,
            grammars,
            tokens,
            text,
        )
