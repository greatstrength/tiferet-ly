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

# *** utils

# ** util: rule_translator
class RuleTranslator:
    '''
    Compile declared action source into a callable a reader can invoke.

    The helper validates a pattern, then builds one new function. It does
    not translate a whole rule, select a grammar, or import PLY.
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
