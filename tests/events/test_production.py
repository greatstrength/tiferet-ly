"""Tiferet Ly Production Event Tests"""

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
import tiferet_ly.events.production as production_events
from tiferet import DomainEvent, TiferetError
from tiferet_ly.events.production import (
    PRODUCTION_ACTION_NOT_SUPPORTED_ID,
    PRODUCTION_ALREADY_EXISTS_ID,
    PRODUCTION_NOT_FOUND_ID,
    AddProduction,
    GetProductions,
    ListProductions,
    ProductionEvent,
    SetProductionAction,
    SetProductionSpec,
)
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)

# *** constants

# ** constant: production_events
_PRODUCTION_EVENTS = (
    AddProduction,
    ListProductions,
    GetProductions,
    SetProductionSpec,
    SetProductionAction,
)

# ** constant: required_parameters
_REQUIRED = {
    AddProduction: ('name', 'grammar_id', 'spec'),
    GetProductions: ('name', 'grammar_id'),
    SetProductionSpec: ('name', 'grammar_id', 'spec', 'new_spec'),
    SetProductionAction: ('name', 'grammar_id', 'spec', 'action'),
}

# ** constant: valid_parameters
_VALID = {
    'name': 'expr',
    'grammar_id': 'g',
    'spec': 'term',
    'new_spec': 'term PLUS factor',
    'action': 'return p[0]',
}

# ** constant: absent_events
_ABSENT_EVENTS = (
    'GetProduction',
    'RemoveProduction',
    'RenameProduction',
    'ReassignProductionGrammar',
)

# *** functions

# ** function: simple
def _simple(
        name: str = 'expr',
        grammar_id: str = 'g',
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
        grammar_id: str = 'g',
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

# ** function: service
def _service(productions: list | None = None) -> Mock:
    '''
    Build a mocked production service.

    :param productions: The catalogue returned by ``list``.
    :type productions: list | None
    :return: The production service mock.
    :rtype: Mock
    '''

    # Listing is the only read these events are allowed to use.
    service = Mock()
    service.list.return_value = list(productions) if productions is not None else []
    return service

# ** function: handle
def _handle(event_cls, production_service, **kwargs):
    '''
    Invoke a production event through the domain-event handle.

    :param event_cls: The event class to handle.
    :type event_cls: type
    :param production_service: The mocked production service.
    :type production_service: Mock
    :param kwargs: Event keyword arguments.
    :type kwargs: dict
    :return: The event result.
    :rtype: object
    '''

    return DomainEvent.handle(
        event_cls,
        dependencies={'production_service': production_service},
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
        calls.append(args)
        return original(self, *args, **kwargs)

    return patch.object(cls, method_name, wrapper), calls

# *** tests

# ** test: module_surface
def test_module_surface():
    '''
    Keep ordinary production events on their module and out of the package export.
    '''

    # The base accepts only the production service.
    service = _service()
    assert issubclass(ProductionEvent, DomainEvent)
    assert list(inspect.signature(ProductionEvent.__init__).parameters) == [
        'self',
        'production_service',
    ]
    assert ProductionEvent(service).production_service is service

    # Every ordinary event extends that base and inherits the same constructor.
    for event_cls in _PRODUCTION_EVENTS:
        assert issubclass(event_cls, ProductionEvent)
        assert event_cls.__module__ == 'tiferet_ly.events.production'
        assert list(inspect.signature(event_cls.__init__).parameters) == [
            'self',
            'production_service',
        ]
        if event_cls is not ListProductions:
            execute_param = inspect.signature(event_cls.execute).parameters['grammar_id']
            assert execute_param.default is inspect.Parameter.empty
        assert not hasattr(events_package, event_cls.__name__)
    assert not hasattr(events_package, 'ProductionEvent')

    # Pair-only and start-safe writes are not this story.
    for name in _ABSENT_EVENTS:
        assert not hasattr(production_events, name)
        assert not hasattr(events_package, name)
    assert not hasattr(ProductionEvent, '_assert_starts_resolve')

    # The package marker does not import or bind the production events.
    package_tree = ast.parse(Path(events_package.__file__).read_text())
    package_modules = _imported_modules(package_tree)
    assert not any(
        module.endswith('production') or '.production' in module
        for module in package_modules
    )
    imported_names = [
        alias.name
        for node in ast.walk(package_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    for event_cls in (ProductionEvent, *_PRODUCTION_EVENTS):
        assert event_cls.__name__ not in imported_names

    # The event module does not reach grammars, repositories, or PLY.
    event_tree = ast.parse(Path(inspect.getfile(ProductionEvent)).read_text())
    event_source = Path(inspect.getfile(ProductionEvent)).read_text()
    for module in _imported_modules(event_tree):
        assert module != 'ply' and not module.startswith('ply.')
        assert not module.startswith('tiferet_ly.repos')
        assert 'GrammarService' not in module
        assert 'GrammarRuleSelector' not in module
    event_names = [
        alias.name
        for node in ast.walk(event_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    assert 'GrammarService' not in event_names
    assert 'GrammarRuleSelector' not in event_names
    assert 'DomainEvent' in event_names
    assert '_assert_starts_resolve' not in event_source

    # Error identifiers live in this module, not as a package export.
    assert production_events.PRODUCTION_ALREADY_EXISTS_ID == 'PRODUCTION_ALREADY_EXISTS'
    assert production_events.PRODUCTION_NOT_FOUND_ID == 'PRODUCTION_NOT_FOUND'
    assert production_events.PRODUCTION_ACTION_NOT_SUPPORTED_ID == 'PRODUCTION_ACTION_NOT_SUPPORTED'
    assert PRODUCTION_ALREADY_EXISTS_ID == 'PRODUCTION_ALREADY_EXISTS'
    assert PRODUCTION_NOT_FOUND_ID == 'PRODUCTION_NOT_FOUND'
    assert PRODUCTION_ACTION_NOT_SUPPORTED_ID == 'PRODUCTION_ACTION_NOT_SUPPORTED'

# ** test: add_production_appends_alternative
def test_add_production_appends_alternative():
    '''
    Save a new spec for an existing name and grammar.
    '''

    service = _service([_simple(spec='term')])
    result = _handle(
        AddProduction,
        service,
        name='expr',
        grammar_id='g',
        spec='term PLUS factor',
    )

    assert isinstance(result, SimpleProductionRuleAggregate)
    assert result is service.save.call_args.args[0]
    assert result.name == 'expr'
    assert result.grammar_id == 'g'
    assert result.spec == 'term PLUS factor'
    service.list.assert_called_once_with()
    service.exists.assert_not_called()
    service.get.assert_not_called()
    service.save.assert_called_once()

# ** test: add_production_already_exists
def test_add_production_already_exists():
    '''
    Reject a stored triple before save.
    '''

    service = _service([_simple(), _complex(name='factor', spec='NUMBER')])

    with pytest.raises(TiferetError) as caught:
        _handle(
            AddProduction,
            service,
            name='expr',
            grammar_id='g',
            spec='term',
        )

    assert caught.value.error_code == PRODUCTION_ALREADY_EXISTS_ID
    assert caught.value.kwargs['name'] == 'expr'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert caught.value.kwargs['spec'] == 'term'
    assert 'Production already exists: expr in grammar g with spec term.' in str(caught.value)
    service.save.assert_not_called()
    service.exists.assert_not_called()
    service.get.assert_not_called()

# ** test: add_production_scans_without_grammar
def test_add_production_scans_without_grammar():
    '''
    Scan the catalogue and save even when the grammar id names no grammar.
    '''

    # The constructor does not accept a grammar service.
    with pytest.raises(TypeError):
        AddProduction(_service(), Mock())

    service = _service()
    result = _handle(
        AddProduction,
        service,
        name='expr',
        grammar_id='missing-grammar',
        spec='term',
    )

    assert result.grammar_id == 'missing-grammar'
    assert result is service.save.call_args.args[0]
    service.list.assert_called_once_with()
    service.exists.assert_not_called()
    service.get.assert_not_called()

# ** test: add_production_simple_or_complex
def test_add_production_simple_or_complex():
    '''
    Save a simple production when action is omitted or None, and a complex one when it is a string.
    '''

    for action in (None,):
        service = _service()
        result = _handle(
            AddProduction,
            service,
            name='expr',
            grammar_id='g',
            spec='term',
            action=action,
        )
        saved = service.save.call_args.args[0]
        assert result is saved
        assert isinstance(result, SimpleProductionRuleAggregate)
        assert not isinstance(result, ComplexProductionRuleAggregate)

    # Omitted action is the same simple aggregate.
    service = _service()
    result = _handle(
        AddProduction,
        service,
        name='expr',
        grammar_id='g',
        spec='term',
    )
    assert isinstance(result, SimpleProductionRuleAggregate)
    assert result is service.save.call_args.args[0]

    # A string action, including a blank one, is complex. Blank is not verified.
    service = _service()
    result = _handle(
        AddProduction,
        service,
        name='expr',
        grammar_id='g',
        spec='term',
        action='return p[0]',
    )
    assert isinstance(result, ComplexProductionRuleAggregate)
    assert result is service.save.call_args.args[0]
    assert result.action == 'return p[0]'

# ** test: list_productions_keeps_order
def test_list_productions_keeps_order():
    '''
    Return the service list unchanged, including mixed grammars and repeated names.
    '''

    productions = [
        _simple('expr', 'g', 'term'),
        _simple('expr', 'g', 'term PLUS factor'),
        _simple('expr', 'h', 'term'),
        _complex('factor', 'g', 'NUMBER'),
    ]
    service = _service(productions)

    result = _handle(ListProductions, service, grammar_id='g')

    assert result == productions
    assert [(row.name, row.grammar_id, row.spec) for row in result] == [
        ('expr', 'g', 'term'),
        ('expr', 'g', 'term PLUS factor'),
        ('expr', 'h', 'term'),
        ('factor', 'g', 'NUMBER'),
    ]
    service.list.assert_called_once_with()
    service.exists.assert_not_called()
    service.get.assert_not_called()
    service.save.assert_not_called()

# ** test: get_productions
def test_get_productions():
    '''
    Return every alternative of a pair in declared order, or reject an empty filter.
    '''

    first = _simple(spec='term')
    second = _complex(spec='term PLUS factor')
    catalogue = [
        _simple(name='factor', spec='NUMBER'),
        first,
        _simple(grammar_id='h', spec='term'),
        second,
    ]
    service = _service(catalogue)

    result = _handle(GetProductions, service, name='expr', grammar_id='g')

    assert result == [first, second]
    service.get.assert_not_called()
    service.exists.assert_not_called()
    service.list.assert_called_once_with()

    missing = _service([_simple(grammar_id='h')])
    with pytest.raises(TiferetError) as caught:
        _handle(GetProductions, missing, name='expr', grammar_id='g')

    assert caught.value.error_code == PRODUCTION_NOT_FOUND_ID
    assert caught.value.kwargs['name'] == 'expr'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert 'spec' not in caught.value.kwargs
    assert 'Production not found: expr in grammar g.' in str(caught.value)
    missing.get.assert_not_called()
    missing.save.assert_not_called()

# ** test: set_production_spec
def test_set_production_spec():
    '''
    Replace one specification by its old triple, and refuse a missing or repeated triple.
    '''

    # The constructor does not accept a grammar service.
    with pytest.raises(TypeError):
        SetProductionSpec(_service(), Mock())

    missing = _service([_simple(spec='other')])
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetProductionSpec,
            missing,
            name='expr',
            grammar_id='g',
            spec='term',
            new_spec='term PLUS factor',
        )
    assert caught.value.error_code == PRODUCTION_NOT_FOUND_ID
    assert caught.value.kwargs['name'] == 'expr'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert caught.value.kwargs['spec'] == 'term'
    assert 'Production not found: expr in grammar g with spec term.' in str(caught.value)
    missing.save.assert_not_called()
    missing.replace.assert_not_called()
    missing.exists.assert_not_called()
    missing.get.assert_not_called()

    repeated = _service([_simple(), _simple()])
    spec_patch, spec_calls = _spy(SimpleProductionRuleAggregate, 'set_spec')
    with spec_patch, pytest.raises(TiferetError) as caught:
        _handle(
            SetProductionSpec,
            repeated,
            name='expr',
            grammar_id='g',
            spec='term',
            new_spec='term PLUS factor',
        )
    assert caught.value.error_code == PRODUCTION_ALREADY_EXISTS_ID
    assert caught.value.kwargs['spec'] == 'term'
    assert 'Production already exists: expr in grammar g with spec term.' in str(caught.value)
    assert spec_calls == []
    assert repeated.list.return_value[0].spec == 'term'
    repeated.save.assert_not_called()
    repeated.replace.assert_not_called()

    row = _simple()
    service = _service([_simple(name='factor'), row, _simple(grammar_id='h')])
    spec_patch, spec_calls = _spy(SimpleProductionRuleAggregate, 'set_spec')
    with spec_patch:
        result = _handle(
            SetProductionSpec,
            service,
            name='expr',
            grammar_id='g',
            spec='term',
            new_spec='term PLUS factor',
        )
    assert result is row
    assert spec_calls == [('term PLUS factor',)]
    assert row.spec == 'term PLUS factor'
    assert row.name == 'expr'
    assert row.grammar_id == 'g'
    service.replace.assert_called_once_with('expr', 'g', 'term', row)
    service.save.assert_not_called()
    service.exists.assert_not_called()
    service.get.assert_not_called()

# ** test: set_production_action
def test_set_production_action():
    '''
    Replace a complex action, and refuse a missing, repeated, or simple row.
    '''

    missing = _service([_complex(spec='other')])
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetProductionAction,
            missing,
            name='expr',
            grammar_id='g',
            spec='term',
            action='return p[0]',
        )
    assert caught.value.error_code == PRODUCTION_NOT_FOUND_ID
    assert caught.value.kwargs['spec'] == 'term'
    missing.save.assert_not_called()
    missing.replace.assert_not_called()

    repeated = _service([_complex(), _complex(action='return None')])
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetProductionAction,
            repeated,
            name='expr',
            grammar_id='g',
            spec='term',
            action='return p[1]',
        )
    assert caught.value.error_code == PRODUCTION_ALREADY_EXISTS_ID
    assert repeated.list.return_value[0].action == 'return p[0]'
    repeated.save.assert_not_called()
    repeated.replace.assert_not_called()

    simple = _simple()
    simple_service = _service([simple])
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetProductionAction,
            simple_service,
            name='expr',
            grammar_id='g',
            spec='term',
            action='return p[0]',
        )
    assert caught.value.error_code == PRODUCTION_ACTION_NOT_SUPPORTED_ID
    assert caught.value.kwargs['name'] == 'expr'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert caught.value.kwargs['spec'] == 'term'
    assert (
        'Production action is not supported for simple production '
        'expr in grammar g with spec term.'
    ) in str(caught.value)
    simple_service.save.assert_not_called()
    simple_service.replace.assert_not_called()

    row = _complex(action='return p[0]')
    service = _service([row])
    action_patch, action_calls = _spy(ComplexProductionRuleAggregate, 'set_action')
    with action_patch:
        result = _handle(
            SetProductionAction,
            service,
            name='expr',
            grammar_id='g',
            spec='term',
            action='return None',
        )
    assert result is row
    assert isinstance(result, ComplexProductionRuleAggregate)
    assert action_calls == [('return None',)]
    assert row.action == 'return None'
    assert service.save.call_args.args[0] is row
    service.save.assert_called_once_with(row)
    service.replace.assert_not_called()
    service.exists.assert_not_called()
    service.get.assert_not_called()

# ** test: required_parameters_fail_before_write
def test_required_parameters_fail_before_write():
    '''
    Reject an omitted, missing, or blank required parameter before save or replace.
    '''

    service = _service([_complex()])
    blanks = (None, '', '   ')

    for event_cls, required in _REQUIRED.items():
        with pytest.raises(TiferetError):
            _handle(event_cls, service)
        service.save.assert_not_called()
        service.replace.assert_not_called()

        for name in required:
            kwargs = {
                key: _VALID[key]
                for key in required
                if key != name
            }
            with pytest.raises(TiferetError):
                _handle(event_cls, service, **kwargs)
            service.save.assert_not_called()
            service.replace.assert_not_called()

            for value in blanks:
                kwargs = {key: _VALID[key] for key in required}
                kwargs[name] = value
                with pytest.raises(TiferetError):
                    _handle(event_cls, service, **kwargs)
                service.save.assert_not_called()
                service.replace.assert_not_called()
