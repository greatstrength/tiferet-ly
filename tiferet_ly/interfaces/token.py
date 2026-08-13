"""Tiferet-Ly Token Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional, Union

# ** app
from tiferet.interfaces.core import Service
from ..domain.token import (
    ComplexTokenRule,
    SimpleTokenRule,
)

# *** interfaces

# ** interface: token_service
class TokenService(Service):
    '''
    Vertical interface for managing token rule definitions.

    Lookup keys are the composite pair ``(name, grammar_id)`` rather than a
    single id, matching per-grammar_id name uniqueness on TokenRule.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Check whether a token rule with the given name and grammar_id exists.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: True if the token rule exists, otherwise False.
        :rtype: bool
        '''
        # Not implemented.
        raise NotImplementedError('exists method is required for TokenService.')

    # * method: get
    @abstractmethod
    def get(self, name: str, grammar_id: str) -> Optional[Union[SimpleTokenRule, ComplexTokenRule]]:
        '''
        Retrieve a token rule by name and grammar_id.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The token rule, or None if not found.
        :rtype: Optional[Union[SimpleTokenRule, ComplexTokenRule]]
        '''
        # Not implemented.
        raise NotImplementedError('get method is required for TokenService.')

    # * method: list
    @abstractmethod
    def list(self) -> List[Union[SimpleTokenRule, ComplexTokenRule]]:
        '''
        List every token rule unfiltered, in declared order.

        :return: All stored token rules.
        :rtype: List[Union[SimpleTokenRule, ComplexTokenRule]]
        '''
        # Not implemented.
        raise NotImplementedError('list method is required for TokenService.')

    # * method: save
    @abstractmethod
    def save(self, token: Union[SimpleTokenRule, ComplexTokenRule]) -> None:
        '''
        Persist a token rule, replacing an existing ``(name, grammar_id)``
        entry in place or appending when absent.

        :param token: The token rule to persist.
        :type token: Union[SimpleTokenRule, ComplexTokenRule]
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('save method is required for TokenService.')

    # * method: delete
    @abstractmethod
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Delete a token rule by name and grammar_id. Idempotent.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''
        # Not implemented.
        raise NotImplementedError('delete method is required for TokenService.')
