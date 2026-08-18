"""Tiferet-Ly Token Domain Events"""

# *** imports

# ** core
from typing import List, Optional, Union

# ** app
from tiferet.events.core import DomainEvent
from .. import assets as a
from ..interfaces.token import TokenService
from ..mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)

# *** events

# ** event: token_event
class TokenEvent(DomainEvent):
    '''
    Base event providing the shared TokenService dependency for token writes.

    Token identity is the composite pair ``(name, grammar_id)``; names are
    unique within one grammar and do not require that grammar to exist yet.
    '''

    # * attribute: token_service
    token_service: TokenService

    # * init
    def __init__(self, token_service: TokenService):
        '''
        Initialize the token event with its shared service dependency.

        :param token_service: The token service shared across token events.
        :type token_service: TokenService
        '''

        # Set the token service dependency.
        self.token_service = token_service

    # * method: _require_token
    def _require_token(
            self,
            name: str,
            grammar_id: str) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Load a token by composite key and verify it exists.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The loaded token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Retrieve the token by composite key.
        token = self.token_service.get(name, grammar_id)

        # Verify the token exists.
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Return the loaded token.
        return token


# ** event: add_token
class AddToken(TokenEvent):
    '''
    Event to add a new token rule under a grammar.

    Constructs a simple aggregate when ``action`` is omitted and a complex
    aggregate when it is provided. The owning grammar need not exist yet.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'pattern'])
    def execute(self,
            name: str,
            grammar_id: str,
            pattern: str,
            action: Optional[str] = None,
            **kwargs) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Add a new token rule.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param pattern: The regular expression pattern.
        :type pattern: str
        :param action: Optional encoded action source for a complex token.
        :type action: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Verify the token name is unique within the grammar.
        self.verify(
            not self.token_service.exists(name, grammar_id),
            a.error.TOKEN_ALREADY_EXISTS_ID,
            message=f'Token already exists: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Construct the matching simple or complex aggregate.
        if action is None:
            token = SimpleTokenRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                pattern=pattern,
            )
        else:
            token = ComplexTokenRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                pattern=pattern,
                action=action,
            )

        # Persist the new token.
        self.token_service.save(token)

        # Return the created token.
        return token


# ** event: get_token
class GetToken(TokenEvent):
    '''
    Event to retrieve a token rule by name and grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(self,
            name: str,
            grammar_id: str,
            **kwargs) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Retrieve a token rule by composite key.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Load and return the token, raising when it is absent.
        return self._require_token(name, grammar_id)


# ** event: list_tokens
class ListTokens(TokenEvent):
    '''
    Event to list every token rule unfiltered, in declared order.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]:
        '''
        List every stored token rule.

        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: All stored token aggregates.
        :rtype: List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]
        '''

        # Return the unfiltered catalogue.
        return self.token_service.list()


# ** event: rename_token
class RenameToken(TokenEvent):
    '''
    Event to rename a token rule within its grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'new_name'])
    def execute(self,
            name: str,
            grammar_id: str,
            new_name: str,
            **kwargs) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Rename a token rule.

        :param name: The current token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param new_name: The new token rule name.
        :type new_name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Load the token that will be renamed.
        token = self._require_token(name, grammar_id)

        # Verify the destination pair is free unless it is the same pair.
        same_pair = new_name == name
        self.verify(
            same_pair or not self.token_service.exists(new_name, grammar_id),
            a.error.TOKEN_ALREADY_EXISTS_ID,
            message=f'Token already exists: {new_name} under {grammar_id}.',
            name=new_name,
            grammar_id=grammar_id,
        )

        # Apply the rename mutator and persist.
        token.rename(new_name)
        self.token_service.save(token)

        # Return the updated token.
        return token


# ** event: reassign_token_grammar
class ReassignTokenGrammar(TokenEvent):
    '''
    Event to move a token rule to another grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'new_grammar_id'])
    def execute(self,
            name: str,
            grammar_id: str,
            new_grammar_id: str,
            **kwargs) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Reassign a token rule to another grammar.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is currently declared under.
        :type grammar_id: str
        :param new_grammar_id: The grammar the rule should be declared under.
        :type new_grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Load the token that will be reassigned.
        token = self._require_token(name, grammar_id)

        # Verify the destination pair is free unless it is the same pair.
        same_pair = new_grammar_id == grammar_id
        self.verify(
            same_pair or not self.token_service.exists(name, new_grammar_id),
            a.error.TOKEN_ALREADY_EXISTS_ID,
            message=f'Token already exists: {name} under {new_grammar_id}.',
            name=name,
            grammar_id=new_grammar_id,
        )

        # Apply the reassign mutator and persist.
        token.reassign_grammar(new_grammar_id)
        self.token_service.save(token)

        # Return the updated token.
        return token


# ** event: set_token_pattern
class SetTokenPattern(TokenEvent):
    '''
    Event to replace a token rule's regular expression pattern.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'pattern'])
    def execute(self,
            name: str,
            grammar_id: str,
            pattern: str,
            **kwargs) -> Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]:
        '''
        Set a token rule's pattern.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param pattern: The new regular expression pattern.
        :type pattern: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated token aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        '''

        # Load the token, apply the pattern mutator, and persist.
        token = self._require_token(name, grammar_id)
        token.set_pattern(pattern)
        self.token_service.save(token)

        # Return the updated token.
        return token


# ** event: set_token_action
class SetTokenAction(TokenEvent):
    '''
    Event to replace a complex token rule's action source.

    Simple tokens cannot gain an action in place; that is a remove-and-add.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'action'])
    def execute(self,
            name: str,
            grammar_id: str,
            action: str,
            **kwargs) -> ComplexTokenRuleAggregate:
        '''
        Set a complex token rule's action.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param action: The new encoded action source.
        :type action: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated complex token aggregate.
        :rtype: ComplexTokenRuleAggregate
        '''

        # Load the token and verify it already carries an action.
        token = self._require_token(name, grammar_id)
        self.verify(
            isinstance(token, ComplexTokenRuleAggregate),
            a.error.TOKEN_ACTION_NOT_SUPPORTED_ID,
            message=f'Token action is not supported: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Apply the action mutator and persist.
        token.set_action(action)
        self.token_service.save(token)

        # Return the updated token.
        return token


# ** event: remove_token
class RemoveToken(TokenEvent):
    '''
    Event to delete a token rule by name and grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(self, name: str, grammar_id: str, **kwargs) -> tuple:
        '''
        Delete a token rule.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The identity that was requested for deletion.
        :rtype: tuple
        '''

        # Delete the token; the repository delete is idempotent.
        self.token_service.delete(name, grammar_id)

        # Return the identity that was given.
        return (name, grammar_id)
