"""Tiferet-Ly Grammar Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional

# ** app
from tiferet.interfaces.core import Service
from ..mappers.grammar import GrammarAggregate

# *** interfaces

# ** interface: grammar_service
class GrammarService(Service):
    '''
    Vertical interface for managing Grammar definitions.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, id: str) -> bool:
        '''
        Check whether a grammar with the given ID exists.

        :param id: The grammar identifier.
        :type id: str
        :return: True if the grammar exists, otherwise False.
        :rtype: bool
        '''
        # Not implemented.
        raise NotImplementedError('exists method is required for GrammarService.')

    # * method: get
    @abstractmethod
    def get(self, id: str) -> Optional[GrammarAggregate]:
        '''
        Retrieve a Grammar by its ID.

        :param id: The grammar identifier.
        :type id: str
        :return: The GrammarAggregate, or None if not found.
        :rtype: Optional[GrammarAggregate]
        '''
        # Not implemented.
        raise NotImplementedError('get method is required for GrammarService.')

    # * method: list
    @abstractmethod
    def list(self) -> List[GrammarAggregate]:
        '''
        List all Grammar aggregates.

        :return: All stored grammars.
        :rtype: List[GrammarAggregate]
        '''
        # Not implemented.
        raise NotImplementedError('list method is required for GrammarService.')

    # * method: save
    @abstractmethod
    def save(self, grammar: GrammarAggregate) -> None:
        '''
        Persist a Grammar aggregate.

        :param grammar: The grammar aggregate to persist.
        :type grammar: GrammarAggregate
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('save method is required for GrammarService.')

    # * method: delete
    @abstractmethod
    def delete(self, id: str) -> None:
        '''
        Delete a Grammar by ID. Idempotent.

        :param id: The grammar identifier.
        :type id: str
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('delete method is required for GrammarService.')
