"""Tiferet Ly Grammar Removal Event Tests"""

# *** imports

# ** core
import ast
import inspect
from unittest.mock import Mock, patch

# ** infra
import pytest

# ** app
import tiferet_ly.events as events_package
from tiferet import DomainEvent, TiferetError
from tiferet_ly.assets import grammar as grammar_assets
from tiferet_ly.events.grammar import (
    AddGrammar,
    GrammarEvent,
    RemoveGrammar,
    SetGrammarParentIds,
    SetGrammarStart,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ProductionRuleAggregate
from tiferet_ly.mappers.token import TokenRuleAggregate

# *** functions

# ** function: grammar
def _grammar(
        grammar_id: str,
        parent_ids: list[str],
        start: str = 'expr',
    ) -> GrammarAggregate:
    '''
    Build a lean grammar aggregate.

    :param grammar_id: The grammar identifier.
    :type grammar_id: str
    :param parent_ids: The ordered parent identifiers.
    :type parent_ids: list[str]
    :param start: The declared start name.
    :type start: str
    :return: A grammar aggregate.
    :rtype: GrammarAggregate
    '''

    return GrammarAggregate(
        id=grammar_id,
        parent_ids=parent_ids,
        start=start,
    )

# ** function: token
def _token(name: str, grammar_id: str) -> TokenRuleAggregate:
    '''
    Build a token aggregate from name and grammar membership only.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar identifier.
    :type grammar_id: str
    :return: A token aggregate.
    :rtype: TokenRuleAggregate
    '''

    return TokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
    )

# ** function: production
def _production(name: str, grammar_id: str) -> ProductionRuleAggregate:
    '''
    Build a production aggregate from name and grammar membership only.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar identifier.
    :type grammar_id: str
    :return: A production aggregate.
    :rtype: ProductionRuleAggregate
    '''

    return ProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
    )

# ** function: services
def _services(
        grammars: list[GrammarAggregate] | None = None,
        tokens: list[TokenRuleAggregate] | None = None,
        productions: list[ProductionRuleAggregate] | None = None,
        gotten: GrammarAggregate | None = None,
    ) -> tuple[Mock, Mock, Mock]:
    '''
    Build mocked grammar, token, and production services.

    :param grammars: The catalogue returned by grammar ``list``.
    :type grammars: list[GrammarAggregate] | None
    :param tokens: The catalogue returned by token ``list``.
    :type tokens: list[TokenRuleAggregate] | None
    :param productions: The catalogue returned by production ``list``.
    :type productions: list[ProductionRuleAggregate] | None
    :param gotten: The aggregate returned by grammar ``get``, if any.
    :type gotten: GrammarAggregate | None
    :return: Grammar, token, and production services.
    :rtype: tuple[Mock, Mock, Mock]
    '''

    # Catalogues are in-memory mocks. Nothing opens a file.
    grammar_service = Mock()
    grammar_service.list.return_value = list(grammars or [])
    grammar_service.get.return_value = gotten

    token_service = Mock()
    token_service.list.return_value = list(tokens or [])

    production_service = Mock()
    production_service.list.return_value = list(productions or [])
    return grammar_service, token_service, production_service

# ** function: handle
def _handle(
        grammar_service,
        token_service,
        production_service,
        **kwargs,
    ):
    '''
    Invoke RemoveGrammar through the domain-event handle.

    :param grammar_service: The mocked grammar service.
    :type grammar_service: Mock
    :param token_service: The mocked token service.
    :type token_service: Mock
    :param production_service: The mocked production service.
    :type production_service: Mock
    :param kwargs: Event keyword arguments.
    :type kwargs: dict
    :return: The event result.
    :rtype: str
    '''

    return DomainEvent.handle(
        RemoveGrammar,
        dependencies={
            'grammar_service': grammar_service,
            'token_service': token_service,
            'production_service': production_service,
        },
        **kwargs,
    )

# ** function: assert_still_referenced
def _assert_still_referenced(caught, grammar_service) -> None:
    '''
    Assert the shared reference refusal and that delete was not called.

    :param caught: The raised-error context.
    :type caught: pytest.ExceptionInfo
    :param grammar_service: The mocked grammar service.
    :type grammar_service: Mock
    :return: None
    :rtype: None
    '''

    # One refusal covers parent, token, and production references.
    assert caught.value.error_code == grammar_assets.GRAMMAR_STILL_REFERENCED_ID
    assert caught.value.error_code != grammar_assets.GRAMMAR_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'g'
    grammar_service.delete.assert_not_called()

# *** tests

# ** test: remove_grammar_shape
def test_remove_grammar_shape():
    '''
    Expose RemoveGrammar from its module, not from the events package.
    '''

    # The constructor takes the three services and stores them.
    grammar_service, token_service, production_service = _services()
    event = RemoveGrammar(
        grammar_service,
        token_service,
        production_service,
    )
    assert list(inspect.signature(RemoveGrammar.__init__).parameters) == [
        'self',
        'grammar_service',
        'token_service',
        'production_service',
    ]
    assert event.grammar_service is grammar_service
    assert event.token_service is token_service
    assert event.production_service is production_service

    # Callers import the event module. The package does not re-export it.
    assert RemoveGrammar.__module__ == 'tiferet_ly.events.grammar'
    assert not hasattr(events_package, 'RemoveGrammar')

    # Create and update events remain. This story adds no other event classes.
    assert GrammarEvent._verify_start_resolves
    for event_cls in (AddGrammar, SetGrammarStart, SetGrammarParentIds):
        assert event_cls.__module__ == 'tiferet_ly.events.grammar'
    grammar_tree = ast.parse(inspect.getsource(inspect.getmodule(RemoveGrammar)))
    class_names = {
        node.name
        for node in grammar_tree.body
        if isinstance(node, ast.ClassDef)
    }
    assert class_names == {
        'GrammarEvent',
        'AddGrammar',
        'SetGrammarParentIds',
        'SetGrammarStart',
        'RemoveGrammar',
    }
    assert 'AddToken' not in class_names
    assert 'AddProduction' not in class_names
    assert 'GetGrammar' not in class_names
    assert 'ListGrammars' not in class_names

# ** test: remove_grammar_parent_reference
def test_remove_grammar_parent_reference():
    '''
    Refuse deletion when another grammar lists the id in parent_ids.
    '''

    # The target itself does not count. A different grammar does.
    grammar_service, token_service, production_service = _services(
        grammars=[
            _grammar('g', ['g']),
            _grammar('child', ['g']),
        ],
        gotten=_grammar('g', []),
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            grammar_service,
            token_service,
            production_service,
            id='g',
        )

    _assert_still_referenced(caught, grammar_service)

# ** test: remove_grammar_token_reference_when_absent
def test_remove_grammar_token_reference_when_absent():
    '''
    Refuse deletion when a token still names an absent grammar.
    '''

    # get returns None. The token reference still refuses the write.
    grammar_service, token_service, production_service = _services(
        tokens=[_token('PLUS', 'g')],
        gotten=None,
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            grammar_service,
            token_service,
            production_service,
            id='g',
        )

    _assert_still_referenced(caught, grammar_service)
    assert grammar_service.get.return_value is None

# ** test: remove_grammar_production_reference
def test_remove_grammar_production_reference():
    '''
    Refuse deletion when a production still names the grammar.
    '''

    grammar_service, token_service, production_service = _services(
        productions=[_production('expr', 'g')],
        gotten=_grammar('g', []),
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            grammar_service,
            token_service,
            production_service,
            id='g',
        )

    _assert_still_referenced(caught, grammar_service)

# ** test: remove_grammar_deletes_unreferenced
def test_remove_grammar_deletes_unreferenced():
    '''
    Delete and return a persisted grammar that nothing still names.
    '''

    # Other rules and a self-parent do not count as a foreign reference.
    grammar = _grammar('g', ['g'])
    grammar_service, token_service, production_service = _services(
        grammars=[grammar, _grammar('other', [])],
        tokens=[_token('PLUS', 'other')],
        productions=[_production('expr', 'other')],
        gotten=grammar,
    )

    result = _handle(
        grammar_service,
        token_service,
        production_service,
        id='g',
    )

    # The id is deleted and returned. Nothing is saved.
    assert result == 'g'
    assert result is not None
    grammar_service.delete.assert_called_once_with('g')
    grammar_service.save.assert_not_called()

# ** test: remove_grammar_absent_is_idempotent
def test_remove_grammar_absent_is_idempotent():
    '''
    Delete an absent id when no parent, token, or production names it.
    '''

    grammar_service, token_service, production_service = _services(
        grammars=[_grammar('other', [])],
        tokens=[_token('PLUS', 'other')],
        productions=[_production('expr', 'other')],
        gotten=None,
    )

    result = _handle(
        grammar_service,
        token_service,
        production_service,
        id='g',
    )

    # Absence is not GRAMMAR_NOT_FOUND. The delete is still called.
    assert result == 'g'
    assert grammar_service.get.return_value is None
    grammar_service.delete.assert_called_once_with('g')

# ** test: remove_grammar_blank_id_does_not_delete
def test_remove_grammar_blank_id_does_not_delete():
    '''
    Do not delete when id is missing, blank, or None.
    '''

    grammar_service, token_service, production_service = _services(
        gotten=_grammar('g', []),
    )

    # Each invalid call stops before delete.
    with pytest.raises(TiferetError):
        _handle(
            grammar_service,
            token_service,
            production_service,
        )
    with pytest.raises(TiferetError):
        _handle(
            grammar_service,
            token_service,
            production_service,
            id='   ',
        )
    with pytest.raises(TiferetError):
        _handle(
            grammar_service,
            token_service,
            production_service,
            id='',
        )
    with pytest.raises(TiferetError):
        _handle(
            grammar_service,
            token_service,
            production_service,
            id=None,
        )

    grammar_service.delete.assert_not_called()

# ** test: remove_grammar_ignores_selector
def test_remove_grammar_ignores_selector():
    '''
    Return the id even when selector methods are patched to raise.
    '''

    grammar = _grammar('g', [])
    grammar_service, token_service, production_service = _services(
        grammars=[grammar],
        gotten=grammar,
    )

    # Cycle and start selection are not part of removal.
    with patch(
        'tiferet_ly.events.grammar.GrammarRuleSelector.has_cycle',
        side_effect=AssertionError('has_cycle'),
    ), patch(
        'tiferet_ly.events.grammar.GrammarRuleSelector.select_productions',
        side_effect=AssertionError('select_productions'),
    ), patch(
        'tiferet_ly.utils.grammar.GrammarRuleSelector.has_cycle',
        side_effect=AssertionError('has_cycle'),
    ), patch(
        'tiferet_ly.utils.grammar.GrammarRuleSelector.select_productions',
        side_effect=AssertionError('select_productions'),
    ):
        result = _handle(
            grammar_service,
            token_service,
            production_service,
            id='g',
        )

    assert result == 'g'
    grammar_service.delete.assert_called_once_with('g')
