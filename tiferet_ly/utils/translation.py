"""Tiferet-Ly PLY Translation Utility"""

# *** imports

# ** core
import re
import textwrap
from typing import Callable, Dict, List, Optional, Tuple, Union

# ** app
from tiferet.interfaces.core import ServiceError
from ..mappers.ast import AstNodeAggregate
from ..mappers.production import (
    ProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from ..mappers.token import (
    SimpleTokenRuleAggregate,
    TokenRuleAggregate,
)

# *** constants

# ** constant: action_compilation_failed_id
ACTION_COMPILATION_FAILED_ID = 'ACTION_COMPILATION_FAILED'

# ** constant: rule_pattern_invalid_id
RULE_PATTERN_INVALID_ID = 'RULE_PATTERN_INVALID'

# *** functions

# ** function: rewrite_action
def rewrite_action(action: str, rewrites: Dict[str, type]) -> str:
    '''
    Replace declared action shorthands with their bound class names.

    Longer keys are applied first so a shorter key cannot clip a longer
    one. Each key is matched as a token and does not eat a following
    identifier continuation.

    :param action: The declared action source fragment.
    :type action: str
    :param rewrites: The effective shorthand-to-class mapping.
    :type rewrites: Dict[str, type]
    :return: The rewritten action source.
    :rtype: str
    '''

    # Apply longer keys first so $stmt cannot clip $stmt_list.
    rewritten = action
    for key in sorted(rewrites, key=len, reverse=True):
        rewritten = re.sub(
            re.escape(key) + r'(?![A-Za-z0-9_])',
            rewrites[key].__name__,
            rewritten,
        )

    # Return the rewritten fragment.
    return rewritten

# *** utils

# ** util: rule_translator
class RuleTranslator:
    '''
    Turns one already-selected token or production rule into the literal
    value PLY's t_* / p_* conventions require, without importing ply or
    deciding which rules belong to a reader.
    '''

    # * attribute: default_rewrites
    DEFAULT_REWRITES = {
        '$ast': AstNodeAggregate,
    }

    # * method: _compile_action (classmethod)
    @classmethod
    def _compile_action(cls,
                        attr_name: str,
                        arg_name: str,
                        action: str,
                        rule_name: str,
                        rewrites: Optional[Dict[str, type]] = None) -> Callable:
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
        :param rewrites: Optional extra or overriding shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: The synthesized function.
        :rtype: Callable
        '''

        # Merge the default table with any caller-supplied rows.
        effective = {
            **cls.DEFAULT_REWRITES,
            **(rewrites or {}),
        }

        # Rewrite only the action fragment, then build the function source.
        rewritten = rewrite_action(action, effective)
        source = (
            f'def {attr_name}({arg_name}):\n'
            f'{textwrap.indent(textwrap.dedent(rewritten), "    ")}'
        )

        # Seed a fresh namespace with one bind per unique class name.
        namespace: Dict[str, type] = {}
        for factory in effective.values():
            name = factory.__name__
            if name in namespace and namespace[name] is not factory:
                ServiceError.raise_for(
                    cls,
                    ACTION_COMPILATION_FAILED_ID,
                    message=(
                        f'Rewrite values share the class name {name!r}.'
                    ),
                    rule_name=rule_name,
                )
            namespace[name] = factory

        # Compile and execute into the seeded namespace.
        try:
            compiled = compile(source, f'<tiferet_ly:{attr_name}>', 'exec')
            exec(compiled, namespace)
        except Exception as error:
            ServiceError.raise_for(
                cls,
                ACTION_COMPILATION_FAILED_ID,
                message=str(error),
                cause=error,
                rule_name=rule_name,
            )

        # Return the one function the compiled source defined.
        return namespace[attr_name]

    # * method: _pass_through (classmethod)
    @classmethod
    def _pass_through(cls, rule: SimpleProductionRuleAggregate) -> Callable:
        '''
        Synthesize the literal p[0] = p[1] action for a simple production.

        :param rule: The simple production whose spec must have one RHS symbol.
        :type rule: SimpleProductionRuleAggregate
        :return: The synthesized pass-through function.
        :rtype: Callable
        '''

        # A simple production is valid only when the right-hand side is one symbol.
        rhs = rule.spec.split(':', 1)[1].split() if ':' in rule.spec else []
        if len(rhs) != 1:
            ServiceError.raise_for(
                cls,
                RULE_PATTERN_INVALID_ID,
                message='Simple production spec must have exactly one right-hand-side symbol.',
                rule_name=rule.name,
            )

        # Compile the literal pass-through body and return the function.
        return cls._compile_action(
            f'p_{rule.name}',
            'p',
            'p[0] = p[1]',
            rule.name,
        )

    # * method: translate_token_rule (classmethod)
    @classmethod
    def translate_token_rule(cls,
                             rule: TokenRuleAggregate,
                             rewrites: Optional[Dict[str, type]] = None) -> Tuple[str, Union[str, Callable]]:
        '''
        Translate one token rule into a PLY t_* attribute pair.

        :param rule: The token rule to translate.
        :type rule: TokenRuleAggregate
        :param rewrites: Optional extra or overriding shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: The prefixed attribute name and the pattern string or function.
        :rtype: Tuple[str, Union[str, Callable]]
        '''

        # Reject a pattern that is not a valid regular expression before synthesis.
        try:
            re.compile(rule.pattern)
        except re.error as error:
            ServiceError.raise_for(
                cls,
                RULE_PATTERN_INVALID_ID,
                message=str(error),
                cause=error,
                rule_name=rule.name,
            )

        # Simple rules are an identity translation of the declared pattern.
        attr_name = f't_{rule.name}'
        if isinstance(rule, SimpleTokenRuleAggregate):
            return (attr_name, rule.pattern)

        # Complex rules become a self-less function whose docstring is the pattern.
        func = cls._compile_action(
            attr_name,
            't',
            rule.action,
            rule.name,
            rewrites=rewrites,
        )
        func.__doc__ = rule.pattern

        # Return the prefixed name and the synthesized function.
        return (attr_name, func)

    # * method: translate_production_rule (classmethod)
    @classmethod
    def translate_production_rule(cls,
                                  rule: ProductionRuleAggregate,
                                  rewrites: Optional[Dict[str, type]] = None) -> Tuple[str, Callable]:
        '''
        Translate one production rule into a PLY p_* attribute pair.

        :param rule: The production rule to translate.
        :type rule: ProductionRuleAggregate
        :param rewrites: Optional extra or overriding shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: The prefixed attribute name and the synthesized function.
        :rtype: Tuple[str, Callable]
        '''

        # Every production becomes a synthesized function; PLY has no string shortcut.
        attr_name = f'p_{rule.name}'

        # Simple productions get the literal pass-through; complex ones compile action.
        if isinstance(rule, SimpleProductionRuleAggregate):
            func = cls._pass_through(rule)
        else:
            func = cls._compile_action(
                attr_name,
                'p',
                rule.action,
                rule.name,
                rewrites=rewrites,
            )

        # Carry the declared spec as the function docstring.
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
