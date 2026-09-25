"""Tiferet Ly Grammar Service"""

# *** imports

# ** core
from abc import abstractmethod

# ** app
from tiferet.interfaces import Service
from tiferet_ly.mappers.grammar import GrammarAggregate

# *** interfaces

# ** interface: grammar_service
class GrammarService(Service):
    '''
    The configuration contract for a lean grammar addressed by its identifier.

    A stored grammar is one mapping key, not a name-and-grammar pair. Callers
    can ask whether that key is stored, read it, and list every grammar once.
    The contract does not check parents or resolve the start production.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Report whether that grammar identifier is a key in grammars.

        :param id: The grammar identifier.
        :type id: str
        :return: True when that key is stored, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, id: str) -> GrammarAggregate | None:
        '''
        Return the grammar for that key, or None.

        :param id: The grammar identifier.
        :type id: str
        :return: The stored grammar aggregate, or None.
        :rtype: GrammarAggregate | None
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self) -> list[GrammarAggregate]:
        '''
        Return every stored grammar once.

        File-position order is not a requirement.

        :return: The stored grammar aggregates.
        :rtype: list[GrammarAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, grammar: GrammarAggregate) -> None:
        '''
        Insert or replace the entry whose key is the grammar identifier.

        :param grammar: The grammar aggregate to persist.
        :type grammar: GrammarAggregate
        :return: None
        :rtype: None
        '''
        raise NotImplementedError()

    # * method: delete
    @abstractmethod
    def delete(self, id: str) -> None:
        '''
        Remove that grammar key. Absence does not raise.

        :param id: The grammar identifier.
        :type id: str
        :return: None
        :rtype: None
        '''
        raise NotImplementedError()
