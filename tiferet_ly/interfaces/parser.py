"""Tiferet-Ly Parser Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Any, Dict, List, Optional

# ** app
from tiferet import Service
from ..mappers.grammar import GrammarAggregate
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
            text: str,
            rewrites: Optional[Dict[str, type]] = None) -> Any:
        '''
        Parse text against the selected rules for a grammar.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The unfiltered production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param text: The source text to parse.
        :type text: str
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: Whatever the start-symbol action left in p[0].
        :rtype: Any
        '''

        # Not implemented.
        raise NotImplementedError('parse method is required for ParserService.')
