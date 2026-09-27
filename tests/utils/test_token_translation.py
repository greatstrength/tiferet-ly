"""Tiferet Ly Token Translation Tests"""

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
from tiferet_ly.assets.translation import RULE_PATTERN_INVALID_ID
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
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

# ** tester: test_token_translation
@use_tester(
    type='generic',
    target_cls=RuleTranslator,
)
class TestTokenTranslation:
    '''
    Tests for token translation and ordered token-name derivation.
    '''

    # * test: simple_token_returns_name_and_pattern
    def test_simple_token_returns_name_and_pattern(self, test_ctx, session):
        '''
        Return the reader name and the pattern text unchanged.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A simple PLUS token keeps the declared pattern, including '+'.
        rule = SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='arithmetic',
            pattern='+',
        )
        translated = RuleTranslator.translate_token_rule(rule)

        # The attribute name is prefixed and the pattern object is unchanged.
        assert translated == ('t_PLUS', '+')
        assert translated[1] is rule.pattern

    # * test: complex_token_returns_compiled_action
    def test_complex_token_returns_compiled_action(self, test_ctx, session):
        '''
        Return a callable whose docstring is the pattern and whose call acts.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Translate a complex token through the shared compiler.
        rule = ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern=r'\d+',
            action='t.value = int(t.value)',
        )
        token_name, compiled = RuleTranslator.translate_token_rule(rule)

        # The reader name is prefixed and the callable carries the pattern.
        assert token_name == 't_NUMBER'
        assert compiled.__doc__ == r'\d+'
        assert callable(compiled)

        # Calling it with one positional argument performs the action.
        token = SimpleNamespace(value='3')
        compiled(token)
        assert token.value == 3

        # A second translation is an independent function object.
        _, again = RuleTranslator.translate_token_rule(rule)
        assert again is not compiled

    # * test: invalid_pattern_raises_before_synthesis
    def test_invalid_pattern_raises_before_synthesis(self, test_ctx, session):
        '''
        Raise a pattern error and do not return a function.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An invalid pattern is rejected even when the action is not Python.
        rule = ComplexTokenRuleAggregate(
            name='BAD',
            grammar_id='arithmetic',
            pattern='[',
            action='def',
        )
        with pytest.raises(ServiceError) as raised:
            RuleTranslator.translate_token_rule(rule)

        # The error names the rule and is the pattern error, not a function.
        error = raised.value
        assert error.error_code == RULE_PATTERN_INVALID_ID
        assert error.kwargs['rule_name'] == 'BAD'
        assert not callable(raised.value)

    # * test: derive_tokens_preserves_order
    def test_derive_tokens_preserves_order(self, test_ctx, session):
        '''
        Return bare names in input order without consulting grammar identity.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # PLUS belongs to arithmetic; NUMBER belongs to logic.
        rules = [
            SimpleTokenRuleAggregate(
                name='PLUS',
                grammar_id='arithmetic',
                pattern='+',
            ),
            ComplexTokenRuleAggregate(
                name='NUMBER',
                grammar_id='logic',
                pattern=r'\d+',
                action='t.value = int(t.value)',
            ),
        ]

        # Derivation keeps both names and does not sort or filter.
        assert RuleTranslator.derive_tokens(rules) == ['PLUS', 'NUMBER']

    # * test: does_not_import_ply_or_define_compiler
    def test_does_not_import_ply_or_define_compiler(self, test_ctx, session):
        '''
        Keep PLY out of translation and do not redefine the compiler here.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Inspect the utility and this test file without executing them again.
        root = Path(__file__).parents[2]
        utility = root / 'tiferet_ly' / 'utils' / 'translation.py'
        test_path = Path(__file__)
        utility_modules = imported_modules(utility)
        test_modules = imported_modules(test_path)

        # Neither file imports ply.
        for modules in (utility_modules, test_modules):
            assert 'ply' not in modules
            assert not any(
                name == 'ply' or name.startswith('ply.')
                for name in modules
            )

        # This test does not define a second action compiler.
        tree = ast.parse(test_path.read_text())
        defined = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert '_compile_action' not in defined
