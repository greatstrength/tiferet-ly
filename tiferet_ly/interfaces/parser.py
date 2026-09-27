"""Tiferet Ly Parser Service"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Any

# ** app
from tiferet.interfaces import Service

# *** interfaces

# ** interface: parser_service
class ParserService(Service):
    '''
    The caller-visible contract for reading declared text into a parse result.

    Callers pass a grammar and the declared vocabulary. The result is untyped
    so a later reader can return a tree without this contract naming one.
    '''

    # * method: parse
    @abstractmethod
    def parse(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
        ) -> Any:
        '''
        Read declared text for one grammar into an untyped parse result.

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
        :return: The parse result.
        :rtype: Any
        '''
        raise NotImplementedError()
