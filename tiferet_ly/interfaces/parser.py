"""Tiferet Ly Parser Service"""

# *** imports

# ** core
from abc import abstractmethod
from typing import Any

# ** infra
from tiferet.interfaces import Service

# *** interfaces

# ** interface: parser_service
class ParserService(Service):
    '''
    The caller-visible contract for reading declared text, or an already-recognized lexeme list, into a parse result.

    Callers pass a grammar and the declared vocabulary. The result is untyped
    so a later reader can return a tree without this contract naming one.
    '''

    # * method: parse
    @abstractmethod
    def parse(
            self,
            grammar_id: str,
            text: str | None,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
            lexemes: list | None = None,
        ) -> Any:
        '''
        Read declared text, or an already-recognized lexeme list, into an untyped parse result.

        Exactly one of text and lexemes must be supplied.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read, or None when lexemes is supplied.
        :type text: str | None
        :param tokens: The declared token rules.
        :type tokens: list
        :param productions: The declared production rules.
        :type productions: list
        :param grammars: The declared grammars.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None.
        :type rewrites: dict | None
        :param lexemes: Already-recognized lexemes. Defaults to None. Mutually exclusive with text.
        :type lexemes: list | None
        :return: The parse result.
        :rtype: Any
        '''
        raise NotImplementedError()
