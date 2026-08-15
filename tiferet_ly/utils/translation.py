"""Tiferet-Ly PLY Translation Utility"""

# *** imports

# ** core
import re
import textwrap
from typing import Callable, List, Tuple, Union

# ** app
from tiferet.interfaces.core import ServiceError
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate

# *** constants

# ** constant: action_compilation_failed_id
ACTION_COMPILATION_FAILED_ID = 'ACTION_COMPILATION_FAILED'

# ** constant: rule_pattern_invalid_id
RULE_PATTERN_INVALID_ID = 'RULE_PATTERN_INVALID'

# *** utils

# ** util: rule_translator
class RuleTranslator:
    '''
    Turns one already-selected token or production rule into the literal
    value PLY's t_* / p_* conventions require, without importing ply or
    deciding which rules belong to a reader.
    '''

    # * method: _compile_action (static)
    @staticmethod
    def _compile_action(
            attr_name: str,
            arg_name: str,
            action: str,
            rule_name: str) -> Callable:
        '''
        Compile a declared action into a plain, self-less function.

        :param attr_name: The synthesized function name.
        :type attr_name: str
        :param arg_name: The sole parameter name (`t` or `p`).
        :type arg_name: str
        :param action: The encoded source fragment used as the function body.
        :type action: str
        :param rule_name: The rule name used to attribute compilation failures.
        :type rule_name: str
        :return: The synthesized function.
        :rtype: Callable
        '''

        # Build a one-parameter function whose body is the declared action.
        source = (
            f'def {attr_name}({arg_name}):\n'
            f'{textwrap.indent(textwrap.dedent(action), "    ")}'
        )

        # Compile and execute into a fresh namespace so calls do not share state.
        try:
            compiled = compile(source, f'<tiferet_ly:{attr_name}>', 'exec')
            namespace = {}
            exec(compiled, namespace)
        except Exception as error:
            ServiceError.raise_for(
                RuleTranslator,
                ACTION_COMPILATION_FAILED_ID,
                message=str(error),
                cause=error,
                rule_name=rule_name,
            )

        # Return the one function the compiled source defined.
        return namespace[attr_name]

    # * method: translate_token_rule (static)
    @staticmethod
    def translate_token_rule(rule: TokenRuleAggregate) -> Tuple[str, Union[str, Callable]]:
        '''
        Translate one token rule into a PLY t_* attribute pair.

        :param rule: The token rule to translate.
        :type rule: TokenRuleAggregate
        :return: The prefixed attribute name and the pattern string or function.
        :rtype: Tuple[str, Union[str, Callable]]
        '''

        # Reject a pattern that is not a valid regular expression before synthesis.
        try:
            re.compile(rule.pattern)
        except re.error as error:
            ServiceError.raise_for(
                RuleTranslator,
                RULE_PATTERN_INVALID_ID,
                message=str(error),
                cause=error,
                rule_name=rule.name,
            )

        # Simple rules are an identity translation of the declared pattern.
        attr_name = f't_{rule.name}'
        if getattr(rule, 'action', None) is None:
            return (attr_name, rule.pattern)

        # Complex rules become a self-less function whose docstring is the pattern.
        func = RuleTranslator._compile_action(
            attr_name,
            't',
            rule.action,
            rule.name,
        )
        func.__doc__ = rule.pattern

        # Return the prefixed name and the synthesized function.
        return (attr_name, func)

    # * method: translate_production_rule (static)
    @staticmethod
    def translate_production_rule(rule: ProductionRuleAggregate) -> Tuple[str, Callable]:
        '''
        Translate one production rule into a PLY p_* attribute pair.

        :param rule: The production rule to translate.
        :type rule: ProductionRuleAggregate
        :return: The prefixed attribute name and the synthesized function.
        :rtype: Tuple[str, Callable]
        '''

        # Every production becomes a synthesized function; PLY has no string shortcut.
        attr_name = f'p_{rule.name}'

        # Simple productions use a literal pass-through when the RHS is one symbol.
        if getattr(rule, 'action', None) is None:
            rhs = rule.spec.split(':', 1)[1].split() if ':' in rule.spec else []
            if len(rhs) != 1:
                ServiceError.raise_for(
                    RuleTranslator,
                    RULE_PATTERN_INVALID_ID,
                    message='Simple production spec must have exactly one right-hand-side symbol.',
                    rule_name=rule.name,
                )

            func = RuleTranslator._compile_action(
                attr_name,
                'p',
                'p[0] = p[1]',
                rule.name,
            )
            func.__doc__ = rule.spec

            # Return the prefixed name and the pass-through function.
            return (attr_name, func)

        # Complex productions compile the declared action and carry the spec as __doc__.
        func = RuleTranslator._compile_action(
            attr_name,
            'p',
            rule.action,
            rule.name,
        )
        func.__doc__ = rule.spec

        # Return the prefixed name and the synthesized function.
        return (attr_name, func)

    # * method: derive_tokens (static)
    @staticmethod
    def derive_tokens(token_rules: List[TokenRuleAggregate]) -> List[str]:
        '''
        Derive PLY's flat token-name list from an already-ordered rule list.

        :param token_rules: The already-selected token rules.
        :type token_rules: List[TokenRuleAggregate]
        :return: Bare, unprefixed token names in input order.
        :rtype: List[str]
        '''

        # Preserve declared order; never convert to a set or sort.
        return [rule.name for rule in token_rules]
