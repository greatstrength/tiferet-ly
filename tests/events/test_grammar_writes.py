"""Tiferet Ly Grammar Write Event Tests"""

# *** imports

# ** core
import ast
import inspect
import textwrap
from pathlib import Path
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
    SetGrammarParentIds,
    SetGrammarStart,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ProductionRuleAggregate

# *** constants

# ** constant: grammar_events
_GRAMMAR_EVENTS = Path(inspect.getfile(GrammarEvent))

# ** constant: grammar_assets_file
_GRAMMAR_ASSETS = Path(grammar_assets.__file__)

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
        stored: set[str] | None = None,
        grammars: list[GrammarAggregate] | None = None,
        productions: list[ProductionRuleAggregate] | None = None,
        gotten: GrammarAggregate | None = None,
    ) -> tuple[Mock, Mock]:
    '''
    Build mocked grammar and production services.

    :param stored: Identifiers that ``exists`` reports as stored.
    :type stored: set[str] | None
    :param grammars: The catalogue returned by ``list``.
    :type grammars: list[GrammarAggregate] | None
    :param productions: The productions returned by ``list``.
    :type productions: list[ProductionRuleAggregate] | None
    :param gotten: The aggregate returned by ``get``, if any.
    :type gotten: GrammarAggregate | None
    :return: The grammar service and the production service.
    :rtype: tuple[Mock, Mock]
    '''

    # Exists answers from the supplied identifier set.
    present = stored or set()
    grammar_service = Mock()
    grammar_service.exists.side_effect = lambda grammar_id: grammar_id in present
    grammar_service.list.return_value = list(grammars or [])
    grammar_service.get.return_value = gotten

    # Productions are a catalogue, not a file.
    production_service = Mock()
    production_service.list.return_value = list(productions or [])
    return grammar_service, production_service

# ** function: handle
def _handle(event_cls, grammar_service, production_service, **kwargs):
    '''
    Invoke a grammar write event through the domain-event handle.

    :param event_cls: The event class to handle.
    :type event_cls: type
    :param grammar_service: The mocked grammar service.
    :type grammar_service: Mock
    :param production_service: The mocked production service.
    :type production_service: Mock
    :param kwargs: Event keyword arguments.
    :type kwargs: dict
    :return: The event result.
    :rtype: GrammarAggregate
    '''

    return DomainEvent.handle(
        event_cls,
        dependencies={
            'grammar_service': grammar_service,
            'production_service': production_service,
        },
        **kwargs,
    )

# ** function: called_names
def _called_names(function) -> set[str]:
    '''
    Collect names and attributes called directly by a function.

    :param function: The function whose source to inspect.
    :type function: Callable
    :return: Called names and attribute names.
    :rtype: set[str]
    '''

    # Read the function body, not the class indentation around it.
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    called = set()
    for node in ast.walk(tree.body[0]):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    return called

# ** function: imported_modules
def _imported_modules(tree: ast.AST) -> list[str]:
    '''
    Collect imported module names from a parsed module.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Imported module names.
    :rtype: list[str]
    '''

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

# ** function: record_calls
def _record_calls(method_name: str):
    '''
    Patch an aggregate mutator so calls are recorded and still run.

    :param method_name: The GrammarAggregate method to wrap.
    :type method_name: str
    :return: The patch and the list of ``(instance, args)`` calls.
    :rtype: tuple
    '''

    # Keep the real mutation. Do not assign onto the pydantic instance.
    original = getattr(GrammarAggregate, method_name)
    calls = []

    def wrapper(self, *args, **kwargs):
        calls.append((self, args))
        return original(self, *args, **kwargs)

    return patch.object(GrammarAggregate, method_name, wrapper), calls

# *** tests

# ** test: module_surface
def test_module_surface():
    '''
    Keep create and update events on the grammar event module.
    '''

    # The four published classes live in the event module.
    assert inspect.getfile(GrammarEvent) == inspect.getfile(AddGrammar)
    assert inspect.getfile(SetGrammarStart) == inspect.getfile(AddGrammar)
    assert inspect.getfile(SetGrammarParentIds) == inspect.getfile(AddGrammar)

    # Constructors set the published service attributes.
    grammar_service, production_service = _services()
    base = GrammarEvent(grammar_service)
    assert list(inspect.signature(GrammarEvent.__init__).parameters) == [
        'self',
        'grammar_service',
    ]
    assert base.grammar_service is grammar_service
    for event_cls in (AddGrammar, SetGrammarStart, SetGrammarParentIds):
        event = event_cls(grammar_service, production_service)
        assert list(inspect.signature(event_cls.__init__).parameters) == [
            'self',
            'grammar_service',
            'production_service',
        ]
        assert event.grammar_service is grammar_service
        assert event.production_service is production_service

    # Start resolution selects productions and does not cycle-check.
    called = _called_names(GrammarEvent._verify_start_resolves)
    assert 'select_productions' in called
    assert 'has_cycle' not in called
    assert '_assert_starts_resolve' not in called

    # The module does not copy the production-side helper or forbidden imports.
    source = _GRAMMAR_EVENTS.read_text()
    tree = ast.parse(source)
    assert 'def _assert_starts_resolve' not in source
    modules = _imported_modules(tree)
    assert 'tiferet_ly.utils.grammar' in modules
    for module in modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert 'ProductionEvent' not in module
        assert not module.startswith('tiferet_ly.repos')
    imported_names = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    assert 'GrammarRuleSelector' in imported_names
    assert 'ProductionEvent' not in imported_names

    # Callers import the event module. The package does not re-export it.
    assert AddGrammar.__module__ == 'tiferet_ly.events.grammar'
    for name in (
        'GrammarEvent',
        'AddGrammar',
        'SetGrammarStart',
        'SetGrammarParentIds',
    ):
        assert not hasattr(events_package, name)

    # Error ids are an ids section only.
    assets_source = _GRAMMAR_ASSETS.read_text()
    assert '# *** constants (ids)' in assets_source
    assert '(models)' not in assets_source
    assert '(groups)' not in assets_source
    assert grammar_assets.GRAMMAR_ALREADY_EXISTS_ID == 'GRAMMAR_ALREADY_EXISTS'
    assert grammar_assets.GRAMMAR_NOT_FOUND_ID == 'GRAMMAR_NOT_FOUND'
    assert grammar_assets.GRAMMAR_CYCLE_DETECTED_ID == 'GRAMMAR_CYCLE_DETECTED'
    assert grammar_assets.GRAMMAR_START_NOT_FOUND_ID == 'GRAMMAR_START_NOT_FOUND'
    assert grammar_assets.GRAMMAR_PARENT_NOT_FOUND_ID == 'GRAMMAR_PARENT_NOT_FOUND'
    assert grammar_assets.GRAMMAR_STILL_REFERENCED_ID == 'GRAMMAR_STILL_REFERENCED'

# ** test: add_grammar_already_exists
def test_add_grammar_already_exists():
    '''
    Reject an existing grammar before a missing parent can be checked.
    '''

    # The id is stored, and one requested parent is not.
    grammar_service, production_service = _services(
        stored={'taken'},
    )

    # Already-exists wins, including when a parent is missing.
    with pytest.raises(TiferetError) as caught:
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='taken',
            start='expr',
            parent_ids=['missing'],
        )

    # The error names that id, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_ALREADY_EXISTS_ID
    assert caught.value.kwargs['id'] == 'taken'
    grammar_service.save.assert_not_called()

# ** test: add_grammar_parent_not_found
def test_add_grammar_parent_not_found():
    '''
    Reject a missing parent before treating a self-parent as a cycle.
    '''

    grammar_service, production_service = _services()

    # The first missing parent fails the write.
    with pytest.raises(TiferetError) as caught:
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='new',
            start='expr',
            parent_ids=['missing', 'new'],
        )

    # The error names the missing parent, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_PARENT_NOT_FOUND_ID
    assert caught.value.kwargs['parent_id'] == 'missing'
    grammar_service.save.assert_not_called()

# ** test: add_grammar_self_cycle
def test_add_grammar_self_cycle():
    '''
    Reject a self-parent as a cycle before start resolution.
    '''

    # No production is named start. Cycle still wins.
    grammar_service, production_service = _services()

    with pytest.raises(TiferetError) as caught:
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='new',
            start='expr',
            parent_ids=['new'],
        )

    # The error names the candidate, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_CYCLE_DETECTED_ID
    assert caught.value.kwargs['id'] == 'new'
    grammar_service.save.assert_not_called()
    production_service.list.assert_not_called()

# ** test: add_grammar_indirect_cycle
def test_add_grammar_indirect_cycle():
    '''
    Reject a parent that already reaches the unsaved candidate.
    '''

    # The catalogue holds only the parent that points back.
    mid = _grammar('mid', ['new'])
    grammar_service, production_service = _services(
        stored={'mid'},
        grammars=[mid],
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='new',
            start='expr',
            parent_ids=['mid'],
        )

    # The cycle is reported, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_CYCLE_DETECTED_ID
    assert caught.value.kwargs['id'] == 'new'
    grammar_service.save.assert_not_called()

# ** test: add_grammar_start_not_found
def test_add_grammar_start_not_found():
    '''
    Reject a start that selection does not return for the candidate.
    '''

    grammar_service, production_service = _services(
        productions=[_production('other', 'new')],
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='new',
            start='expr',
        )

    # The error names the candidate and its start, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'new'
    assert caught.value.kwargs['start'] == 'expr'
    grammar_service.save.assert_not_called()

# ** test: add_grammar_own_production
def test_add_grammar_own_production():
    '''
    Save a root grammar whose start is declared on the new id.
    '''

    # The catalogue does not yet contain the new grammar.
    grammar_service, production_service = _services(
        productions=[_production('expr', 'new')],
    )

    # An omitted parent list is empty.
    result = _handle(
        AddGrammar,
        grammar_service,
        production_service,
        id='new',
        start='expr',
        parent_ids=None,
    )

    # The returned aggregate is the saved aggregate.
    assert result is grammar_service.save.call_args.args[0]
    assert isinstance(result, GrammarAggregate)
    assert result is not None
    assert result.id == 'new'
    assert result.parent_ids == []
    assert result.start == 'expr'

# ** test: add_grammar_parent_production
def test_add_grammar_parent_production():
    '''
    Save a dialect whose start is declared only on an existing parent.
    '''

    base = _grammar('base', [])
    grammar_service, production_service = _services(
        stored={'base'},
        grammars=[base],
        productions=[_production('expr', 'base')],
    )

    result = _handle(
        AddGrammar,
        grammar_service,
        production_service,
        id='dialect',
        start='expr',
        parent_ids=['base'],
    )

    # The dialect is saved even though it declares no production.
    assert result is grammar_service.save.call_args.args[0]
    assert result.id == 'dialect'
    assert result.parent_ids == ['base']
    assert result.start == 'expr'
    assert result is not None

# ** test: set_parent_ids_not_found
def test_set_parent_ids_not_found():
    '''
    Do not mutate or save a grammar that is not stored.
    '''

    grammar_service, production_service = _services(gotten=None)
    parent_patch, parent_calls = _record_calls('set_parent_ids')

    with parent_patch:
        with pytest.raises(TiferetError) as caught:
            _handle(
                SetGrammarParentIds,
                grammar_service,
                production_service,
                id='missing',
                parent_ids=['base'],
            )

    # The error names the missing id, and neither mutation nor save runs.
    assert caught.value.error_code == grammar_assets.GRAMMAR_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'missing'
    assert parent_calls == []
    grammar_service.save.assert_not_called()

# ** test: set_parent_ids_parent_not_found
def test_set_parent_ids_parent_not_found():
    '''
    Reject a missing parent before replacing the stored parent list.
    '''

    grammar = _grammar('g', ['safe'])
    grammar_service, production_service = _services(gotten=grammar)
    parent_patch, parent_calls = _record_calls('set_parent_ids')

    with parent_patch:
        with pytest.raises(TiferetError) as caught:
            _handle(
                SetGrammarParentIds,
                grammar_service,
                production_service,
                id='g',
                parent_ids=['missing'],
            )

    # The parent error wins, and neither mutation nor save runs.
    assert caught.value.error_code == grammar_assets.GRAMMAR_PARENT_NOT_FOUND_ID
    assert caught.value.kwargs['parent_id'] == 'missing'
    assert parent_calls == []
    grammar_service.save.assert_not_called()
    assert grammar.parent_ids == ['safe']

# ** test: set_parent_ids_cycle
def test_set_parent_ids_cycle():
    '''
    Reject a candidate parent that reaches the grammar through another grammar.
    '''

    # Persisted parents are safe. The candidate parent loops back.
    grammar = _grammar('g', ['safe'])
    looper = _grammar('looper', ['g'])
    safe = _grammar('safe', [])
    grammar_service, production_service = _services(
        stored={'g', 'looper', 'safe'},
        grammars=[grammar, looper, safe],
        gotten=grammar,
    )
    parent_patch, parent_calls = _record_calls('set_parent_ids')

    with parent_patch:
        with pytest.raises(TiferetError) as caught:
            _handle(
                SetGrammarParentIds,
                grammar_service,
                production_service,
                id='g',
                parent_ids=['looper'],
            )

    # The candidate frontier cycles, so neither mutation nor save runs.
    assert caught.value.error_code == grammar_assets.GRAMMAR_CYCLE_DETECTED_ID
    assert caught.value.kwargs['id'] == 'g'
    assert parent_calls == []
    grammar_service.save.assert_not_called()
    assert grammar.parent_ids == ['safe']

# ** test: set_parent_ids_start_not_found
def test_set_parent_ids_start_not_found():
    '''
    Reject clearing parents when the start lived only on the old parent.
    '''

    # The loaded aggregate is distinct from the catalogue copy.
    dialect = _grammar('dialect', ['base'])
    catalogue = _grammar('dialect', ['base'])
    base = _grammar('base', [], start='other')
    grammar_service, production_service = _services(
        stored={'base'},
        grammars=[catalogue, base],
        productions=[_production('expr', 'base')],
        gotten=dialect,
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            SetGrammarParentIds,
            grammar_service,
            production_service,
            id='dialect',
            parent_ids=[],
        )

    # Start fails for the candidate, and the catalogue copy is not saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'dialect'
    assert caught.value.kwargs['start'] == 'expr'
    grammar_service.save.assert_not_called()
    assert dialect.parent_ids == []
    assert catalogue.parent_ids == ['base']

# ** test: set_parent_ids_saves
def test_set_parent_ids_saves():
    '''
    Save the mutated aggregate when the new parent provides the start.
    '''

    dialect = _grammar('dialect', [])
    base = _grammar('base', [])
    grammar_service, production_service = _services(
        stored={'base', 'dialect'},
        grammars=[_grammar('dialect', []), base],
        productions=[_production('expr', 'base')],
        gotten=dialect,
    )
    parent_patch, parent_calls = _record_calls('set_parent_ids')

    with parent_patch:
        result = _handle(
            SetGrammarParentIds,
            grammar_service,
            production_service,
            id='dialect',
            parent_ids=['base'],
        )

    # The candidate parents are applied, saved, and returned.
    assert parent_calls == [(dialect, (['base'],))]
    assert result is dialect
    assert result is grammar_service.save.call_args.args[0]
    assert result is not None
    assert result.parent_ids == ['base']

# ** test: set_start_not_found_grammar
def test_set_start_not_found_grammar():
    '''
    Do not save a start change for a grammar that is not stored.
    '''

    grammar_service, production_service = _services(gotten=None)

    with pytest.raises(TiferetError) as caught:
        _handle(
            SetGrammarStart,
            grammar_service,
            production_service,
            id='missing',
            start='expr',
        )

    # The error names the missing id, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'missing'
    grammar_service.save.assert_not_called()

# ** test: set_start_not_found_name
def test_set_start_not_found_name():
    '''
    Reject a start that is not in the current effective set.
    '''

    grammar = _grammar('g', [])
    grammar_service, production_service = _services(
        grammars=[grammar],
        productions=[_production('expr', 'g')],
        gotten=grammar,
    )

    with pytest.raises(TiferetError) as caught:
        _handle(
            SetGrammarStart,
            grammar_service,
            production_service,
            id='g',
            start='missing',
        )

    # The error names the candidate start, and nothing is saved.
    assert caught.value.error_code == grammar_assets.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['id'] == 'g'
    assert caught.value.kwargs['start'] == 'missing'
    grammar_service.save.assert_not_called()

# ** test: set_start_ignores_cycle_patch
def test_set_start_ignores_cycle_patch():
    '''
    Save a resolved start even when the cycle check is forced true.
    '''

    grammar = _grammar('g', [], start='old')
    grammar_service, production_service = _services(
        grammars=[grammar],
        productions=[_production('expr', 'g')],
        gotten=grammar,
    )
    start_patch, start_calls = _record_calls('set_start')
    parent_patch, parent_calls = _record_calls('set_parent_ids')

    # The cycle check is not part of a start write.
    with start_patch, parent_patch, patch(
        'tiferet_ly.events.grammar.GrammarRuleSelector.has_cycle',
        return_value=True,
    ) as has_cycle:
        result = _handle(
            SetGrammarStart,
            grammar_service,
            production_service,
            id='g',
            start='expr',
        )

    # The start is applied, saved, and returned without a cycle check.
    has_cycle.assert_not_called()
    assert start_calls == [(grammar, ('expr',))]
    assert parent_calls == []
    assert result is grammar
    assert result is grammar_service.save.call_args.args[0]
    assert result is not None
    assert result.start == 'expr'

# ** test: set_start_ignores_other_grammar
def test_set_start_ignores_other_grammar():
    '''
    Do not reject another grammar whose own start does not resolve.
    '''

    grammar = _grammar('g', [], start='old')
    other = _grammar('other', [], start='absent')
    grammar_service, production_service = _services(
        grammars=[grammar, other],
        productions=[_production('expr', 'g')],
        gotten=grammar,
    )

    result = _handle(
        SetGrammarStart,
        grammar_service,
        production_service,
        id='g',
        start='expr',
    )

    # The other grammar's unresolved start does not fail this write.
    assert result is grammar
    assert result is not None
    assert result.start == 'expr'
    grammar_service.save.assert_called_once_with(grammar)

# ** test: required_parameters_do_not_save
def test_required_parameters_do_not_save():
    '''
    Do not save when a required parameter is missing, blank, or None.
    '''

    grammar_service, production_service = _services(
        gotten=_grammar('g', []),
    )

    # Each invalid call stops before a write.
    with pytest.raises(TiferetError):
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            start='expr',
        )
    with pytest.raises(TiferetError):
        _handle(
            AddGrammar,
            grammar_service,
            production_service,
            id='   ',
            start='expr',
        )
    with pytest.raises(TiferetError):
        _handle(
            SetGrammarStart,
            grammar_service,
            production_service,
            id='g',
        )
    with pytest.raises(TiferetError):
        _handle(
            SetGrammarParentIds,
            grammar_service,
            production_service,
            id='g',
            parent_ids=None,
        )

    grammar_service.save.assert_not_called()
