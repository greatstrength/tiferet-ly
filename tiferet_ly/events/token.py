"""Tiferet Ly Token Events"""

# *** imports

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.interfaces.token import TokenService
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from .. import assets as a

# *** events

# ** event: token_event
class TokenEvent(DomainEvent):
    '''
    Shared access for a token addressed by name and grammar.

    The pair is the identity. These events do not ask whether the grammar
    id names a stored grammar.
    '''

    # * attribute: token_service
    token_service: TokenService

    # * init
    def __init__(self, token_service: TokenService) -> None:
        '''
        Initialize with the token service.

        :param token_service: The token service.
        :type token_service: TokenService
        '''

        # Set the token service dependency.
        self.token_service = token_service

# ** event: add_token
class AddToken(TokenEvent):
    '''
    Declare a token for one grammar without requiring that grammar to exist.

    An omitted or missing action is a simple token. A string action is a
    complex token. The same name may be declared again under another grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'pattern'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            pattern: str,
            action: str | None = None,
            **kwargs,
        ) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Add a token when its name and grammar pair is not already stored.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that will own the token.
        :type grammar_id: str
        :param pattern: The declared token pattern.
        :type pattern: str
        :param action: Action source. None selects a simple token.
        :type action: str | None
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # Reject a pair that is already stored. Do not save it again.
        self.verify(
            not self.token_service.exists(name, grammar_id),
            a.error.TOKEN_ALREADY_EXISTS_ID,
            message=f'Token already exists: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # A string action is complex. Omitted and None stay simple.
        if isinstance(action, str):
            token = ComplexTokenRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                pattern=pattern,
                action=action,
            )
        else:
            token = SimpleTokenRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                pattern=pattern,
            )

        # Persist and return the same aggregate.
        self.token_service.save(token)
        return token

# ** event: get_token
class GetToken(TokenEvent):
    '''
    Read one token by its name and grammar pair.

    A missing pair is a not-found failure, not an empty result.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            **kwargs,
        ) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Return the token stored under the name and grammar pair.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The stored token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # A missing pair is not an empty success.
        token = self.token_service.get(name, grammar_id)
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Return the loaded aggregate.
        return token

# ** event: list_tokens
class ListTokens(TokenEvent):
    '''
    Return every stored token in declared order.

    The list is not filtered by grammar.
    '''

    # * method: execute
    def execute(
            self,
            **kwargs,
        ) -> list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate]:
        '''
        Return the token catalogue in the order the service already has.

        :param kwargs: Additional keyword arguments. Grammar id is ignored.
        :type kwargs: dict
        :return: The stored token aggregates.
        :rtype: list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate]
        '''

        # Do not sort or drop rows. Declared order is the service order.
        return self.token_service.list()

# ** event: rename_token
class RenameToken(TokenEvent):
    '''
    Rename a token inside its grammar when the new pair is free.

    Renaming to the loaded name is the same pair and is not a duplicate.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'new_name'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            new_name: str,
            **kwargs,
        ) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Rename a stored token and save it.

        :param name: The current token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :param new_name: The replacement token name.
        :type new_name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # A missing pair is not renamed.
        token = self.token_service.get(name, grammar_id)
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # The loaded pair is not a duplicate of itself.
        if (new_name, grammar_id) != (token.name, token.grammar_id):
            self.verify(
                not self.token_service.exists(new_name, grammar_id),
                a.error.TOKEN_ALREADY_EXISTS_ID,
                message=f'Token already exists: {new_name} in grammar {grammar_id}.',
                name=new_name,
                grammar_id=grammar_id,
            )

        # Rename, persist, and return the same aggregate.
        token.rename(new_name)
        self.token_service.save(token)
        return token

# ** event: reassign_token_grammar
class ReassignTokenGrammar(TokenEvent):
    '''
    Move a token to another grammar id without requiring that grammar to exist.

    Reassigning to the loaded grammar is the same pair and is not a duplicate.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'new_grammar_id'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            new_grammar_id: str,
            **kwargs,
        ) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Reassign a stored token to another grammar id and save it.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that currently owns the token.
        :type grammar_id: str
        :param new_grammar_id: The destination grammar id.
        :type new_grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # A missing pair is not moved.
        token = self.token_service.get(name, grammar_id)
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # The loaded pair is not a duplicate of itself.
        if (name, new_grammar_id) != (token.name, token.grammar_id):
            self.verify(
                not self.token_service.exists(name, new_grammar_id),
                a.error.TOKEN_ALREADY_EXISTS_ID,
                message=f'Token already exists: {name} in grammar {new_grammar_id}.',
                name=name,
                grammar_id=new_grammar_id,
            )

        # Reassign, persist, and return the same aggregate.
        token.reassign_grammar(new_grammar_id)
        self.token_service.save(token)
        return token

# ** event: set_token_pattern
class SetTokenPattern(TokenEvent):
    '''
    Replace the pattern of a stored token.

    The new pattern is stored as text. It is not checked as a regex.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'pattern'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            pattern: str,
            **kwargs,
        ) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Replace a stored token pattern and save it.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :param pattern: The replacement pattern.
        :type pattern: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # A missing pair is not updated.
        token = self.token_service.get(name, grammar_id)
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Replace the pattern, persist, and return the same aggregate.
        token.set_pattern(pattern)
        self.token_service.save(token)
        return token

# ** event: set_token_action
class SetTokenAction(TokenEvent):
    '''
    Replace the action source of a complex token.

    A simple token has no action, so the write is refused before save.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'action'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            action: str,
            **kwargs,
        ) -> ComplexTokenRuleAggregate:
        '''
        Replace a complex token action and save it.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :param action: The replacement action source.
        :type action: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved complex token aggregate.
        :rtype: ComplexTokenRuleAggregate
        '''

        # A missing pair is not updated.
        token = self.token_service.get(name, grammar_id)
        self.verify(
            token is not None,
            a.error.TOKEN_NOT_FOUND_ID,
            message=f'Token not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # A simple token cannot take an action.
        self.verify(
            isinstance(token, ComplexTokenRuleAggregate),
            a.error.TOKEN_ACTION_NOT_SUPPORTED_ID,
            message=f'Token action is not supported for simple token {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Replace the action, persist, and return the same aggregate.
        token.set_action(action)
        self.token_service.save(token)
        return token

# ** event: remove_token
class RemoveToken(TokenEvent):
    '''
    Delete a token pair and return that pair.

    Absence is not an error. The delete is still requested.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(self, name: str, grammar_id: str, **kwargs) -> tuple[str, str]:
        '''
        Delete a token pair whether or not it is stored.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The deleted name and grammar pair.
        :rtype: tuple[str, str]
        '''

        # Absence is an idempotent delete, not a not-found failure.
        self.token_service.delete(name, grammar_id)

        # Return the pair. Do not return None.
        return (name, grammar_id)
