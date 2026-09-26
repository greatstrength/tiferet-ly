"""Tiferet Ly Token Event Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path
from unittest.mock import Mock, patch

# ** infra
import pytest

# ** app
import tiferet_ly.assets as assets
import tiferet_ly.events as events_package
from tiferet import DomainEvent, TiferetError
from tiferet_ly.domain.token import ComplexTokenRule, SimpleTokenRule, TokenRule
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
from tiferet_ly.mappers.core import NamedRuleAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)

# *** constants

# ** constant: token_events
_TOKEN_EVENTS = (
    AddToken,
    GetToken,
    ListTokens,
    RenameToken,
    ReassignTokenGrammar,
    SetTokenPattern,
    SetTokenAction,
    RemoveToken,
)

# ** constant: required_parameters
_REQUIRED = {
    AddToken: ('name', 'grammar_id', 'pattern'),
    GetToken: ('name', 'grammar_id'),
    RenameToken: ('name', 'grammar_id', 'new_name'),
    ReassignTokenGrammar: ('name', 'grammar_id', 'new_grammar_id'),
    SetTokenPattern: ('name', 'grammar_id', 'pattern'),
    SetTokenAction: ('name', 'grammar_id', 'action'),
    RemoveToken: ('name', 'grammar_id'),
}

# ** constant: valid_parameters
_VALID = {
    'name': 'PLUS',
    'grammar_id': 'g',
    'pattern': r'\+',
    'new_name': 'MINUS',
    'new_grammar_id': 'h',
    'action': 'return t',
}

# *** functions

# ** function: simple
def _simple(name: str = 'PLUS', grammar_id: str = 'g', pattern: str = r'\+') -> SimpleTokenRuleAggregate:
    '''
    Build a simple token aggregate.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :return: A simple token aggregate.
    :rtype: SimpleTokenRuleAggregate
    '''

    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
    )

# ** function: complex
def _complex(
        name: str = 'PLUS',
        grammar_id: str = 'g',
        pattern: str = r'\+',
        action: str = 'return t',
    ) -> ComplexTokenRuleAggregate:
    '''
    Build a complex token aggregate.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :param action: The action source.
    :type action: str
    :return: A complex token aggregate.
    :rtype: ComplexTokenRuleAggregate
    '''

    return ComplexTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
        action=action,
    )

# ** function: service
def _service(
        exists_pairs: set[tuple[str, str]] | None = None,
        gotten: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate | None = None,
        tokens: list | None = None,
    ) -> Mock:
    '''
    Build a mocked token service.

    :param exists_pairs: Pairs that ``exists`` reports as stored.
    :type exists_pairs: set[tuple[str, str]] | None
    :param gotten: The aggregate returned by ``get``, if any.
    :type gotten: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate | None
    :param tokens: The catalogue returned by ``list``.
    :type tokens: list | None
    :return: The token service mock.
    :rtype: Mock
    '''

    # Exists answers from the supplied pair set.
    present = exists_pairs or set()
    service = Mock()
    service.exists.side_effect = lambda name, grammar_id: (name, grammar_id) in present
    service.get.return_value = gotten
    service.list.return_value = list(tokens) if tokens is not None else []
    return service

# ** function: handle
def _handle(event_cls, token_service, **kwargs):
    '''
    Invoke a token event through the domain-event handle.

    :param event_cls: The event class to handle.
    :type event_cls: type
    :param token_service: The mocked token service.
    :type token_service: Mock
    :param kwargs: Event keyword arguments.
    :type kwargs: dict
    :return: The event result.
    :rtype: object
    '''

    return DomainEvent.handle(
        event_cls,
        dependencies={'token_service': token_service},
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
    Keep the token events on their module and the error ids on assets.
    '''

    # The base accepts only the token service.
    service = _service()
    assert issubclass(TokenEvent, DomainEvent)
    assert list(inspect.signature(TokenEvent.__init__).parameters) == [
        'self',
        'token_service',
    ]
    assert TokenEvent(service).token_service is service

    # Every concrete event extends that base and inherits the same constructor.
    for event_cls in _TOKEN_EVENTS:
        assert issubclass(event_cls, TokenEvent)
        assert event_cls.__module__ == 'tiferet_ly.events.token'
        assert list(inspect.signature(event_cls.__init__).parameters) == [
            'self',
            'token_service',
        ]
        assert not hasattr(events_package, event_cls.__name__)
    assert not hasattr(events_package, 'TokenEvent')

    # The package marker does not import the token event module.
    package_tree = ast.parse(Path(events_package.__file__).read_text())
    package_modules = _imported_modules(package_tree)
    assert not any(module.endswith('token') or '.token' in module for module in package_modules)
    imported_names = [
        alias.name
        for node in ast.walk(package_tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    ]
    for event_cls in (TokenEvent, *_TOKEN_EVENTS):
        assert event_cls.__name__ not in imported_names

    # The event module does not reach grammars, repositories, or PLY.
    event_tree = ast.parse(Path(inspect.getfile(TokenEvent)).read_text())
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

    # Error ids are reachable as a.error and are an ids section only.
    error_source = Path(assets.error.__file__).read_text()
    assert '# *** constants (ids)' in error_source
    assert '(models)' not in error_source
    assert '(groups)' not in error_source
    assert assets.error.TOKEN_ALREADY_EXISTS_ID == 'TOKEN_ALREADY_EXISTS'
    assert assets.error.TOKEN_NOT_FOUND_ID == 'TOKEN_NOT_FOUND'
    assert assets.error.TOKEN_ACTION_NOT_SUPPORTED_ID == 'TOKEN_ACTION_NOT_SUPPORTED'

    # This story does not add reader or precedence fields to the token models.
    for model in (TokenRule, SimpleTokenRule, ComplexTokenRule):
        for field_name in ('subgrammar', 't_error', 'precedence', 'associativity'):
            assert field_name not in model.model_fields

# ** test: add_token_already_exists
def test_add_token_already_exists():
    '''
    Reject a stored pair before save.
    '''

    service = _service(exists_pairs={('PLUS', 'g')})

    with pytest.raises(TiferetError) as caught:
        _handle(
            AddToken,
            service,
            name='PLUS',
            grammar_id='g',
            pattern=r'\+',
        )

    assert caught.value.error_code == assets.error.TOKEN_ALREADY_EXISTS_ID
    assert caught.value.kwargs['name'] == 'PLUS'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert 'Token already exists: PLUS in grammar g.' in str(caught.value)
    service.save.assert_not_called()

# ** test: add_token_simple_without_grammar
def test_add_token_simple_without_grammar():
    '''
    Save a simple token when action is omitted or None, even if the grammar is absent.
    '''

    # The constructor does not accept a grammar service.
    with pytest.raises(TypeError):
        AddToken(_service(), Mock())

    for action in (None,):
        service = _service()
        result = _handle(
            AddToken,
            service,
            name='PLUS',
            grammar_id='missing-grammar',
            pattern=r'\+',
            action=action,
        )
        saved = service.save.call_args.args[0]
        assert result is saved
        assert isinstance(result, SimpleTokenRuleAggregate)
        assert not isinstance(result, ComplexTokenRuleAggregate)
        assert result.name == 'PLUS'
        assert result.grammar_id == 'missing-grammar'
        assert result.pattern == r'\+'

    # Omitted action is the same simple aggregate.
    service = _service()
    result = _handle(
        AddToken,
        service,
        name='PLUS',
        grammar_id='missing-grammar',
        pattern=r'\+',
    )
    assert isinstance(result, SimpleTokenRuleAggregate)
    assert result is service.save.call_args.args[0]

# ** test: add_token_complex
def test_add_token_complex():
    '''
    Save a complex token when action is a string.
    '''

    service = _service()
    result = _handle(
        AddToken,
        service,
        name='PLUS',
        grammar_id='g',
        pattern=r'\+',
        action='return t',
    )

    assert isinstance(result, ComplexTokenRuleAggregate)
    assert result is service.save.call_args.args[0]
    assert result.action == 'return t'
    assert result.grammar_id == 'g'

# ** test: add_token_same_name_other_grammar
def test_add_token_same_name_other_grammar():
    '''
    Allow the same name under a different grammar.
    '''

    service = _service(exists_pairs={('PLUS', 'other')})
    result = _handle(
        AddToken,
        service,
        name='PLUS',
        grammar_id='g',
        pattern=r'\+',
    )

    assert isinstance(result, SimpleTokenRuleAggregate)
    assert result.grammar_id == 'g'
    service.exists.assert_called_with('PLUS', 'g')
    service.save.assert_called_once()

# ** test: get_token
def test_get_token():
    '''
    Return the loaded aggregate, or reject a missing pair.
    '''

    stored = _complex()
    service = _service(gotten=stored)
    assert _handle(GetToken, service, name='PLUS', grammar_id='g') is stored
    service.get.assert_called_with('PLUS', 'g')

    missing = _service(gotten=None)
    with pytest.raises(TiferetError) as caught:
        _handle(GetToken, missing, name='PLUS', grammar_id='g')

    assert caught.value.error_code == assets.error.TOKEN_NOT_FOUND_ID
    assert caught.value.kwargs['name'] == 'PLUS'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert 'Token not found: PLUS in grammar g.' in str(caught.value)
    missing.save.assert_not_called()

# ** test: list_tokens_keeps_order
def test_list_tokens_keeps_order():
    '''
    Return the service list unchanged, including mixed grammars.
    '''

    tokens = [_simple('PLUS', 'g'), _simple('PLUS', 'h'), _complex('NUMBER', 'g')]
    service = _service(tokens=tokens)

    result = _handle(ListTokens, service, grammar_id='g')

    assert result == tokens
    assert [token.grammar_id for token in result] == ['g', 'h', 'g']
    service.list.assert_called_once_with()
    service.exists.assert_not_called()
    service.get.assert_not_called()
    service.save.assert_not_called()

# ** test: rename_token
def test_rename_token():
    '''
    Rename a stored token, including a rename to the same name.
    '''

    # A missing pair is not saved.
    missing = _service(gotten=None)
    with pytest.raises(TiferetError) as caught:
        _handle(
            RenameToken,
            missing,
            name='PLUS',
            grammar_id='g',
            new_name='MINUS',
        )
    assert caught.value.error_code == assets.error.TOKEN_NOT_FOUND_ID
    missing.save.assert_not_called()

    # A different token holding the new pair blocks the write.
    taken = _service(
        exists_pairs={('MINUS', 'g')},
        gotten=_simple(),
    )
    with pytest.raises(TiferetError) as caught:
        _handle(
            RenameToken,
            taken,
            name='PLUS',
            grammar_id='g',
            new_name='MINUS',
        )
    assert caught.value.error_code == assets.error.TOKEN_ALREADY_EXISTS_ID
    assert caught.value.kwargs['name'] == 'MINUS'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert taken.get.return_value.name == 'PLUS'
    taken.save.assert_not_called()

    # A free new name is renamed and saved.
    token = _simple()
    service = _service(gotten=token)
    rename_patch, rename_calls = _spy(NamedRuleAggregate, 'rename')
    with rename_patch:
        result = _handle(
            RenameToken,
            service,
            name='PLUS',
            grammar_id='g',
            new_name='MINUS',
        )
    assert result is token
    assert rename_calls == [('MINUS',)]
    assert token.name == 'MINUS'
    assert service.save.call_args.args[0] is token

    # The same name is not treated as a duplicate, even if exists would say so.
    same = _simple()
    same_service = _service(exists_pairs={('PLUS', 'g')}, gotten=same)
    same_patch, same_calls = _spy(NamedRuleAggregate, 'rename')
    with same_patch:
        result = _handle(
            RenameToken,
            same_service,
            name='PLUS',
            grammar_id='g',
            new_name='PLUS',
        )
    assert result is same
    assert same_calls == [('PLUS',)]
    same_service.exists.assert_not_called()
    same_service.save.assert_called_once_with(same)

# ** test: reassign_token_grammar
def test_reassign_token_grammar():
    '''
    Move a token to another grammar id, including a no-op reassignment.
    '''

    missing = _service(gotten=None)
    with pytest.raises(TiferetError) as caught:
        _handle(
            ReassignTokenGrammar,
            missing,
            name='PLUS',
            grammar_id='g',
            new_grammar_id='h',
        )
    assert caught.value.error_code == assets.error.TOKEN_NOT_FOUND_ID
    missing.save.assert_not_called()

    taken = _service(
        exists_pairs={('PLUS', 'h')},
        gotten=_simple(),
    )
    with pytest.raises(TiferetError) as caught:
        _handle(
            ReassignTokenGrammar,
            taken,
            name='PLUS',
            grammar_id='g',
            new_grammar_id='h',
        )
    assert caught.value.error_code == assets.error.TOKEN_ALREADY_EXISTS_ID
    assert caught.value.kwargs['name'] == 'PLUS'
    assert caught.value.kwargs['grammar_id'] == 'h'
    assert taken.get.return_value.grammar_id == 'g'
    taken.save.assert_not_called()

    # The destination need not name a stored grammar.
    token = _simple()
    service = _service(gotten=token)
    reassign_patch, reassign_calls = _spy(NamedRuleAggregate, 'reassign_grammar')
    with reassign_patch:
        result = _handle(
            ReassignTokenGrammar,
            service,
            name='PLUS',
            grammar_id='g',
            new_grammar_id='missing-grammar',
        )
    assert result is token
    assert reassign_calls == [('missing-grammar',)]
    assert token.grammar_id == 'missing-grammar'
    assert service.save.call_args.args[0] is token

    # The same grammar is not treated as a duplicate.
    same = _simple()
    same_service = _service(exists_pairs={('PLUS', 'g')}, gotten=same)
    same_patch, same_calls = _spy(NamedRuleAggregate, 'reassign_grammar')
    with same_patch:
        result = _handle(
            ReassignTokenGrammar,
            same_service,
            name='PLUS',
            grammar_id='g',
            new_grammar_id='g',
        )
    assert result is same
    assert same_calls == [('g',)]
    same_service.exists.assert_not_called()
    same_service.save.assert_called_once_with(same)

# ** test: set_token_pattern
def test_set_token_pattern():
    '''
    Replace a stored pattern, and refuse a missing pair.
    '''

    missing = _service(gotten=None)
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetTokenPattern,
            missing,
            name='PLUS',
            grammar_id='g',
            pattern='[0-9]+',
        )
    assert caught.value.error_code == assets.error.TOKEN_NOT_FOUND_ID
    missing.save.assert_not_called()

    token = _simple()
    service = _service(gotten=token)
    pattern_patch, pattern_calls = _spy(SimpleTokenRuleAggregate, 'set_pattern')
    with pattern_patch:
        result = _handle(
            SetTokenPattern,
            service,
            name='PLUS',
            grammar_id='g',
            pattern='[0-9]+',
        )
    assert result is token
    assert pattern_calls == [('[0-9]+',)]
    assert token.pattern == '[0-9]+'
    assert service.save.call_args.args[0] is token

# ** test: set_token_action
def test_set_token_action():
    '''
    Replace a complex action, and refuse a missing or simple token.
    '''

    missing = _service(gotten=None)
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetTokenAction,
            missing,
            name='PLUS',
            grammar_id='g',
            action='return t',
        )
    assert caught.value.error_code == assets.error.TOKEN_NOT_FOUND_ID
    missing.save.assert_not_called()

    simple = _simple()
    simple_service = _service(gotten=simple)
    with pytest.raises(TiferetError) as caught:
        _handle(
            SetTokenAction,
            simple_service,
            name='PLUS',
            grammar_id='g',
            action='return t',
        )
    assert caught.value.error_code == assets.error.TOKEN_ACTION_NOT_SUPPORTED_ID
    assert caught.value.kwargs['name'] == 'PLUS'
    assert caught.value.kwargs['grammar_id'] == 'g'
    assert 'Token action is not supported for simple token PLUS in grammar g.' in str(caught.value)
    simple_service.save.assert_not_called()

    token = _complex(action='return t')
    service = _service(gotten=token)
    action_patch, action_calls = _spy(ComplexTokenRuleAggregate, 'set_action')
    with action_patch:
        result = _handle(
            SetTokenAction,
            service,
            name='PLUS',
            grammar_id='g',
            action='return None',
        )
    assert result is token
    assert isinstance(result, ComplexTokenRuleAggregate)
    assert action_calls == [('return None',)]
    assert token.action == 'return None'
    assert service.save.call_args.args[0] is token

# ** test: remove_token
def test_remove_token():
    '''
    Delete and return the pair whether or not it is stored.
    '''

    absent = _service()
    assert _handle(RemoveToken, absent, name='PLUS', grammar_id='g') == ('PLUS', 'g')
    absent.delete.assert_called_once_with('PLUS', 'g')
    absent.exists.assert_not_called()
    absent.get.assert_not_called()

    present = _service(exists_pairs={('PLUS', 'g')}, gotten=_simple())
    assert _handle(RemoveToken, present, name='PLUS', grammar_id='g') == ('PLUS', 'g')
    present.delete.assert_called_once_with('PLUS', 'g')
    present.save.assert_not_called()

# ** test: required_parameters_fail_before_write
def test_required_parameters_fail_before_write():
    '''
    Reject an omitted, missing, or blank required parameter before save or delete.
    '''

    service = _service(gotten=_complex())
    blanks = (None, '', '   ')

    for event_cls, required in _REQUIRED.items():
        with pytest.raises(TiferetError):
            _handle(event_cls, service)
        service.save.assert_not_called()
        service.delete.assert_not_called()

        for name in required:
            kwargs = {
                key: _VALID[key]
                for key in required
                if key != name
            }
            with pytest.raises(TiferetError):
                _handle(event_cls, service, **kwargs)
            service.save.assert_not_called()
            service.delete.assert_not_called()

            for value in blanks:
                kwargs = {key: _VALID[key] for key in required}
                kwargs[name] = value
                with pytest.raises(TiferetError):
                    _handle(event_cls, service, **kwargs)
                service.save.assert_not_called()
                service.delete.assert_not_called()
