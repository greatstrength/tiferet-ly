"""Tests for Tiferet-Ly Token Domain Events"""

# *** imports

# ** core
from unittest.mock import Mock

# ** infra
import pytest

# ** app
from tiferet.assets.core import TiferetError
from tiferet.events.core import DomainEvent
from tiferet_ly import assets as a
from tiferet_ly.events.token import (
    AddToken,
    GetToken,
    ListTokens,
    ReassignTokenGrammar,
    RemoveToken,
    RenameToken,
    SetTokenAction,
    SetTokenPattern,
    TokenEvent,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)

# *** functions

# ** function: simple_token
def simple_token(
        name: str = 'PLUS',
        grammar_id: str = 'arithmetic',
        pattern: str = r'\+') -> SimpleTokenRuleAggregate:
    '''
    Construct a simple token aggregate for event tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :return: The constructed simple token.
    :rtype: SimpleTokenRuleAggregate
    '''

    # Construct a simple token under the given grammar.
    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
    )


# ** function: complex_token
def complex_token(
        name: str = 'NUMBER',
        grammar_id: str = 'arithmetic',
        pattern: str = r'\d+',
        action: str = 't.value = int(t.value)') -> ComplexTokenRuleAggregate:
    '''
    Construct a complex token aggregate for event tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :param action: The encoded action source.
    :type action: str
    :return: The constructed complex token.
    :rtype: ComplexTokenRuleAggregate
    '''

    # Construct a complex token under the given grammar.
    return ComplexTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
        action=action,
    )


# ** function: token_service
def token_service(**attrs) -> Mock:
    '''
    Build a mocked TokenService with optional preconfigured behavior.

    :param attrs: Attributes assigned onto the mock.
    :type attrs: dict
    :return: The mocked token service.
    :rtype: Mock
    '''

    # Construct a mock service and apply any preconfigured attributes.
    service = Mock()
    service.configure_mock(**attrs)
    return service


# *** tests

# ** test: token_event_injects_token_service
def test_token_event_injects_token_service() -> None:
    '''
    Test that TokenEvent holds the injected TokenService.
    '''

    # Construct the base event with a mock service.
    service = token_service()
    event = TokenEvent(service)

    # Assert the service is stored on the base event.
    assert event.token_service is service


# ** test: add_token_duplicate_raises
def test_add_token_duplicate_raises() -> None:
    '''
    Test that AddToken of a duplicate (name, grammar_id) raises.
    '''

    # Handle AddToken against a service that already has the pair.
    service = token_service(exists=Mock(return_value=True))

    # Assert the already-exists error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddToken,
            dependencies={'token_service': service},
            name='PLUS',
            grammar_id='arithmetic',
            pattern=r'\+',
        )
    assert raised.value.error_code == a.error.TOKEN_ALREADY_EXISTS_ID
    service.save.assert_not_called()


# ** test: add_token_missing_grammar_does_not_raise
def test_add_token_missing_grammar_does_not_raise() -> None:
    '''
    Test that AddToken of a grammar_id that does not exist still succeeds.
    '''

    # Handle AddToken without consulting GrammarService at all.
    service = token_service(exists=Mock(return_value=False))
    token = DomainEvent.handle(
        AddToken,
        dependencies={'token_service': service},
        name='PLUS',
        grammar_id='missing',
        pattern=r'\+',
    )

    # Assert a simple token is saved under the missing grammar.
    assert isinstance(token, SimpleTokenRuleAggregate)
    assert token.grammar_id == 'missing'
    service.save.assert_called_once()


# ** test: add_token_with_action_is_complex
def test_add_token_with_action_is_complex() -> None:
    '''
    Test that AddToken with an action constructs a complex aggregate.
    '''

    # Handle AddToken with an action body.
    service = token_service(exists=Mock(return_value=False))
    token = DomainEvent.handle(
        AddToken,
        dependencies={'token_service': service},
        name='NUMBER',
        grammar_id='arithmetic',
        pattern=r'\d+',
        action='t.value = int(t.value)',
    )

    # Assert the constructed aggregate is complex.
    assert isinstance(token, ComplexTokenRuleAggregate)
    assert token.action == 't.value = int(t.value)'


# ** test: get_token_raises_when_missing
def test_get_token_raises_when_missing() -> None:
    '''
    Test that GetToken raises TOKEN_NOT_FOUND_ID when get returns None.
    '''

    # Handle GetToken against an empty service.
    service = token_service(get=Mock(return_value=None))

    # Assert the not-found error.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            GetToken,
            dependencies={'token_service': service},
            name='PLUS',
            grammar_id='arithmetic',
        )
    assert raised.value.error_code == a.error.TOKEN_NOT_FOUND_ID


# ** test: list_tokens_returns_unfiltered_catalogue
def test_list_tokens_returns_unfiltered_catalogue() -> None:
    '''
    Test that ListTokens returns the service list unchanged.
    '''

    # Handle ListTokens against a preloaded catalogue.
    tokens = [simple_token(), simple_token(name='MINUS', pattern=r'-')]
    service = token_service(list=Mock(return_value=tokens))
    result = DomainEvent.handle(
        ListTokens,
        dependencies={'token_service': service},
    )

    # Assert the catalogue is returned as-is.
    assert result == tokens


# ** test: rename_token_rejects_existing_pair
def test_rename_token_rejects_existing_pair() -> None:
    '''
    Test that RenameToken refuses a destination pair that already exists.
    '''

    # Handle RenameToken toward a pair the service already has.
    service = token_service(
        get=Mock(return_value=simple_token()),
        exists=Mock(return_value=True),
    )

    # Assert the already-exists error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RenameToken,
            dependencies={'token_service': service},
            name='PLUS',
            grammar_id='arithmetic',
            new_name='ADD',
        )
    assert raised.value.error_code == a.error.TOKEN_ALREADY_EXISTS_ID
    service.save.assert_not_called()


# ** test: reassign_token_grammar_rejects_existing_pair
def test_reassign_token_grammar_rejects_existing_pair() -> None:
    '''
    Test that ReassignTokenGrammar refuses a destination pair that exists.
    '''

    # Handle ReassignTokenGrammar toward a pair the service already has.
    service = token_service(
        get=Mock(return_value=simple_token()),
        exists=Mock(return_value=True),
    )

    # Assert the already-exists error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            ReassignTokenGrammar,
            dependencies={'token_service': service},
            name='PLUS',
            grammar_id='arithmetic',
            new_grammar_id='algebra',
        )
    assert raised.value.error_code == a.error.TOKEN_ALREADY_EXISTS_ID
    service.save.assert_not_called()


# ** test: set_token_pattern_updates_and_saves
def test_set_token_pattern_updates_and_saves() -> None:
    '''
    Test that SetTokenPattern applies the mutator and saves.
    '''

    # Handle SetTokenPattern against an existing simple token.
    token = simple_token()
    service = token_service(get=Mock(return_value=token))
    result = DomainEvent.handle(
        SetTokenPattern,
        dependencies={'token_service': service},
        name='PLUS',
        grammar_id='arithmetic',
        pattern=r'\+\+',
    )

    # Assert the pattern changed and the token was saved.
    assert result.pattern == r'\+\+'
    service.save.assert_called_once_with(token)


# ** test: set_token_action_on_simple_raises
def test_set_token_action_on_simple_raises() -> None:
    '''
    Test that SetTokenAction on a Simple aggregate raises and does not save.
    '''

    # Handle SetTokenAction against a simple token.
    service = token_service(get=Mock(return_value=simple_token()))

    # Assert the action-not-supported error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            SetTokenAction,
            dependencies={'token_service': service},
            name='PLUS',
            grammar_id='arithmetic',
            action='t.value = t.value',
        )
    assert raised.value.error_code == a.error.TOKEN_ACTION_NOT_SUPPORTED_ID
    service.save.assert_not_called()


# ** test: set_token_action_on_complex_saves
def test_set_token_action_on_complex_saves() -> None:
    '''
    Test that SetTokenAction on a Complex aggregate updates and saves.
    '''

    # Handle SetTokenAction against a complex token.
    token = complex_token()
    service = token_service(get=Mock(return_value=token))
    result = DomainEvent.handle(
        SetTokenAction,
        dependencies={'token_service': service},
        name='NUMBER',
        grammar_id='arithmetic',
        action='t.value = float(t.value)',
    )

    # Assert the action changed and the token was saved.
    assert result.action == 't.value = float(t.value)'
    service.save.assert_called_once_with(token)


# ** test: remove_token_returns_identity
def test_remove_token_returns_identity() -> None:
    '''
    Test that RemoveToken deletes and returns the given identity.
    '''

    # Handle RemoveToken against a mock service.
    service = token_service()
    result = DomainEvent.handle(
        RemoveToken,
        dependencies={'token_service': service},
        name='PLUS',
        grammar_id='arithmetic',
    )

    # Assert the identity is returned and delete was called.
    assert result == ('PLUS', 'arithmetic')
    service.delete.assert_called_once_with('PLUS', 'arithmetic')
