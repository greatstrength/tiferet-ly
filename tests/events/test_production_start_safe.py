"""Tiferet Ly Production Start-Safe Event Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path
from unittest.mock import Mock, patch

# ** infra
import pytest

# ** app
import tiferet_ly.events as events_package
from tiferet import DomainEvent, TiferetError
from tiferet_ly import assets as a
from tiferet_ly.events.grammar import GrammarEvent
from tiferet_ly.events.production import (
    PRODUCTION_ALREADY_EXISTS_ID,
    PRODUCTION_NOT_FOUND_ID,
    ProductionEvent,
    ReassignProductionGrammar,
    RemoveProduction,
    RenameProduction,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)

# *** constants

# ** constant: start_safe_events
_START_SAFE_EVENTS = (
    RemoveProduction,
    RenameProduction,
    ReassignProductionGrammar,
)

# ** constant: required_parameters
_REQUIRED = {
    RemoveProduction: ('name', 'grammar_id', 'spec'),
    RenameProduction: ('name', 'grammar_id', 'spec', 'new_name'),
    ReassignProductionGrammar: ('name', 'grammar_id', 'spec', 'new_grammar_id'),
}

# ** constant: valid_parameters
_VALID = {
    'name': 'expr',
    'grammar_id': 'base',
    'spec': 'term',
    'new_name': 'stmt',
    'new_grammar_id': 'other',
}

# *** functions

# ** function: simple
def _simple(
        name: str = 'expr',
        grammar_id: str = 'base',
        spec: str = 'term',
    ) -> SimpleProductionRuleAggregate:
    '''
    Build a simple production aggregate.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production specification.
    :type spec: str
    :return: A simple production aggregate.
    :rtype: SimpleProductionRuleAggregate
    '''

    return SimpleProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )

# ** function: complex
def _complex(
        name: str = 'expr',
        grammar_id: str = 'base',
        spec: str = 'term',
        action: str = 'return p[0]',
    ) -> ComplexProductionRuleAggregate:
    '''
    Build a complex production aggregate.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production specification.
    :type spec: str
    :param action: The action source.
    :type action: str
    :return: A complex production aggregate.
    :rtype: ComplexProductionRuleAggregate
    '''

    return ComplexProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
        action=action,
    )

# ** function: grammar
def _grammar(
        grammar_id: str,
        parent_ids: list[str] | None = None,
        start: str = 'stmt',
    ) -> GrammarAggregate:
    '''
    Build a lean grammar aggregate.

    :param grammar_id: The grammar identifier.
    :type grammar_id: str
    :param parent_ids: The ordered parent identifiers.
    :type parent_ids: list[str] | None
    :param start: The declared start name.
    :type start: str
    :return: A grammar aggregate.
    :rtype: GrammarAggregate
    '''

    return GrammarAggregate(
        id=grammar_id,
        parent_ids=parent_ids or [],
        start=start,
    )

# ** function: services
def _services(
        productions: list | None = None,
        grammars: list | None = None,
    ) -> tuple[Mock, Mock]:
    '''
    Build mocked production and grammar services.

    :param productions: The catalogue returned by production ``list``.
    :type productions: list | None
    :param grammars: The catalogue returned by grammar ``list``.
    :type grammars: list | None
    :return: The production service and the grammar service.
    :rtype: tuple[Mock, Mock]
    '''

    # Listing is the only read these events are allowed to use.
    production_service = Mock()
    production_service.list.return_value = list(productions or [])
    grammar_service = Mock()
    grammar_service.list.return_value = list(grammars or [])
    return production_service, grammar_service

# ** function: handle
def _handle(event_cls, production_service, grammar_service, **kwargs):
    '''
    Invoke a start-safe production event through the domain-event handle.

    :param event_cls: The event class to handle.
    :type event_cls: type
    :param production_service: The mocked production service.
    :type production_service: Mock
    :param grammar_service: The mocked grammar service.
    :type grammar_service: Mock
    :param kwargs: Event keyword arguments.
    :type kwargs: dict
    :return: The event result.
    :rtype: object
    '''

    return DomainEvent.handle(
        event_cls,
        dependencies={
            'production_service': production_service,
            'grammar_service': grammar_service,
        },
        **kwargs,
    )

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

# ** function: spy
def _spy(cls, method_name: str):
    '''
    Patch an aggregate mutator so calls are recorded and still run.

    :param cls: The aggregate class that defines the method.
    :type cls: type
    :param method_name: The method to wrap.
    :type method_name: str
    :return: The patch and the recorded positional arguments.
    :rtype: tuple
    '''

    # Keep the real mutation. Do not assign onto the pydantic instance.
    original = getattr(cls, method_name)
    calls = []

    def wrapper(self, *args, **kwargs):
        calls.append((self, args))
        return original(self, *args, **kwargs)

    return patch.object(cls, method_name, wrapper), calls

# ** function: watch_assert
def _watch_assert(seen: dict):
    '''
    Record the catalogue passed to the start helper, then run it.

    :param seen: The dict that receives the catalogue and grammar list.
    :type seen: dict
    :return: The patch for ``ProductionEvent._assert_starts_resolve``.
    :rtype: unittest.mock._patch
    '''

    # Capture the post-mutation catalogue before the loaded row can change.
    original = ProductionEvent._assert_starts_resolve

    def wrapper(self, productions, grammars):
        seen['productions'] = list(productions)
        seen['grammars'] = grammars
        return original(self, productions, grammars)

    return patch.object(ProductionEvent, '_assert_starts_resolve', wrapper)

# ** function: assert_unwritten
def _assert_unwritten(production_service: Mock) -> None:
    '''
    Assert that no production write was attempted.

    :param production_service: The mocked production service.
    :type production_service: Mock
    :return: None
    :rtype: None
    '''

    production_service.save.assert_not_called()
    production_service.delete.assert_not_called()
    production_service.delete_alternative.assert_not_called()
    production_service.replace.assert_not_called()

# *** tests

# ** test: module_surface
def test_module_surface():
    '''
    Keep the shrinking writers on their module, out of the package export.
    '''

    production_service, grammar_service = _services()
    event_path = Path(inspect.getfile(ProductionEvent))
    event_tree = ast.parse(event_path.read_text())
    event_source = event_path.read_text()

    # Each writer extends the base and takes only the two services.
    for event_cls in _START_SAFE_EVENTS:
        assert issubclass(event_cls, ProductionEvent)
        assert event_cls.__module__ == 'tiferet_ly.events.production'
        assert list(inspect.signature(event_cls.__init__).parameters) == [
            'self',
            'production_service',
            'grammar_service',
        ]
        event = event_cls(production_service, grammar_service)
        assert event.production_service is production_service
        assert event.grammar_service is grammar_service
        with pytest.raises(TypeError):
            event_cls(production_service)
        assert not hasattr(events_package, event_cls.__name__)

    # The base still constructs with only the production service.
    assert list(inspect.signature(ProductionEvent.__init__).parameters) == [
        'self',
        'production_service',
    ]

    # The package marker does not import or bind the shrinking writers.
    package_tree = ast.parse(Path(events_package.__file__).read_text())
    imported_names = [
        alias.name
        for node in ast.walk(package_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    for event_cls in _START_SAFE_EVENTS:
        assert event_cls.__name__ not in imported_names
    assert not any(
        module.endswith('production') or '.production' in module
        for module in _imported_modules(package_tree)
    )

    # Selector is imported. Repositories, PLY, and GrammarEvent are not.
    modules = _imported_modules(event_tree)
    assert 'tiferet_ly.utils.grammar' in modules
    assert 'GrammarRuleSelector' in [
        alias.name
        for node in ast.walk(event_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    for module in modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert not module.startswith('tiferet_ly.repos')
        assert 'events.grammar' not in module
    assert 'GrammarEvent' not in event_source
    assert '_verify_start_resolves' not in event_source
    for forbidden in ('token_rules', 'production_rules', 'subgrammars', 'subgrammar'):
        assert forbidden not in event_source

# ** test: assert_starts_resolve_uses_selector_order
def test_assert_starts_resolve_uses_selector_order():
    '''
    Raise on the first grammar whose selector result lacks that start.
    '''

    kept = _simple(name='kept', spec='ID')
    production_service, grammar_service = _services(
        productions=[kept, _simple(name='other', spec='NUMBER')],
        grammars=[
            _grammar('first', start='expr'),
            _grammar('later', start='expr'),
        ],
    )
    calls = []

    def select(grammar, grammars, productions):
        calls.append(grammar.id)
        assert grammars is grammar_service.list.return_value
        assert productions == [kept]
        return [_simple(name='unrelated', grammar_id=grammar.id, spec='x')]

    # The first grammar fails. The later grammar is not consulted.
    verify = patch.object(
        GrammarEvent,
        '_verify_start_resolves',
        side_effect=AssertionError('grammar event must not resolve starts'),
    )
    selector = patch(
        'tiferet_ly.events.production.GrammarRuleSelector.select_productions',
        side_effect=select,
    )
    with verify, selector, pytest.raises(TiferetError) as caught:
        _handle(
            RemoveProduction,
            production_service,
            grammar_service,
            name='other',
            grammar_id='base',
            spec='NUMBER',
        )

    assert caught.value.error_code == a.grammar.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.error_code == 'GRAMMAR_START_NOT_FOUND'
    assert caught.value.kwargs['grammar_id'] == 'first'
    assert caught.value.kwargs['start'] == 'expr'
    assert 'Grammar start not found: expr in grammar first.' in str(caught.value)
    assert calls == ['first']
    _assert_unwritten(production_service)

    # An earlier grammar that the selector can resolve does not hide a later failure.
    calls.clear()
    production_service, grammar_service = _services(
        productions=[_simple(name='other', spec='NUMBER')],
        grammars=[
            _grammar('earlier', start='stmt'),
            _grammar('dialect', start='expr'),
        ],
    )

    def select_later(grammar, grammars, productions):
        calls.append((grammar.id, grammars))
        if grammar.id == 'earlier':
            return [_simple(name='stmt', grammar_id='earlier', spec='keep')]
        return []

    selector = patch(
        'tiferet_ly.events.production.GrammarRuleSelector.select_productions',
        side_effect=select_later,
    )
    with verify, selector, pytest.raises(TiferetError) as caught:
        _handle(
            RemoveProduction,
            production_service,
            grammar_service,
            name='other',
            grammar_id='base',
            spec='NUMBER',
        )

    assert caught.value.kwargs['grammar_id'] == 'dialect'
    assert calls == [
        ('earlier', grammar_service.list.return_value),
        ('dialect', grammar_service.list.return_value),
    ]
    _assert_unwritten(production_service)

# ** test: remove_production_identity_errors
def test_remove_production_identity_errors():
    '''
    Refuse a missing or repeated triple before delete.
    '''

    missing_service, grammar_service = _services([_simple(spec='other')])
    with pytest.raises(TiferetError) as caught:
        _handle(
            RemoveProduction,
            missing_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
        )

    assert caught.value.error_code == PRODUCTION_NOT_FOUND_ID
    assert caught.value.kwargs['name'] == 'expr'
    assert caught.value.kwargs['grammar_id'] == 'base'
    assert caught.value.kwargs['spec'] == 'term'
    assert 'Production not found: expr in grammar base with spec term.' in str(caught.value)
    _assert_unwritten(missing_service)
    grammar_service.list.assert_not_called()

    repeated_service, grammar_service = _services([_simple(), _simple()])
    with pytest.raises(TiferetError) as caught:
        _handle(
            RemoveProduction,
            repeated_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
        )

    assert caught.value.error_code == PRODUCTION_ALREADY_EXISTS_ID
    assert caught.value.kwargs['spec'] == 'term'
    assert 'Production already exists: expr in grammar base with spec term.' in str(caught.value)
    _assert_unwritten(repeated_service)
    grammar_service.list.assert_not_called()

# ** test: remove_production_inherited_start
def test_remove_production_inherited_start():
    '''
    Refuse removal when a later dialect would lose an inherited start.
    '''

    base = _grammar('base', start='stmt')
    dialect = _grammar('dialect', parent_ids=['base'], start='expr')
    stmt = _simple(name='stmt', spec='SKIP')
    expr = _simple(name='expr', grammar_id='base', spec='term')
    production_service, grammar_service = _services(
        productions=[stmt, expr],
        grammars=[base, dialect],
    )
    verify = patch.object(
        GrammarEvent,
        '_verify_start_resolves',
        side_effect=AssertionError('grammar event must not resolve starts'),
    )

    with verify, pytest.raises(TiferetError) as caught:
        _handle(
            RemoveProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
        )

    assert caught.value.error_code == a.grammar.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['grammar_id'] == 'dialect'
    assert caught.value.kwargs['start'] == 'expr'
    assert 'Grammar start not found: expr in grammar dialect.' in str(caught.value)
    assert expr.name == 'expr'
    _assert_unwritten(production_service)

# ** test: remove_production_keeps_alternative_or_orphan
def test_remove_production_keeps_alternative_or_orphan():
    '''
    Delete one alternative when a sibling or no persisted start still needs it.
    '''

    # A remaining alternative keeps the inherited start resolvable.
    base = _grammar('base', start='stmt')
    dialect = _grammar('dialect', parent_ids=['base'], start='expr')
    sibling = _simple(name='expr', spec='term PLUS factor')
    target = _simple(name='expr', spec='term')
    production_service, grammar_service = _services(
        productions=[_simple(name='stmt', spec='SKIP'), target, sibling],
        grammars=[base, dialect],
    )
    seen = {}
    with _watch_assert(seen):
        result = _handle(
            RemoveProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
        )

    assert result == ('expr', 'base', 'term')
    assert seen['productions'] == [
        production_service.list.return_value[0],
        sibling,
    ]
    assert target not in seen['productions']
    assert seen['grammars'] is grammar_service.list.return_value
    production_service.delete_alternative.assert_called_once_with('expr', 'base', 'term')
    production_service.delete.assert_not_called()
    production_service.save.assert_not_called()

    # An orphan row is outside every persisted effective set.
    orphan = _simple(grammar_id='missing-grammar')
    kept = _simple(name='stmt', grammar_id='base', spec='SKIP')
    production_service, grammar_service = _services(
        productions=[kept, orphan],
        grammars=[_grammar('base', start='stmt')],
    )
    seen = {}
    with _watch_assert(seen):
        result = _handle(
            RemoveProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='missing-grammar',
            spec='term',
        )

    assert result == ('expr', 'missing-grammar', 'term')
    assert seen['productions'] == [kept]
    production_service.delete_alternative.assert_called_once_with(
        'expr',
        'missing-grammar',
        'term',
    )
    production_service.delete.assert_not_called()
    grammar_service.exists.assert_not_called()

# ** test: rename_and_reassign_identity_errors
def test_rename_and_reassign_identity_errors():
    '''
    Refuse a missing or repeated triple before save.
    '''

    for event_cls, extra in (
        (RenameProduction, {'new_name': 'stmt'}),
        (ReassignProductionGrammar, {'new_grammar_id': 'other'}),
    ):
        missing_service, grammar_service = _services([_simple(spec='other')])
        with pytest.raises(TiferetError) as caught:
            _handle(
                event_cls,
                missing_service,
                grammar_service,
                name='expr',
                grammar_id='base',
                spec='term',
                **extra,
            )
        assert caught.value.error_code == PRODUCTION_NOT_FOUND_ID
        assert caught.value.kwargs['name'] == 'expr'
        assert caught.value.kwargs['grammar_id'] == 'base'
        assert caught.value.kwargs['spec'] == 'term'
        _assert_unwritten(missing_service)
        grammar_service.list.assert_not_called()

        repeated_service, grammar_service = _services([_simple(), _simple()])
        with pytest.raises(TiferetError) as caught:
            _handle(
                event_cls,
                repeated_service,
                grammar_service,
                name='expr',
                grammar_id='base',
                spec='term',
                **extra,
            )
        assert caught.value.error_code == PRODUCTION_ALREADY_EXISTS_ID
        assert repeated_service.list.return_value[0].name == 'expr'
        assert repeated_service.list.return_value[0].grammar_id == 'base'
        _assert_unwritten(repeated_service)
        grammar_service.list.assert_not_called()

# ** test: rename_and_reassign_unresolved_start
def test_rename_and_reassign_unresolved_start():
    '''
    Refuse a rename or reassign that leaves an inherited start unresolved.
    '''

    base = _grammar('base', start='stmt')
    dialect = _grammar('dialect', parent_ids=['base'], start='expr')
    stmt = _simple(name='stmt', spec='SKIP')
    expr = _complex(name='expr', grammar_id='base', spec='term', action='return p[0]')
    grammars = [base, dialect]
    verify = patch.object(
        GrammarEvent,
        '_verify_start_resolves',
        side_effect=AssertionError('grammar event must not resolve starts'),
    )

    production_service, grammar_service = _services(
        productions=[stmt, expr],
        grammars=grammars,
    )
    rename_patch, rename_calls = _spy(ComplexProductionRuleAggregate, 'rename')
    with verify, rename_patch, pytest.raises(TiferetError) as caught:
        _handle(
            RenameProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
            new_name='factor',
        )
    assert caught.value.error_code == a.grammar.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['grammar_id'] == 'dialect'
    assert caught.value.kwargs['start'] == 'expr'
    assert rename_calls == []
    assert expr.name == 'expr'
    assert expr.grammar_id == 'base'
    assert expr.action == 'return p[0]'
    _assert_unwritten(production_service)

    expr = _complex(name='expr', grammar_id='base', spec='term', action='return p[0]')
    production_service, grammar_service = _services(
        productions=[stmt, expr],
        grammars=grammars,
    )
    reassign_patch, reassign_calls = _spy(
        ComplexProductionRuleAggregate,
        'reassign_grammar',
    )
    with verify, reassign_patch, pytest.raises(TiferetError) as caught:
        _handle(
            ReassignProductionGrammar,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
            new_grammar_id='outside',
        )
    assert caught.value.error_code == a.grammar.GRAMMAR_START_NOT_FOUND_ID
    assert caught.value.kwargs['grammar_id'] == 'dialect'
    assert reassign_calls == []
    assert expr.grammar_id == 'base'
    assert expr.name == 'expr'
    _assert_unwritten(production_service)
    grammar_service.exists.assert_not_called()

# ** test: rename_and_reassign_success
def test_rename_and_reassign_success():
    '''
    Rename or reassign in place when every persisted start still resolves.
    '''

    before = _simple(name='stmt', spec='SKIP')
    target = _complex(action='return p[1]')
    after = _simple(name='factor', spec='NUMBER')
    grammars = [_grammar('base', start='stmt')]
    production_service, grammar_service = _services(
        productions=[before, target, after],
        grammars=grammars,
    )
    seen = {}
    rename_patch, rename_calls = _spy(ComplexProductionRuleAggregate, 'rename')
    with rename_patch, _watch_assert(seen):
        result = _handle(
            RenameProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
            new_name='term_expr',
        )

    projected = seen['productions'][1]
    assert seen['productions'][0] is before
    assert projected is not target
    assert type(projected) is ComplexProductionRuleAggregate
    assert projected.name == 'term_expr'
    assert projected.grammar_id == 'base'
    assert projected.spec == 'term'
    assert projected.action == 'return p[1]'
    assert seen['productions'][2] is after
    assert seen['grammars'] is grammar_service.list.return_value
    assert result is target
    assert rename_calls == [(target, ('term_expr',))]
    assert target.name == 'term_expr'
    assert target.grammar_id == 'base'
    assert target.spec == 'term'
    assert target.action == 'return p[1]'
    production_service.replace.assert_called_once_with('expr', 'base', 'term', target)
    production_service.save.assert_not_called()

    # The destination grammar does not need to be stored.
    target = _simple()
    production_service, grammar_service = _services(
        productions=[before, target, after],
        grammars=grammars,
    )
    seen = {}
    reassign_patch, reassign_calls = _spy(
        SimpleProductionRuleAggregate,
        'reassign_grammar',
    )
    with reassign_patch, _watch_assert(seen):
        result = _handle(
            ReassignProductionGrammar,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
            new_grammar_id='not-stored',
        )

    projected = seen['productions'][1]
    assert projected is not target
    assert type(projected) is SimpleProductionRuleAggregate
    assert projected.name == 'expr'
    assert projected.grammar_id == 'not-stored'
    assert projected.spec == 'term'
    assert not hasattr(projected, 'action')
    assert seen['productions'][0] is before
    assert seen['productions'][2] is after
    assert result is target
    assert reassign_calls == [(target, ('not-stored',))]
    assert target.name == 'expr'
    assert target.spec == 'term'
    assert target.grammar_id == 'not-stored'
    production_service.replace.assert_called_once_with('expr', 'base', 'term', target)
    production_service.save.assert_not_called()
    grammar_service.exists.assert_not_called()
    grammar_service.get.assert_not_called()

# ** test: catalogue_is_unmutated_until_assert_returns
def test_catalogue_is_unmutated_until_assert_returns():
    '''
    Leave the loaded aggregate unchanged until the start check returns.
    '''

    target = _complex()
    production_service, grammar_service = _services(
        productions=[_simple(name='stmt', spec='SKIP'), target],
        grammars=[_grammar('base', start='stmt')],
    )
    original = ProductionEvent._assert_starts_resolve
    seen = {}

    def wrapper(self, productions, grammars):
        seen['name'] = target.name
        seen['grammar_id'] = target.grammar_id
        seen['projected_name'] = productions[1].name
        seen['projected_is_target'] = productions[1] is target
        return original(self, productions, grammars)

    rename_patch, rename_calls = _spy(ComplexProductionRuleAggregate, 'rename')
    with rename_patch, patch.object(ProductionEvent, '_assert_starts_resolve', wrapper):
        _handle(
            RenameProduction,
            production_service,
            grammar_service,
            name='expr',
            grammar_id='base',
            spec='term',
            new_name='factor',
        )

    assert seen['name'] == 'expr'
    assert seen['grammar_id'] == 'base'
    assert seen['projected_name'] == 'factor'
    assert seen['projected_is_target'] is False
    assert rename_calls == [(target, ('factor',))]
    assert target.name == 'factor'

# ** test: required_parameters_fail_before_write
def test_required_parameters_fail_before_write():
    '''
    Reject an omitted, missing, or blank required parameter before save or delete.
    '''

    production_service, grammar_service = _services([_complex()])
    blanks = (None, '', '   ')

    for event_cls, required in _REQUIRED.items():
        with pytest.raises(TiferetError):
            _handle(event_cls, production_service, grammar_service)
        _assert_unwritten(production_service)

        for name in required:
            kwargs = {
                key: _VALID[key]
                for key in required
                if key != name
            }
            with pytest.raises(TiferetError):
                _handle(
                    event_cls,
                    production_service,
                    grammar_service,
                    **kwargs,
                )
            _assert_unwritten(production_service)

            for value in blanks:
                kwargs = {key: _VALID[key] for key in required}
                kwargs[name] = value
                with pytest.raises(TiferetError):
                    _handle(
                        event_cls,
                        production_service,
                        grammar_service,
                        **kwargs,
                    )
                _assert_unwritten(production_service)
