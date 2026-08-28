"""Tiferet-Ly Parser Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Any, Dict, List, Optional

# ** app
from tiferet import Service
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate

# *** interfaces

# ** interface: parser_service
class ParserService(Service):
    '''
    Vertical interface for assembling a parser and parsing text against a
    declared grammar's selected token and production set.
    '''

    # * method: parse
    @abstractmethod
    def parse(self,
            grammar_id: str,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            productions: List[ProductionRuleAggregate],
            text: Optional[str] = None,
            lexemes: Optional[List[LexemeAggregate]] = None,
            rewrites: Optional[Dict[str, type]] = None) -> Any:
        '''
        Parse against the selected rules for a grammar, from source text
        or from an already-recognized lexeme stream.

        Exactly one of text or lexemes must be supplied. When lexemes is
        given, no PLY lexer is built or run at all.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The unfiltered production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param text: The source text to parse. Mutually exclusive with lexemes.
        :type text: Optional[str]
        :param lexemes: An already-recognized lexeme stream to parse. Mutually exclusive with text.
        :type lexemes: Optional[List[LexemeAggregate]]
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: Whatever the start-symbol action left in p[0].
        :rtype: Any
        '''

        # Not implemented.
        raise NotImplementedError('parse method is required for ParserService.')
