"""Tiferet-Ly Production Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional, Union

# ** app
from tiferet.interfaces.core import Service
from ..domain.production import (
    ComplexProductionRule,
    SimpleProductionRule,
)

# *** interfaces

# ** interface: production_service
class ProductionService(Service):
    '''
    Vertical interface for managing production rule definitions.

    Lookup keys are the composite pair ``(name, grammar_id)`` rather than a
    single id, matching per-grammar_id name uniqueness on ProductionRule.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Check whether a production rule with the given name and grammar_id exists.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: True if the production rule exists, otherwise False.
        :rtype: bool
        '''
        # Not implemented.
        raise NotImplementedError('exists method is required for ProductionService.')

    # * method: get
    @abstractmethod
    def get(self, name: str, grammar_id: str) -> Optional[Union[SimpleProductionRule, ComplexProductionRule]]:
        '''
        Retrieve a production rule by name and grammar_id.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The production rule, or None if not found.
        :rtype: Optional[Union[SimpleProductionRule, ComplexProductionRule]]
        '''
        # Not implemented.
        raise NotImplementedError('get method is required for ProductionService.')

    # * method: list
    @abstractmethod
    def list(self) -> List[Union[SimpleProductionRule, ComplexProductionRule]]:
        '''
        List every production rule unfiltered, in declared order.

        :return: All stored production rules.
        :rtype: List[Union[SimpleProductionRule, ComplexProductionRule]]
        '''
        # Not implemented.
        raise NotImplementedError('list method is required for ProductionService.')

    # * method: save
    @abstractmethod
    def save(self, production: Union[SimpleProductionRule, ComplexProductionRule]) -> None:
        '''
        Persist a production rule, replacing an existing ``(name, grammar_id)``
        entry in place or appending when absent.

        :param production: The production rule to persist.
        :type production: Union[SimpleProductionRule, ComplexProductionRule]
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('save method is required for ProductionService.')

    # * method: delete
    @abstractmethod
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Delete a production rule by name and grammar_id. Idempotent.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('delete method is required for ProductionService.')
