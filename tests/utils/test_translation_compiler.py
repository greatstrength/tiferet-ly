"""Tiferet Ly Action Compiler Tests"""

# *** imports

# ** core
import ast
from pathlib import Path
from types import SimpleNamespace

# ** infra
import pytest

# ** app
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.translation import (
    ACTION_COMPILATION_FAILED_ID,
    RULE_PATTERN_INVALID_ID,
)
from tiferet_ly.utils.translation import RuleTranslator

# *** functions

# ** function: imported_modules
def imported_modules(path: Path) -> set[str]:
    '''
    Collect imported module names from a Python source file.

    :param path: The source file to inspect.
    :type path: Path
    :return: Imported module names, including dotted paths.
    :rtype: set[str]
    '''

    # Parse the source without importing it.
    tree = ast.parse(path.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    # Return the imported module names.
    return modules

# *** testers

# ** tester: test_translation_compiler
@use_tester(
    type='generic',
    target_cls=RuleTranslator,
)
class TestTranslationCompiler:
    '''
    Tests for the shared action compiler and its error identifiers.
    '''

    # * test: error_identifiers
    def test_error_identifiers(self, test_ctx, session):
        '''
        Expose the two translation error identifiers.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The identifiers match the published values.
        assert ACTION_COMPILATION_FAILED_ID == 'ACTION_COMPILATION_FAILED'
        assert RULE_PATTERN_INVALID_ID == 'RULE_PATTERN_INVALID'

    # * test: compile_action_runs_declared_action
    def test_compile_action_runs_declared_action(self, test_ctx, session):
        '''
        Return a named callable whose docstring is the pattern.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile a valid token action.
        compiled = RuleTranslator._compile_action(
            'NUMBER',
            r'\d+',
            't.value = int(t.value)',
        )

        # The function is named from the rule and carries the pattern.
        assert compiled.__name__ == 'NUMBER'
        assert compiled.__doc__ == r'\d+'

        # Calling it with one positional argument performs the action.
        token = SimpleNamespace(value='3')
        compiled(token)
        assert token.value == 3

    # * test: invalid_pattern_does_not_compile_action
    def test_invalid_pattern_does_not_compile_action(self, test_ctx, session):
        '''
        Raise a pattern error before compiling or executing the action.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An invalid pattern wins even when the action is not valid Python.
        with pytest.raises(ServiceError) as raised:
            RuleTranslator._compile_action('BAD', '[', 'def')

        # The error names the rule and is not an action-compilation failure.
        error = raised.value
        assert error.error_code == RULE_PATTERN_INVALID_ID
        assert error.kwargs['rule_name'] == 'BAD'
        assert error.error_code != ACTION_COMPILATION_FAILED_ID

    # * test: syntax_error_names_rule_and_cause
    def test_syntax_error_names_rule_and_cause(self, test_ctx, session):
        '''
        Raise an action-compilation error that includes the SyntaxError.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A valid pattern with invalid action source fails compilation.
        with pytest.raises(ServiceError) as raised:
            RuleTranslator._compile_action('BAD', 'a', 'def')

        # The error names the rule and carries the original SyntaxError.
        error = raised.value
        assert error.error_code == ACTION_COMPILATION_FAILED_ID
        assert error.kwargs['rule_name'] == 'BAD'
        assert isinstance(error.__cause__, SyntaxError)
        assert 'SyntaxError' in error.kwargs['syntax_error']

    # * test: successful_calls_are_independent
    def test_successful_calls_are_independent(self, test_ctx, session):
        '''
        Return a distinct function object on each successful call.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile the same declaration twice.
        first = RuleTranslator._compile_action(
            'NUMBER',
            r'\d+',
            't.value = int(t.value)',
        )
        second = RuleTranslator._compile_action(
            'NUMBER',
            r'\d+',
            't.value = int(t.value)',
        )

        # The functions are independent and behave the same.
        assert first is not second
        assert first.__doc__ == second.__doc__
        left = SimpleNamespace(value='3')
        right = SimpleNamespace(value='4')
        first(left)
        second(right)
        assert left.value == 3
        assert right.value == 4

    # * test: does_not_import_ply_or_events
    def test_does_not_import_ply_or_events(self, test_ctx, session):
        '''
        Keep PLY and domain events out of the compiler and this test.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Inspect the compiler module and this test file.
        root = Path(__file__).parents[2]
        compiler = imported_modules(root / 'tiferet_ly' / 'utils' / 'translation.py')
        test_modules = imported_modules(Path(__file__))

        # Neither file imports ply or tiferet_ly.events.
        for modules in (compiler, test_modules):
            assert 'ply' not in modules
            assert not any(name == 'ply' or name.startswith('ply.') for name in modules)
            assert 'tiferet_ly.events' not in modules
