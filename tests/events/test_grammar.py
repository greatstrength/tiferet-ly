"""Tests for Tiferet-Ly Grammar Domain Events"""

# *** imports

# ** core
from unittest.mock import Mock

# ** infra
import pytest

# ** app
from tiferet.assets.core import TiferetError
from tiferet.events.core import DomainEvent
from tiferet_ly import assets as a
from tiferet_ly.events.grammar import (
    AddGrammar,
    GetGrammar,
    GrammarEvent,
    ListGrammars,
    RemoveGrammar,
    SetGrammarParentIds,
    SetGrammarStart,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import SimpleProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate

# *** functions

# ** function: grammar
def grammar(
        id: str,
        parent_ids=None,
        start: str = 'expression') -> GrammarAggregate:
    '''
    Construct a grammar aggregate for event tests.

    :param id: The grammar id.
    :type id: str
    :param parent_ids: Optional ordered parent ids.
    :type parent_ids: list | None
    :param start: The start symbol.
    :type start: str
    :return: The constructed grammar.
    :rtype: GrammarAggregate
    '''

    # Construct a lean grammar with the given composition.
    return GrammarAggregate(
        id=id,
        parent_ids=list(parent_ids or []),
        start=start,
    )


# ** function: production
def production(
        name: str = 'expression',
        grammar_id: str = 'arithmetic',
        spec: str = 'expression : term') -> SimpleProductionRuleAggregate:
    '''
    Construct a simple production aggregate for event tests.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :return: The constructed production.
    :rtype: SimpleProductionRuleAggregate
    '''

    # Construct a simple production under the given grammar.
    return SimpleProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )


# ** function: token
def token(
        name: str = 'PLUS',
        grammar_id: str = 'arithmetic') -> SimpleTokenRuleAggregate:
    '''
    Construct a simple token aggregate for still-referenced tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The constructed token.
    :rtype: SimpleTokenRuleAggregate
    '''

    # Construct a simple token under the given grammar.
    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=r'\+',
    )


# ** function: grammar_service
def grammar_service(grammars=None, exists=None) -> Mock:
    '''
    Build a mocked GrammarService.

    :param grammars: Optional catalogue returned by list() and get().
    :type grammars: list | None
    :param exists: Optional exists() return value; defaults to membership.
    :type exists: bool | None
    :return: The mocked grammar service.
    :rtype: Mock
    '''

    # Index the supplied catalogue by id for get/exists.
    catalogue = list(grammars or [])
    by_id = {item.id: item for item in catalogue}
    service = Mock()
    service.list.return_value = catalogue
    service.get.side_effect = lambda id: by_id.get(id)
    if exists is None:
        service.exists.side_effect = lambda id: id in by_id
    else:
        service.exists.return_value = exists
    return service


# ** function: production_service
def production_service(productions=None) -> Mock:
    '''
    Build a mocked ProductionService.

    :param productions: Optional catalogue returned by list().
    :type productions: list | None
    :return: The mocked production service.
    :rtype: Mock
    '''

    # Construct a mock service whose list returns the supplied catalogue.
    service = Mock()
    service.list.return_value = list(productions or [])
    return service


# ** function: token_service
def token_service(tokens=None) -> Mock:
    '''
    Build a mocked TokenService.

    :param tokens: Optional catalogue returned by list().
    :type tokens: list | None
    :return: The mocked token service.
    :rtype: Mock
    '''

    # Construct a mock service whose list returns the supplied catalogue.
    service = Mock()
    service.list.return_value = list(tokens or [])
    return service


# *** tests

# ** test: grammar_event_injects_grammar_service
def test_grammar_event_injects_grammar_service() -> None:
    '''
    Test that GrammarEvent holds the injected GrammarService.
    '''

    # Construct the base event with a mock service.
    service = grammar_service()
    event = GrammarEvent(service)

    # Assert the service is stored on the base event.
    assert event.grammar_service is service


# ** test: add_grammar_missing_parent_raises
def test_add_grammar_missing_parent_raises() -> None:
    '''
    Test that AddGrammar with a missing parent_ids entry raises and does not save.
    '''

    # Handle AddGrammar whose only parent is not persisted.
    grammars = grammar_service()
    productions = production_service([production()])

    # Assert the parent-not-found error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='comments',
            start='expression',
            parent_ids=['missing'],
        )
    assert raised.value.error_code == a.error.GRAMMAR_PARENT_NOT_FOUND_ID
    assert raised.value.kwargs['parent_id'] == 'missing'
    grammars.save.assert_not_called()


# ** test: add_grammar_direct_cycle_raises
def test_add_grammar_direct_cycle_raises() -> None:
    '''
    Test that AddGrammar with a direct self-reference raises and does not save.
    '''

    # Handle AddGrammar that lists itself as a parent.
    grammars = grammar_service()
    productions = production_service([production(grammar_id='loop')])

    # Assert the cycle error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='loop',
            start='expression',
            parent_ids=['loop'],
        )
    assert raised.value.error_code == a.error.GRAMMAR_CYCLE_DETECTED_ID
    grammars.save.assert_not_called()


# ** test: add_grammar_transitive_cycle_raises
def test_add_grammar_transitive_cycle_raises() -> None:
    '''
    Test that AddGrammar with a transitive cycle raises and does not save.
    '''

    # Persist B -> C and try to add A -> B when C already points at A.
    # Equivalent: adding A with parent B, where B's ancestor already lists A.
    child = grammar('B', ['A'])
    grammars = grammar_service([child])
    productions = production_service([production(grammar_id='A')])

    # Assert the cycle error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='A',
            start='expression',
            parent_ids=['B'],
        )
    assert raised.value.error_code == a.error.GRAMMAR_CYCLE_DETECTED_ID
    grammars.save.assert_not_called()


# ** test: add_grammar_start_not_found_raises
def test_add_grammar_start_not_found_raises() -> None:
    '''
    Test that AddGrammar whose start is not in select_productions raises.
    '''

    # Handle AddGrammar with no productions in the catalogue.
    grammars = grammar_service()
    productions = production_service()

    # Assert the start error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='arithmetic',
            start='expression',
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    grammars.save.assert_not_called()


# ** test: add_grammar_succeeds_with_own_production
def test_add_grammar_succeeds_with_own_production() -> None:
    '''
    Test that AddGrammar succeeds when a production already exists under it.
    '''

    # Handle AddGrammar after a productions-first write.
    grammars = grammar_service()
    productions = production_service([production()])
    result = DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammars,
            'production_service': productions,
        },
        id='arithmetic',
        start='expression',
    )

    # Assert the grammar is saved with the declared start.
    assert result.id == 'arithmetic'
    assert result.start == 'expression'
    grammars.save.assert_called_once()


# ** test: add_grammar_succeeds_with_ancestor_production
def test_add_grammar_succeeds_with_ancestor_production() -> None:
    '''
    Test that AddGrammar succeeds when an ancestor supplies the start.
    '''

    # Handle AddGrammar for a dialect with no own productions.
    root = grammar('arithmetic')
    grammars = grammar_service([root])
    productions = production_service([production()])
    result = DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammars,
            'production_service': productions,
        },
        id='comments',
        start='expression',
        parent_ids=['arithmetic'],
    )

    # Assert the dialect is saved and inherits start from the ancestor.
    assert result.id == 'comments'
    assert result.parent_ids == ['arithmetic']
    grammars.save.assert_called_once()


# ** test: get_grammar_raises_when_missing
def test_get_grammar_raises_when_missing() -> None:
    '''
    Test that GetGrammar raises GRAMMAR_NOT_FOUND_ID when get returns None.
    '''

    # Handle GetGrammar against an empty service.
    grammars = grammar_service()

    # Assert the not-found error.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            GetGrammar,
            dependencies={'grammar_service': grammars},
            id='missing',
        )
    assert raised.value.error_code == a.error.GRAMMAR_NOT_FOUND_ID


# ** test: list_grammars_returns_unfiltered_catalogue
def test_list_grammars_returns_unfiltered_catalogue() -> None:
    '''
    Test that ListGrammars returns the service list unchanged.
    '''

    # Handle ListGrammars against a preloaded catalogue.
    catalogue = [grammar('arithmetic'), grammar('algebra')]
    grammars = grammar_service(catalogue)
    result = DomainEvent.handle(
        ListGrammars,
        dependencies={'grammar_service': grammars},
    )

    # Assert the catalogue is returned as-is.
    assert result == catalogue


# ** test: set_grammar_start_unresolved_raises
def test_set_grammar_start_unresolved_raises() -> None:
    '''
    Test that SetGrammarStart to a name not in the effective set raises.
    '''

    # Handle SetGrammarStart toward a name no production declares.
    root = grammar('arithmetic')
    grammars = grammar_service([root])
    productions = production_service([production()])

    # Assert the start error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            SetGrammarStart,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='arithmetic',
            start='missing',
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    grammars.save.assert_not_called()


# ** test: set_grammar_parent_ids_dropping_start_raises
def test_set_grammar_parent_ids_dropping_start_raises() -> None:
    '''
    Test that SetGrammarParentIds that would drop start raises and does not save.
    '''

    # Dialect currently inherits expression from arithmetic; drop that parent.
    root = grammar('arithmetic')
    dialect = grammar('comments', ['arithmetic'])
    grammars = grammar_service([root, dialect])
    productions = production_service([production()])

    # Assert the start error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            SetGrammarParentIds,
            dependencies={
                'grammar_service': grammars,
                'production_service': productions,
            },
            id='comments',
            parent_ids=[],
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    grammars.save.assert_not_called()


# ** test: remove_grammar_still_listed_as_parent_raises
def test_remove_grammar_still_listed_as_parent_raises() -> None:
    '''
    Test that RemoveGrammar of a still-listed parent raises and does not delete.
    '''

    # Arithmetic is still listed in the dialect's parent_ids.
    root = grammar('arithmetic')
    dialect = grammar('comments', ['arithmetic'])
    grammars = grammar_service([root, dialect])

    # Assert the still-referenced error and that delete is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RemoveGrammar,
            dependencies={
                'grammar_service': grammars,
                'token_service': token_service(),
                'production_service': production_service(),
            },
            id='arithmetic',
        )
    assert raised.value.error_code == a.error.GRAMMAR_STILL_REFERENCED_ID
    grammars.delete.assert_not_called()


# ** test: remove_grammar_still_referenced_by_token_raises
def test_remove_grammar_still_referenced_by_token_raises() -> None:
    '''
    Test that RemoveGrammar of a grammar still owning a token raises.
    '''

    # A token is still declared under arithmetic.
    root = grammar('arithmetic')
    grammars = grammar_service([root])

    # Assert the still-referenced error and that delete is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RemoveGrammar,
            dependencies={
                'grammar_service': grammars,
                'token_service': token_service([token()]),
                'production_service': production_service(),
            },
            id='arithmetic',
        )
    assert raised.value.error_code == a.error.GRAMMAR_STILL_REFERENCED_ID
    grammars.delete.assert_not_called()


# ** test: remove_grammar_still_referenced_by_production_raises
def test_remove_grammar_still_referenced_by_production_raises() -> None:
    '''
    Test that RemoveGrammar of a grammar still owning a production raises.
    '''

    # A production is still declared under arithmetic.
    root = grammar('arithmetic')
    grammars = grammar_service([root])

    # Assert the still-referenced error and that delete is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RemoveGrammar,
            dependencies={
                'grammar_service': grammars,
                'token_service': token_service(),
                'production_service': production_service([production()]),
            },
            id='arithmetic',
        )
    assert raised.value.error_code == a.error.GRAMMAR_STILL_REFERENCED_ID
    grammars.delete.assert_not_called()


# ** test: remove_grammar_unreferenced_returns_id
def test_remove_grammar_unreferenced_returns_id() -> None:
    '''
    Test that RemoveGrammar of an unreferenced grammar deletes and returns id.
    '''

    # Handle RemoveGrammar with no remaining references.
    root = grammar('arithmetic')
    grammars = grammar_service([root])
    result = DomainEvent.handle(
        RemoveGrammar,
        dependencies={
            'grammar_service': grammars,
            'token_service': token_service(),
            'production_service': production_service(),
        },
        id='arithmetic',
    )

    # Assert the identity is returned and delete was called.
    assert result == 'arithmetic'
    grammars.delete.assert_called_once_with('arithmetic')


# ** test: event_modules_do_not_import_repos_or_ply
def test_event_modules_do_not_import_repos_or_ply() -> None:
    '''
    Test that event modules do not import repos or ply.
    '''

    # Import the event package modules under test.
    from tiferet_ly.events import grammar as grammar_events
    from tiferet_ly.events import production as production_events
    from tiferet_ly.events import token as token_events

    # Assert no event module imported repos or ply.
    for module in (token_events, production_events, grammar_events):
        assert 'ply' not in module.__dict__
        assert not any(name.startswith('tiferet_ly.repos') for name in module.__dict__)


# ** test: shrinking_writers_import_grammar_rule_selector
def test_shrinking_writers_import_grammar_rule_selector() -> None:
    '''
    Test that grammar writers and shrinking production writers import the selector.
    '''

    # Import the modules that must call GrammarRuleSelector statically.
    from tiferet_ly.events import grammar as grammar_events
    from tiferet_ly.events import production as production_events
    from tiferet_ly.utils.grammar import GrammarRuleSelector

    # Assert both modules bind the RFP-004 utility.
    assert production_events.GrammarRuleSelector is GrammarRuleSelector
    assert grammar_events.GrammarRuleSelector is GrammarRuleSelector
