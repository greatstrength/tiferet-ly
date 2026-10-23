"""Tiferet-Ly Token Service Interface"""

# *** imports

# ** core
from abc import abstractmethod
from typing import List, Optional, Union

# ** infra
from tiferet import Service

# ** app
from ..mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    SyntheticTokenRuleAggregate,
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
    def get(self, name: str, grammar_id: str) -> Optional[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]]:
        '''
        Retrieve a token rule aggregate by name and grammar_id.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The token rule aggregate, or None if not found.
        :rtype: Optional[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]]
        '''
        # Not implemented.
        raise NotImplementedError('get method is required for TokenService.')

    # * method: list
    @abstractmethod
    def list(self) -> List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]]:
        '''
        List every token rule aggregate unfiltered, in declared order.

        :return: All stored token rule aggregates.
        :rtype: List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]]
        '''
        # Not implemented.
        raise NotImplementedError('list method is required for TokenService.')

    # * method: save
    @abstractmethod
    def save(self, token: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]) -> None:
        '''
        Persist a token rule aggregate, replacing an existing
        ``(name, grammar_id)`` entry in place or appending when absent.

        :param token: The token rule aggregate to persist.
        :type token: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]
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
