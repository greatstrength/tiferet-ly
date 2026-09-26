"""Tiferet Ly Production Translation Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** infra
import pytest

# ** app
from tiferet import use_tester
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.translation import RULE_PATTERN_INVALID_ID
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
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

# ** function: defined_functions
def defined_functions(path: Path) -> list[str]:
    '''
    Collect function names defined in a Python source file.

    Nested definitions are included so a copied compiler cannot hide.

    :param path: The source file to inspect.
    :type path: Path
    :return: Defined function names.
    :rtype: list[str]
    '''

    # Parse the source without importing it.
    tree = ast.parse(path.read_text())

    # Include nested definitions.
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

# *** testers

# ** tester: test_production_translation
@use_tester(
    type='generic',
    target_cls=RuleTranslator,
)
class TestProductionTranslation:
    '''
    Tests for simple production pass-through and complex production compilation.
    '''

    # * test: complex_production_performs_action
    def test_complex_production_performs_action(self, test_ctx, session):
        '''
        Return a callable whose docstring is the spec and whose call acts.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Compile a complex production through the shared compiler.
        rule = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : expr PLUS term',
            action='p[0] = p[1] + p[3]',
        )
        production_name, compiled = RuleTranslator.translate_production_rule(rule)

        # The reader name is prefixed and the callable carries the spec.
        assert production_name == 'p_expr'
        assert compiled.__doc__ == 'expr : expr PLUS term'
        assert compiled.__name__ == 'expr'
        assert callable(compiled)

        # Calling it with one positional argument performs the action.
        values = [None, 1, '+', 2]
        compiled(values)
        assert values[0] == 3

    # * test: simple_production_passes_through
    def test_simple_production_passes_through(self, test_ctx, session):
        '''
        Return a callable that sets ``p[0]`` from ``p[1]`` and carries the spec.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A one-symbol simple production is manufactured, not compiled.
        rule = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : term',
        )
        production_name, compiled = RuleTranslator.translate_production_rule(rule)

        # The reader name is prefixed and the docstring is the specification.
        assert production_name == 'p_expr'
        assert compiled.__doc__ == 'expr : term'
        assert callable(compiled)
        assert not hasattr(rule, 'action')

        # Calling it copies the first right-hand-side value.
        values = [None, 'term-value']
        compiled(values)
        assert values[0] == 'term-value'
        assert values[0] is values[1]

    # * test: multi_symbol_simple_production_is_rejected
    def test_multi_symbol_simple_production_is_rejected(self, test_ctx, session):
        '''
        Reject a simple production whose specification has more than one symbol.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Three right-hand-side symbols are not a pass-through.
        rule = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : expr PLUS term',
        )
        with pytest.raises(ServiceError) as raised:
            RuleTranslator.translate_production_rule(rule)

        # The error names the rule and is the pattern error.
        error = raised.value
        assert error.error_code == RULE_PATTERN_INVALID_ID
        assert error.kwargs['rule_name'] == 'expr'

    # * test: empty_simple_production_is_rejected
    def test_empty_simple_production_is_rejected(self, test_ctx, session):
        '''
        Reject a simple production whose specification has no right-hand-side symbol.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A bare colon has zero right-hand-side symbols.
        rule = SimpleProductionRuleAggregate(
            name='empty',
            grammar_id='arithmetic',
            spec='empty :',
        )
        with pytest.raises(ServiceError) as raised:
            RuleTranslator.translate_production_rule(rule)

        # The error names the rule and is the pattern error.
        error = raised.value
        assert error.error_code == RULE_PATTERN_INVALID_ID
        assert error.kwargs['rule_name'] == 'empty'

    # * test: translations_are_independent
    def test_translations_are_independent(self, test_ctx, session):
        '''
        Return a distinct function object on each translation.

        :param test_ctx: The bound generic tester context.
        :type test_ctx: GenericTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Translate the same simple and complex rules twice.
        simple = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : term',
        )
        complex_rule = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='expr : expr PLUS term',
            action='p[0] = p[1] + p[3]',
        )
        _, simple_first = RuleTranslator.translate_production_rule(simple)
        _, simple_second = RuleTranslator.translate_production_rule(simple)
        _, complex_first = RuleTranslator.translate_production_rule(complex_rule)
        _, complex_second = RuleTranslator.translate_production_rule(complex_rule)

        # Each call manufactures or compiles a new function.
        assert simple_first is not simple_second
        assert complex_first is not complex_second
        assert simple_first.__doc__ == simple_second.__doc__ == 'expr : term'
        assert complex_first.__doc__ == complex_second.__doc__ == 'expr : expr PLUS term'

        # The simple functions do not share a result slot.
        left = [None, 'left']
        right = [None, 'right']
        simple_first(left)
        simple_second(right)
        assert left[0] == 'left'
        assert right[0] == 'right'

    # * test: does_not_import_ply_or_redefine_compiler
    def test_does_not_import_ply_or_redefine_compiler(self, test_ctx, session):
        '''
        Keep PLY out of translation and do not redefine the action compiler.

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

        # The shared compiler remains the only ``_compile_action``.
        utility_functions = defined_functions(utility)
        assert utility_functions.count('_compile_action') == 1
        assert '_compile_action' not in defined_functions(test_path)
        assert 'pass_through' not in defined_functions(test_path)
