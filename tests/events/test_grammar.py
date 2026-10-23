"""Tests for Tiferet-Ly Grammar Domain Events"""

# *** imports

# ** core
from pathlib import Path
from unittest.mock import Mock

# ** infra
import pytest
import yaml
from pydantic import ValidationError
from tiferet.assets.core import TiferetError
from tiferet.events.core import DomainEvent, a as tiferet_a

# ** app
from tiferet_ly import assets as a
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.events.grammar import (
    AddGrammar,
    GetGrammar,
    GrammarEvent,
    ListGrammars,
    RemoveGrammar,
    SetGrammarIgnore,
    SetGrammarLayout,
    SetGrammarParentIds,
    SetGrammarStart,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import SimpleProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate
from tiferet_ly.repos.grammar import GrammarConfigRepository

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

# ** function: layout_profile
def layout_profile(indent_token: str = 'INDENT', tab_size: int = 4) -> LayoutProfile:
    '''
    Construct a layout profile for fact-write tests.

    :param indent_token: The synthetic indent token name.
    :type indent_token: str
    :param tab_size: The declared indentation width.
    :type tab_size: int
    :return: The constructed profile.
    :rtype: LayoutProfile
    '''

    # Construct a profile with a block token and the given names and width.
    return LayoutProfile(
        block_tokens=['COLON'],
        indent_token=indent_token,
        dedent_token='DEDENT',
        tab_size=tab_size,
    )

# *** fixtures

# ** fixture: grammar_repo
@pytest.fixture
def grammar_repo(tmp_path: Path) -> GrammarConfigRepository:
    '''
    Build a real GrammarConfigRepository against a temporary YAML file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: The repository under test.
    :rtype: GrammarConfigRepository
    '''

    # Seed an empty YAML document so the loader can open the file.
    config_path = tmp_path / 'grammars.yml'
    config_path.write_text('{}\n', encoding='utf-8')

    # Return the repository pointed at the temp file.
    return GrammarConfigRepository(grammar_config=str(config_path))

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

# ** test: add_grammar_saves_both_facts
def test_add_grammar_saves_both_facts() -> None:
    '''
    Test that AddGrammar with ignore and a layout profile saves both and
    returns an aggregate carrying both.
    '''

    # Handle AddGrammar with both facts.
    grammars = grammar_service()
    profile = layout_profile()
    result = DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammars,
            'production_service': production_service([production()]),
        },
        id='arithmetic',
        start='expression',
        ignore=' \t',
        layout=profile,
    )

    # Assert the saved and returned aggregate carries both facts.
    assert result.ignore == ' \t'
    assert result.layout == profile
    grammars.save.assert_called_once_with(result)

# ** test: add_grammar_without_facts_saves_none
@pytest.mark.parametrize('facts', [
    {},
    {'ignore': None, 'layout': None},
])
def test_add_grammar_without_facts_saves_none(facts) -> None:
    '''
    Test that AddGrammar with the facts omitted, or passed as None, saves
    both as None.
    '''

    # Handle AddGrammar with no facts or explicit None facts.
    grammars = grammar_service()
    result = DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammars,
            'production_service': production_service([production()]),
        },
        id='arithmetic',
        start='expression',
        **facts,
    )

    # Assert both facts are absent on the saved aggregate.
    assert result.ignore is None
    assert result.layout is None
    grammars.save.assert_called_once_with(result)

# ** test: add_grammar_empty_ignore_is_set
def test_add_grammar_empty_ignore_is_set() -> None:
    '''
    Test that AddGrammar with ignore='' stores the empty string, not None.
    '''

    # Handle AddGrammar with an empty skip string.
    grammars = grammar_service()
    result = DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammars,
            'production_service': production_service([production()]),
        },
        id='arithmetic',
        start='expression',
        ignore='',
    )

    # Assert the empty string survives.
    assert result.ignore == ''
    grammars.save.assert_called_once()

# ** test: add_grammar_failed_checks_with_facts_do_not_save
@pytest.mark.parametrize('catalogue, productions, id, parent_ids, error_code', [
    ([], [production()], 'comments', ['missing'], a.error.GRAMMAR_PARENT_NOT_FOUND_ID),
    ([], [production(grammar_id='loop')], 'loop', ['loop'], a.error.GRAMMAR_CYCLE_DETECTED_ID),
    ([], [], 'arithmetic', [], a.error.GRAMMAR_START_NOT_FOUND_ID),
])
def test_add_grammar_failed_checks_with_facts_do_not_save(
        catalogue,
        productions,
        id,
        parent_ids,
        error_code) -> None:
    '''
    Test that AddGrammar still refuses the save on a failed parent, cycle,
    or start check when ignore and layout are supplied.
    '''

    # Handle AddGrammar with both facts and a failing check.
    grammars = grammar_service(catalogue)
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': production_service(productions),
            },
            id=id,
            start='expression',
            parent_ids=parent_ids,
            ignore=' \t',
            layout=layout_profile(),
        )

    # Assert the existing check error and that save is not called.
    assert raised.value.error_code == error_code
    grammars.save.assert_not_called()

# ** test: add_grammar_rejected_fact_does_not_save
@pytest.mark.parametrize('facts', [
    {'ignore': 5},
    {'layout': {'indent_token': 'INDENT', 'dedent_token': 'DEDENT', 'tab_size': 0}},
    {'layout': {'indent_token': 'INDENT', 'dedent_token': 'DEDENT', 'tab_size': -1}},
    {'layout': {'indent_token': 'INDENT', 'dedent_token': 'DEDENT', 'tab_size': False}},
])
def test_add_grammar_rejected_fact_does_not_save(facts) -> None:
    '''
    Test that AddGrammar with a fact the model rejects raises the field's
    ValidationError and does not save.
    '''

    # Handle AddGrammar with a rejected fact.
    grammars = grammar_service()
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            AddGrammar,
            dependencies={
                'grammar_service': grammars,
                'production_service': production_service([production()]),
            },
            id='arithmetic',
            start='expression',
            **facts,
        )

    # Assert nothing was saved.
    grammars.save.assert_not_called()

# ** test: set_grammar_ignore_sets_exact_string
@pytest.mark.parametrize('ignore', [' \t', '[ \t]'])
def test_set_grammar_ignore_sets_exact_string(ignore) -> None:
    '''
    Test that SetGrammarIgnore saves the exact string and leaves layout,
    start, and parent_ids unchanged.
    '''

    # Persist a dialect that already carries a layout profile.
    profile = layout_profile()
    root = grammar('arithmetic')
    dialect = GrammarAggregate(
        id='comments',
        parent_ids=['arithmetic'],
        start='expression',
        layout=profile,
    )
    grammars = grammar_service([root, dialect])
    result = DomainEvent.handle(
        SetGrammarIgnore,
        dependencies={'grammar_service': grammars},
        id='comments',
        ignore=ignore,
    )

    # Assert the exact string is saved and nothing else changed.
    assert result.ignore == ignore
    assert result.layout == profile
    assert result.start == 'expression'
    assert result.parent_ids == ['arithmetic']
    grammars.save.assert_called_once_with(result)

# ** test: set_grammar_ignore_none_clears
def test_set_grammar_ignore_none_clears() -> None:
    '''
    Test that SetGrammarIgnore with ignore=None clears the fact, saves, and
    leaves layout unchanged.
    '''

    # Persist a grammar with both facts and clear ignore.
    profile = layout_profile()
    root = GrammarAggregate(id='arithmetic', start='expression', ignore=' ', layout=profile)
    grammars = grammar_service([root])
    result = DomainEvent.handle(
        SetGrammarIgnore,
        dependencies={'grammar_service': grammars},
        id='arithmetic',
        ignore=None,
    )

    # Assert the clear is saved and layout is untouched.
    assert result.ignore is None
    assert result.layout == profile
    grammars.save.assert_called_once_with(result)

# ** test: set_grammar_ignore_rejects_non_string
def test_set_grammar_ignore_rejects_non_string() -> None:
    '''
    Test that SetGrammarIgnore with a non-string, non-None value does not save.
    '''

    # Handle SetGrammarIgnore with an integer.
    grammars = grammar_service([grammar('arithmetic')])
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            SetGrammarIgnore,
            dependencies={'grammar_service': grammars},
            id='arithmetic',
            ignore=5,
        )

    # Assert nothing was saved.
    grammars.save.assert_not_called()

# ** test: set_grammar_layout_sets_or_clears
def test_set_grammar_layout_sets_or_clears() -> None:
    '''
    Test that SetGrammarLayout saves a profile, then clears it on None,
    leaving ignore, start, and parent_ids unchanged each time.
    '''

    # Persist a grammar with skip characters and set a profile.
    root = GrammarAggregate(id='arithmetic', start='expression', ignore=' \t')
    grammars = grammar_service([root])
    profile = layout_profile()
    result = DomainEvent.handle(
        SetGrammarLayout,
        dependencies={'grammar_service': grammars},
        id='arithmetic',
        layout=profile,
    )

    # Assert the profile is saved and ignore is untouched.
    assert result.layout == profile
    assert result.ignore == ' \t'
    assert result.start == 'expression'
    assert result.parent_ids == []

    # Clear the profile and assert ignore is still untouched.
    result = DomainEvent.handle(
        SetGrammarLayout,
        dependencies={'grammar_service': grammars},
        id='arithmetic',
        layout=None,
    )
    assert result.layout is None
    assert result.ignore == ' \t'
    assert grammars.save.call_count == 2

# ** test: set_grammar_layout_rejected_profile_does_not_save
@pytest.mark.parametrize('tab_size', [0, -1, False])
def test_set_grammar_layout_rejected_profile_does_not_save(tab_size) -> None:
    '''
    Test that SetGrammarLayout with a profile the field rejects raises that
    ValidationError, not a grammar error, and does not save.
    '''

    # Handle SetGrammarLayout with a non-positive tab size.
    grammars = grammar_service([grammar('arithmetic')])
    with pytest.raises(ValidationError):
        DomainEvent.handle(
            SetGrammarLayout,
            dependencies={'grammar_service': grammars},
            id='arithmetic',
            layout={
                'indent_token': 'INDENT',
                'dedent_token': 'DEDENT',
                'tab_size': tab_size,
            },
        )

    # Assert nothing was saved.
    grammars.save.assert_not_called()

# ** test: fact_writers_require_fact_keyword
@pytest.mark.parametrize('event_cls, keyword', [
    (SetGrammarIgnore, 'ignore'),
    (SetGrammarLayout, 'layout'),
])
def test_fact_writers_require_fact_keyword(event_cls, keyword) -> None:
    '''
    Test that a fact writer without its fact keyword raises
    COMMAND_PARAMETER_REQUIRED and does not save.
    '''

    # Handle the event with only the id.
    grammars = grammar_service([grammar('arithmetic')])
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            event_cls,
            dependencies={'grammar_service': grammars},
            id='arithmetic',
        )

    # Assert the framework's required-parameter error names the fact.
    assert raised.value.error_code == tiferet_a.error.COMMAND_PARAMETER_REQUIRED_ID
    assert raised.value.kwargs['parameters'] == [keyword]
    grammars.save.assert_not_called()

# ** test: fact_writers_require_only_id_through_decorator
@pytest.mark.parametrize('event_cls, keyword', [
    (SetGrammarIgnore, 'ignore'),
    (SetGrammarLayout, 'layout'),
])
def test_fact_writers_require_only_id_through_decorator(event_cls, keyword) -> None:
    '''
    Test that parameters_required lists only id: a missing id is the only
    decorator violation, even with a None fact.
    '''

    # Handle the event with a None id and a None fact.
    grammars = grammar_service([grammar('arithmetic')])
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            event_cls,
            dependencies={'grammar_service': grammars},
            id=None,
            **{keyword: None},
        )

    # Assert only id is reported missing.
    assert raised.value.error_code == tiferet_a.error.COMMAND_PARAMETER_REQUIRED_ID
    assert raised.value.kwargs['parameters'] == ['id']
    grammars.save.assert_not_called()

# ** test: fact_writers_need_only_grammar_service
@pytest.mark.parametrize('event_cls, facts', [
    (SetGrammarIgnore, {'ignore': ' '}),
    (SetGrammarLayout, {'layout': None}),
])
def test_fact_writers_need_only_grammar_service(event_cls, facts) -> None:
    '''
    Test that a fact writer is built from GrammarService alone, raises
    GRAMMAR_NOT_FOUND for a missing grammar, and runs no catalogue check.
    '''

    # Handle the event against a grammar that is not persisted.
    grammars = grammar_service()
    with pytest.raises(TiferetError) as raised:
        DomainEvent.handle(
            event_cls,
            dependencies={'grammar_service': grammars},
            id='missing',
            **facts,
        )
    assert raised.value.error_code == a.error.GRAMMAR_NOT_FOUND_ID
    grammars.save.assert_not_called()

    # A successful write never lists the catalogue or checks parents.
    grammars = grammar_service([grammar('arithmetic')])
    DomainEvent.handle(
        event_cls,
        dependencies={'grammar_service': grammars},
        id='arithmetic',
        **facts,
    )
    grammars.list.assert_not_called()
    grammars.exists.assert_not_called()
    grammars.save.assert_called_once()

# ** test_int: fact_writes_round_trip_through_repository
def test_int_fact_writes_round_trip_through_repository(
        grammar_repo: GrammarConfigRepository) -> None:
    '''
    Test fact writes against a real repository: exact strings and equal
    profiles reload, an empty ignore reloads as '', and a clear is omitted
    from the saved body and reloads as None.
    '''

    # Seed a grammar and set both facts.
    grammar_repo.save(grammar('arithmetic'))
    profile = layout_profile(tab_size=2)
    DomainEvent.handle(
        SetGrammarIgnore,
        dependencies={'grammar_service': grammar_repo},
        id='arithmetic',
        ignore=' \t',
    )
    DomainEvent.handle(
        SetGrammarLayout,
        dependencies={'grammar_service': grammar_repo},
        id='arithmetic',
        layout=profile,
    )

    # Assert the reloaded grammar carries the exact string and an equal profile.
    loaded = grammar_repo.get('arithmetic')
    assert loaded.ignore == ' \t'
    assert isinstance(loaded.layout, LayoutProfile)
    assert loaded.layout.model_dump() == profile.model_dump()

    # Set an empty ignore and assert it reloads as '', not None.
    DomainEvent.handle(
        SetGrammarIgnore,
        dependencies={'grammar_service': grammar_repo},
        id='arithmetic',
        ignore='',
    )
    assert grammar_repo.get('arithmetic').ignore == ''

    # Clear both facts and assert the saved body omits them.
    DomainEvent.handle(
        SetGrammarIgnore,
        dependencies={'grammar_service': grammar_repo},
        id='arithmetic',
        ignore=None,
    )
    DomainEvent.handle(
        SetGrammarLayout,
        dependencies={'grammar_service': grammar_repo},
        id='arithmetic',
        layout=None,
    )
    raw = yaml.safe_load(Path(grammar_repo.config_file).read_text(encoding='utf-8'))
    assert raw['grammars']['arithmetic'] == {
        'parent_ids': [],
        'start': 'expression',
    }
    loaded = grammar_repo.get('arithmetic')
    assert loaded.ignore is None
    assert loaded.layout is None

# ** test_int: fact_writes_are_not_inherited
def test_int_fact_writes_are_not_inherited(
        grammar_repo: GrammarConfigRepository) -> None:
    '''
    Test that a child created under a parent with both facts, and then
    re-parented, reloads with neither fact while the parent keeps both.
    '''

    # Add a parent with both facts through AddGrammar.
    productions = production_service([production()])
    profile = layout_profile()
    DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammar_repo,
            'production_service': productions,
        },
        id='arithmetic',
        start='expression',
        ignore=' \t',
        layout=profile,
    )

    # Add a child under that parent without its own facts.
    DomainEvent.handle(
        AddGrammar,
        dependencies={
            'grammar_service': grammar_repo,
            'production_service': productions,
        },
        id='comments',
        start='expression',
        parent_ids=['arithmetic'],
    )

    # Update the child's parents and start without touching its facts.
    DomainEvent.handle(
        SetGrammarParentIds,
        dependencies={
            'grammar_service': grammar_repo,
            'production_service': productions,
        },
        id='comments',
        parent_ids=['arithmetic'],
    )

    # Assert the child reloads with no facts and the parent keeps both.
    child = grammar_repo.get('comments')
    assert child.ignore is None
    assert child.layout is None
    parent = grammar_repo.get('arithmetic')
    assert parent.ignore == ' \t'
    assert parent.layout.model_dump() == profile.model_dump()

# ** test: fact_writers_do_not_consult_layout_filter
def test_fact_writers_do_not_consult_layout_filter() -> None:
    '''
    Test that the grammar event module neither imports LayoutFilter nor
    defines a combined or clear-only fact event.
    '''

    # Import the grammar event module.
    from tiferet_ly.events import grammar as grammar_events

    # Assert no filter dependency and no extra update types.
    assert 'LayoutFilter' not in grammar_events.__dict__
    for name in ('UpdateGrammar', 'ClearGrammarIgnore', 'ClearGrammarLayout', 'SetGrammarFacts'):
        assert not hasattr(grammar_events, name)

