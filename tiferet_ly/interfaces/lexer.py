"""Tiferet-Ly Lexer Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Dict, List, Optional

# ** app
from tiferet import Service
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.token import TokenRuleAggregate

# *** interfaces

# ** interface: lexer_service
class LexerService(Service):
    '''
    Vertical interface for assembling a lexer and tokenizing text against
    a declared grammar's selected token set.
    '''

    # * method: tokenize
    @abstractmethod
    def tokenize(self,
            grammar_id: str,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            text: str,
            rewrites: Optional[Dict[str, type]] = None) -> List[LexemeAggregate]:
        '''
        Tokenize text against the selected token rules for a grammar.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param text: The source text to tokenize.
        :type text: str
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: The recognized lexemes in source order.
        :rtype: List[LexemeAggregate]
        '''

        # Not implemented.
        raise NotImplementedError('tokenize method is required for LexerService.')
