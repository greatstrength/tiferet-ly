"""Tiferet Ly Rule Translation Utility"""

# *** imports

# ** core
import re
from textwrap import dedent, indent
from typing import Callable

# ** app
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.translation import (
    ACTION_COMPILATION_FAILED_ID,
    RULE_PATTERN_INVALID_ID,
)
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)

# *** utils

# ** util: rule_translator
class RuleTranslator:
    '''
    Translate declared rules into names and values a reader can use.

    Simple tokens keep their pattern text. Complex tokens and complex
    productions become callables through the shared action compiler. A
    simple production with one right-hand-side symbol becomes a
    pass-through manufactured at translation time, carrying its
    specification as the callable docstring. The utility does not select
    a grammar, persist rules, or import PLY.
    '''

    # * method: _compile_action (static)
    @staticmethod
    def _compile_action(
            rule_name: str,
            pattern: str,
            action: str,
        ) -> Callable:
        '''
        Compile action source into a new one-argument function.

        An invalid regular expression is rejected before the action is
        compiled. Token actions may name the argument ``t``; production
        actions may name it ``p``. Both names refer to the single
        positional argument.

        :param rule_name: The declared rule name used to name the function.
        :type rule_name: str
        :param pattern: The pattern stored as the function docstring.
        :type pattern: str
        :param action: The declared action source.
        :type action: str
        :return: A new function named from the rule.
        :rtype: Callable
        '''

        # Reject an invalid regular expression before compiling the action.
        try:
            re.compile(pattern)
        except re.error as error:
            ServiceError.raise_for(
                RuleTranslator,
                RULE_PATTERN_INVALID_ID,
                message='Rule pattern is not a valid regular expression.',
                cause=error,
                rule_name=rule_name,
            )

        # Bind the one positional argument to both t and p, then indent the action.
        body = indent(dedent(action).strip('\n'), '    ')
        source = (
            'def _compiled_action(t):\n'
            '    p = t\n'
            f'{body}\n'
        )

        # Compile the action. A syntax error names the rule and the SyntaxError.
        namespace = {}
        try:
            code = compile(source, f'<rule:{rule_name}>', 'exec')
            exec(code, namespace)
        except SyntaxError as error:
            ServiceError.raise_for(
                RuleTranslator,
                ACTION_COMPILATION_FAILED_ID,
                message='Action source could not be compiled.',
                cause=error,
                rule_name=rule_name,
                syntax_error=f'{error.__class__.__name__}: {error.msg}',
            )

        # Name the function from the rule and carry the pattern as its docstring.
        function = namespace['_compiled_action']
        function.__name__ = rule_name
        function.__qualname__ = rule_name
        function.__doc__ = pattern

        # Return a distinct function object for this call.
        return function

    # * method: translate_token_rule (static)
    @staticmethod
    def translate_token_rule(
            rule: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate,
        ) -> tuple[str, str | Callable]:
        '''
        Translate one declared token rule into a reader name and value.

        A simple token returns its attribute name and the pattern text
        unchanged. A complex token returns a callable from the shared
        action compiler. An invalid complex pattern is rejected by that
        compiler before the action is compiled.

        :param rule: A simple or complex token aggregate.
        :type rule: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        :return: The ``t_`` name and either the pattern or a callable.
        :rtype: tuple[str, str | Callable]
        '''

        # Name the reader attribute from the bare declared token name.
        token_name = f't_{rule.name}'

        # Keep a simple pattern as text. Do not compile or rewrite it.
        if isinstance(rule, SimpleTokenRuleAggregate):
            return token_name, rule.pattern

        # Compile a complex token. Invalid patterns fail before synthesis.
        function = RuleTranslator._compile_action(
            rule.name,
            rule.pattern,
            rule.action,
        )

        # Return the reader name and the compiled action.
        return token_name, function

    # * method: derive_tokens (static)
    @staticmethod
    def derive_tokens(rules) -> list[str]:
        '''
        Derive bare token names in declared order.

        Every rule contributes its name. Membership and grammar identity
        are not consulted, and the names are not sorted.

        :param rules: Declared token rules in input order.
        :type rules: list
        :return: Bare token names in that same order.
        :rtype: list[str]
        '''

        # Copy names in input order without filtering or sorting.
        return [rule.name for rule in rules]

    # * method: translate_production_rule (static)
    @staticmethod
    def translate_production_rule(
            rule: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate,
        ) -> tuple[str, Callable]:
        '''
        Translate one declared production into a reader name and callable.

        A complex production is compiled by the shared action compiler, so
        its docstring is the specification and its call performs the
        declared action. A simple production stores no action. When its
        specification has exactly one right-hand-side symbol, a
        pass-through that assigns ``p[0] = p[1]`` is manufactured here and
        carries the specification as its docstring. Any other simple
        specification is rejected and names the rule.

        :param rule: A simple or complex production aggregate.
        :type rule: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        :return: The ``p_`` name and a callable.
        :rtype: tuple[str, Callable]
        '''

        # Name the reader attribute from the bare declared production name.
        production_name = f'p_{rule.name}'

        # Manufacture a one-symbol simple pass-through. Do not compile it.
        if isinstance(rule, SimpleProductionRuleAggregate):
            function = RuleTranslator._simple_pass_through(rule)
            return production_name, function

        # Compile a complex production through the shared action compiler.
        function = RuleTranslator._compile_action(
            rule.name,
            rule.spec,
            rule.action,
        )

        # Return the reader name and the compiled action.
        return production_name, function

    # * method: _simple_pass_through (static)
    @staticmethod
    def _simple_pass_through(rule: SimpleProductionRuleAggregate) -> Callable:
        '''
        Manufacture a one-symbol simple production pass-through.

        The function is created at translation time and is not stored on
        the domain model. A specification with no colon, or with zero or
        more than one right-hand-side symbol, is rejected before the
        function is created.

        :param rule: A simple production aggregate.
        :type rule: SimpleProductionRuleAggregate
        :return: A new function that assigns ``p[0] = p[1]``.
        :rtype: Callable
        '''

        # Count right-hand-side symbols after the specification colon.
        _, separator, rhs = rule.spec.partition(':')
        symbols = rhs.split() if separator else []

        # Reject zero or many symbols and name the rule.
        if len(symbols) != 1:
            ServiceError.raise_for(
                RuleTranslator,
                RULE_PATTERN_INVALID_ID,
                message='Simple production specification must have exactly one right-hand-side symbol.',
                rule_name=rule.name,
            )

        # Manufacture a new pass-through. Carry the spec as the docstring.
        def pass_through(p):
            p[0] = p[1]

        pass_through.__name__ = rule.name
        pass_through.__qualname__ = rule.name
        pass_through.__doc__ = rule.spec

        # Return a distinct function object for this call.
        return pass_through
