"""Tiferet Ly Lexer Service"""

# *** imports

# ** core
from abc import abstractmethod

# ** app
from tiferet.interfaces import Service
from tiferet_ly.mappers.lexeme import LexemeAggregate

# *** interfaces

# ** interface: lexer_service
class LexerService(Service):
    '''
    The caller-visible contract for turning declared text into lexeme aggregates.

    Callers pass a grammar and the declared vocabulary. The result is a list of
    lexeme aggregates. This contract does not name a concrete reader.
    '''

    # * method: tokenize
    @abstractmethod
    def tokenize(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
        ) -> list[LexemeAggregate]:
        '''
        Turn declared text into lexeme aggregates for one grammar.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read.
        :type text: str
        :param tokens: The declared token rules.
        :type tokens: list
        :param productions: The declared production rules.
        :type productions: list
        :param grammars: The declared grammars.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None.
        :type rewrites: dict | None
        :return: The lexeme aggregates.
        :rtype: list[LexemeAggregate]
        '''
        raise NotImplementedError()
