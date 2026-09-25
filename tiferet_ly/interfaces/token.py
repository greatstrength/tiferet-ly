"""Tiferet Ly Token Service"""

# *** imports

# ** core
from abc import abstractmethod

# ** app
from tiferet.interfaces import Service
from tiferet_ly.mappers.token import TokenRuleAggregate

# *** interfaces

# ** interface: token_service
class TokenService(Service):
    '''
    The configuration contract for declared token rules addressed by name and grammar.

    A stored token is the pair ``(name, grammar_id)``, not a single identifier
    and not a name alone. Callers can ask whether that pair is stored, read the
    first match, and list every token in declared order.
    '''

    # * method: exists
    @abstractmethod
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Report whether any stored token has the exact name and grammar pair.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: True when a stored token has that pair, otherwise False.
        :rtype: bool
        '''
        raise NotImplementedError()

    # * method: get
    @abstractmethod
    def get(self, name: str, grammar_id: str) -> TokenRuleAggregate | None:
        '''
        Return the first stored token with the exact name and grammar pair.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: The first matching token aggregate, or None.
        :rtype: TokenRuleAggregate | None
        '''
        raise NotImplementedError()

    # * method: list
    @abstractmethod
    def list(self) -> list[TokenRuleAggregate]:
        '''
        Return every stored token, unfiltered, in declared order.

        :return: The stored token aggregates.
        :rtype: list[TokenRuleAggregate]
        '''
        raise NotImplementedError()

    # * method: save
    @abstractmethod
    def save(self, token: TokenRuleAggregate) -> None:
        '''
        Replace the first matching pair in place, or append when the pair is absent.

        :param token: The token aggregate to persist.
        :type token: TokenRuleAggregate
        :return: None
        :rtype: None
        '''
        raise NotImplementedError()

    # * method: delete
    @abstractmethod
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Remove the first matching pair. Absence does not raise.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''
        raise NotImplementedError()
