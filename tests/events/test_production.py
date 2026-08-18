"""Tests for Tiferet-Ly Production Domain Events"""

# *** imports

# ** core
from inspect import signature
from unittest.mock import Mock

# ** infra
import pytest

# ** app
from tiferet.assets.core import TiferetError
from tiferet.events.core import DomainEvent
from tiferet_ly import assets as a
from tiferet_ly.events.production import (
    AddProduction,
    GetProductions,
    ListProductions,
    ProductionEvent,
    ReassignProductionGrammar,
    RemoveProduction,
    RenameProduction,
    SetProductionAction,
    SetProductionSpec,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)

# *** functions

# ** function: simple_production
def simple_production(
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
    :return: The constructed simple production.
    :rtype: SimpleProductionRuleAggregate
    '''

    # Construct a simple production under the given grammar.
    return SimpleProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )


# ** function: complex_production
def complex_production(
        name: str = 'expression',
        grammar_id: str = 'arithmetic',
        spec: str = 'expression : expression PLUS term',
        action: str = 'p[0] = p[1] + p[3]') -> ComplexProductionRuleAggregate:
    '''
    Construct a complex production aggregate for event tests.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :param action: The encoded action source.
    :type action: str
    :return: The constructed complex production.
    :rtype: ComplexProductionRuleAggregate
    '''

    # Construct a complex production under the given grammar.
    return ComplexProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
        action=action,
    )


# ** function: grammar
def grammar(
        id: str,
        parent_ids=None,
        start: str = 'expression') -> GrammarAggregate:
    '''
    Construct a grammar aggregate for start-check tests.

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


# ** function: production_service
def production_service(productions=None) -> Mock:
    '''
    Build a mocked ProductionService whose list returns the given catalogue.

    :param productions: Optional catalogue returned by list().
    :type productions: list | None
    :return: The mocked production service.
    :rtype: Mock
    '''

    # Construct a mock service whose list returns the supplied catalogue.
    service = Mock()
    service.list.return_value = list(productions or [])
    return service


# ** function: grammar_service
def grammar_service(grammars=None) -> Mock:
    '''
    Build a mocked GrammarService whose list returns the given catalogue.

    :param grammars: Optional catalogue returned by list().
    :type grammars: list | None
    :return: The mocked grammar service.
    :rtype: Mock
    '''

    # Construct a mock service whose list returns the supplied catalogue.
    service = Mock()
    service.list.return_value = list(grammars or [])
    return service


# *** tests

# ** test: production_event_injects_production_service
def test_production_event_injects_production_service() -> None:
    '''
    Test that ProductionEvent holds the injected ProductionService.
    '''

    # Construct the base event with a mock service.
    service = production_service()
    event = ProductionEvent(service)

    # Assert the service is stored on the base event.
    assert event.production_service is service


# ** test: add_production_appends_new_spec
def test_add_production_appends_new_spec() -> None:
    '''
    Test that AddProduction of a new spec under an existing name succeeds.
    '''

    # Handle AddProduction against a catalogue that already has another spec.
    existing = simple_production(spec='expression : term')
    service = production_service([existing])
    production = DomainEvent.handle(
        AddProduction,
        dependencies={'production_service': service},
        name='expression',
        grammar_id='arithmetic',
        spec='expression : expression PLUS term',
        action='p[0] = p[1] + p[3]',
    )

    # Assert the new alternative is constructed and saved.
    assert isinstance(production, ComplexProductionRuleAggregate)
    assert production.spec == 'expression : expression PLUS term'
    service.save.assert_called_once()


# ** test: add_production_duplicate_triple_raises
def test_add_production_duplicate_triple_raises() -> None:
    '''
    Test that AddProduction of an identical triple raises.
    '''

    # Handle AddProduction against a catalogue that already has this triple.
    existing = simple_production()
    service = production_service([existing])

    # Assert the already-exists error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddProduction,
            dependencies={'production_service': service},
            name='expression',
            grammar_id='arithmetic',
            spec='expression : term',
        )
    assert raised.value.error_code == a.error.PRODUCTION_ALREADY_EXISTS_ID
    service.save.assert_not_called()


# ** test: add_production_missing_grammar_does_not_inject_grammar_service
def test_add_production_missing_grammar_does_not_inject_grammar_service() -> None:
    '''
    Test that AddProduction does not take GrammarService and still succeeds.
    '''

    # Handle AddProduction with only the production service injected.
    service = production_service()
    production = DomainEvent.handle(
        AddProduction,
        dependencies={'production_service': service},
        name='expression',
        grammar_id='missing',
        spec='expression : term',
    )

    # Assert the constructor has no grammar_service and the write succeeded.
    assert 'grammar_service' not in signature(AddProduction.__init__).parameters
    assert production.grammar_id == 'missing'
    service.save.assert_called_once()


# ** test: get_productions_returns_every_match_in_order
def test_get_productions_returns_every_match_in_order() -> None:
    '''
    Test that GetProductions returns every matching alternative in order.
    '''

    # Handle GetProductions against a mixed catalogue.
    first = simple_production(spec='expression : term')
    other = simple_production(name='term', spec='term : NUMBER')
    second = complex_production()
    service = production_service([first, other, second])
    result = DomainEvent.handle(
        GetProductions,
        dependencies={'production_service': service},
        name='expression',
        grammar_id='arithmetic',
    )

    # Assert only the expression alternatives survive, in declared order.
    assert result == [first, second]


# ** test: get_productions_raises_when_empty
def test_get_productions_raises_when_empty() -> None:
    '''
    Test that GetProductions raises when no alternative matches.
    '''

    # Handle GetProductions against an empty catalogue.
    service = production_service()

    # Assert the not-found error.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            GetProductions,
            dependencies={'production_service': service},
            name='expression',
            grammar_id='arithmetic',
        )
    assert raised.value.error_code == a.error.PRODUCTION_NOT_FOUND_ID


# ** test: list_productions_returns_unfiltered_catalogue
def test_list_productions_returns_unfiltered_catalogue() -> None:
    '''
    Test that ListProductions returns the service list unchanged.
    '''

    # Handle ListProductions against a preloaded catalogue.
    productions = [simple_production(), complex_production()]
    service = production_service(productions)
    result = DomainEvent.handle(
        ListProductions,
        dependencies={'production_service': service},
    )

    # Assert the catalogue is returned as-is.
    assert result == productions


# ** test: set_production_spec_missing_raises
def test_set_production_spec_missing_raises() -> None:
    '''
    Test that SetProductionSpec against an unknown spec raises.
    '''

    # Handle SetProductionSpec against a catalogue that lacks the triple.
    service = production_service([simple_production()])

    # Assert the not-found error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            SetProductionSpec,
            dependencies={'production_service': service},
            name='expression',
            grammar_id='arithmetic',
            spec='expression : missing',
            new_spec='expression : NUMBER',
        )
    assert raised.value.error_code == a.error.PRODUCTION_NOT_FOUND_ID
    service.save.assert_not_called()


# ** test: set_production_spec_affects_only_matching_row
def test_set_production_spec_affects_only_matching_row() -> None:
    '''
    Test that SetProductionSpec updates only the matching triple.
    '''

    # Handle SetProductionSpec against two alternatives of the same name.
    first = simple_production(spec='expression : term')
    second = complex_production()
    service = production_service([first, second])
    result = DomainEvent.handle(
        SetProductionSpec,
        dependencies={'production_service': service},
        name='expression',
        grammar_id='arithmetic',
        spec='expression : term',
        new_spec='expression : NUMBER',
    )

    # Assert only the targeted row changed and was saved.
    assert result is first
    assert first.spec == 'expression : NUMBER'
    assert second.spec == 'expression : expression PLUS term'
    service.save.assert_called_once_with(first)


# ** test: set_production_action_on_simple_raises
def test_set_production_action_on_simple_raises() -> None:
    '''
    Test that SetProductionAction on a Simple aggregate raises and does not save.
    '''

    # Handle SetProductionAction against a simple production.
    service = production_service([simple_production()])

    # Assert the action-not-supported error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            SetProductionAction,
            dependencies={'production_service': service},
            name='expression',
            grammar_id='arithmetic',
            spec='expression : term',
            action='p[0] = p[1]',
        )
    assert raised.value.error_code == a.error.PRODUCTION_ACTION_NOT_SUPPORTED_ID
    service.save.assert_not_called()


# ** test: remove_production_missing_raises
def test_remove_production_missing_raises() -> None:
    '''
    Test that RemoveProduction against an unknown spec raises.
    '''

    # Handle RemoveProduction against a catalogue that lacks the triple.
    productions = production_service([simple_production()])
    grammars = grammar_service()

    # Assert the not-found error and that delete is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RemoveProduction,
            dependencies={
                'production_service': productions,
                'grammar_service': grammars,
            },
            name='expression',
            grammar_id='arithmetic',
            spec='expression : missing',
        )
    assert raised.value.error_code == a.error.PRODUCTION_NOT_FOUND_ID
    productions.delete.assert_not_called()


# ** test: remove_production_last_start_including_ancestor_raises
def test_remove_production_last_start_including_ancestor_raises() -> None:
    '''
    Test that deleting the last start production, including a dialect's
    inherited start, raises and does not delete.
    '''

    # Delete arithmetic.comment while dialect comments inherits that start.
    root = grammar('arithmetic')
    dialect = grammar('comments', ['arithmetic'], start='comment')
    start = simple_production()
    inherited = simple_production(name='comment', spec='comment : HASH text')
    productions = production_service([start, inherited])
    grammars = grammar_service([root, dialect])

    # Assert the start error names the dialect and delete is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RemoveProduction,
            dependencies={
                'production_service': productions,
                'grammar_service': grammars,
            },
            name='comment',
            grammar_id='arithmetic',
            spec='comment : HASH text',
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    assert raised.value.kwargs['id'] == 'comments'
    productions.delete.assert_not_called()


# ** test: remove_production_succeeds_when_another_alternative_remains
def test_remove_production_succeeds_when_another_alternative_remains() -> None:
    '''
    Test that RemoveProduction succeeds when another start alternative remains.
    '''

    # Delete one expression alternative while another remains.
    root = grammar('arithmetic')
    first = simple_production(spec='expression : term')
    second = complex_production()
    productions = production_service([first, second])
    grammars = grammar_service([root])
    result = DomainEvent.handle(
        RemoveProduction,
        dependencies={
            'production_service': productions,
            'grammar_service': grammars,
        },
        name='expression',
        grammar_id='arithmetic',
        spec='expression : term',
    )

    # Assert the identity is returned and delete was called.
    assert result == ('expression', 'arithmetic', 'expression : term')
    productions.delete.assert_called_once_with('expression', 'arithmetic')


# ** test: remove_production_succeeds_when_no_start_depends
def test_remove_production_succeeds_when_no_start_depends() -> None:
    '''
    Test that RemoveProduction succeeds when no persisted start depends on it.
    '''

    # Delete a term production while start remains expression.
    root = grammar('arithmetic')
    start = simple_production()
    unused = simple_production(name='term', spec='term : NUMBER')
    productions = production_service([start, unused])
    grammars = grammar_service([root])
    result = DomainEvent.handle(
        RemoveProduction,
        dependencies={
            'production_service': productions,
            'grammar_service': grammars,
        },
        name='term',
        grammar_id='arithmetic',
        spec='term : NUMBER',
    )

    # Assert the unused row can be deleted.
    assert result == ('term', 'arithmetic', 'term : NUMBER')
    productions.delete.assert_called_once()


# ** test: rename_production_that_breaks_start_raises
def test_rename_production_that_breaks_start_raises() -> None:
    '''
    Test that RenameProduction that would leave start unresolved raises.
    '''

    # Rename the only expression production away from the start name.
    root = grammar('arithmetic')
    production = simple_production()
    productions = production_service([production])
    grammars = grammar_service([root])

    # Assert the start error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            RenameProduction,
            dependencies={
                'production_service': productions,
                'grammar_service': grammars,
            },
            name='expression',
            grammar_id='arithmetic',
            spec='expression : term',
            new_name='expr',
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    productions.save.assert_not_called()


# ** test: reassign_production_grammar_that_breaks_start_raises
def test_reassign_production_grammar_that_breaks_start_raises() -> None:
    '''
    Test that ReassignProductionGrammar that would leave start unresolved raises.
    '''

    # Move the only start production onto a grammar outside ancestry.
    root = grammar('arithmetic')
    production = simple_production()
    productions = production_service([production])
    grammars = grammar_service([root])

    # Assert the start error and that save is not called.
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            ReassignProductionGrammar,
            dependencies={
                'production_service': productions,
                'grammar_service': grammars,
            },
            name='expression',
            grammar_id='arithmetic',
            spec='expression : term',
            new_grammar_id='other',
        )
    assert raised.value.error_code == a.error.GRAMMAR_START_NOT_FOUND_ID
    productions.save.assert_not_called()
