"""Tiferet-Ly Token Rule Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional, Union

# ** infra
from pydantic import Field

# ** app
from tiferet import TransferObject
from ..domain.token import (
    ComplexTokenRule,
    SimpleTokenRule,
    SyntheticTokenRule,
    TokenRule,
)
from .core import NamedRuleAggregate

# *** mappers

# ** mapper: token_rule_aggregate
class TokenRuleAggregate(TokenRule, NamedRuleAggregate):
    '''
    Mutable aggregate base for a token rule.

    Shared name/grammar mutators come from :class:`NamedRuleAggregate`.
    ``set_pattern`` is shared by both variants; ``set_action`` lives only
    on :class:`ComplexTokenRuleAggregate`.
    '''

    # * method: set_pattern
    def set_pattern(self, pattern: str) -> None:
        '''
        Set the regular expression pattern.

        :param pattern: The new pattern.
        :type pattern: str
        :return: None
        :rtype: None
        '''

        # Update the pattern; validate_assignment=True handles re-validation.
        self.pattern = pattern

# ** mapper: simple_token_rule_aggregate
class SimpleTokenRuleAggregate(SimpleTokenRule, TokenRuleAggregate):
    '''
    Mutable aggregate for a simple token rule.
    '''

    pass

# ** mapper: complex_token_rule_aggregate
class ComplexTokenRuleAggregate(ComplexTokenRule, TokenRuleAggregate):
    '''
    Mutable aggregate for a complex token rule.
    '''

    # * method: set_action
    def set_action(self, action: str) -> None:
        '''
        Set the encoded source fragment that runs on match.

        :param action: The new action source fragment.
        :type action: str
        :return: None
        :rtype: None
        '''

        # Update the action; validate_assignment=True handles re-validation.
        self.action = action

# ** mapper: synthetic_token_rule_aggregate
class SyntheticTokenRuleAggregate(SyntheticTokenRule, TokenRuleAggregate):
    '''
    Mutable aggregate for a synthetic token rule.

    Carries no pattern or action mutators: a synthetic rule has nothing
    beyond the name/grammar_id shared mutators on NamedRuleAggregate.
    '''

    pass

# ** mapper: token_rule_config_object
class TokenRuleConfigObject(TransferObject):
    '''
    Configuration data representation of a token rule.

    Deliberately does not subclass :class:`TokenRule`, whose base carries
    no ``pattern``: a config entry must represent any of the three variants
    before it is known which one it is. ``.map()`` branches on ``action``'s
    and ``pattern``'s presence, with no separate discriminator field.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {
            'exclude': {
                'name',
            },
        },
    }

    # * attribute: name
    name: str = Field(
        ...,
        description='The bare token name PLY expects after its t_ prefix.',
    )

    # * attribute: grammar_id
    grammar_id: str = Field(
        ...,
        description='The id of the single Grammar this rule is declared under.',
    )

    # * attribute: pattern
    pattern: Optional[str] = Field(
        default=None,
        description='The regular expression pattern PLY matches this token against.',
    )

    # * attribute: action
    action: Optional[str] = Field(
        default=None,
        description='An encoded source fragment that runs whenever the rule matches.',
    )

    # * method: map
    def map(self, **overrides) -> Union[
            SimpleTokenRuleAggregate,
            ComplexTokenRuleAggregate,
            SyntheticTokenRuleAggregate]:
        '''
        Map the token rule configuration data to a token rule aggregate.

        Branches on ``action``'s and ``pattern``'s presence: a set action
        yields :class:`ComplexTokenRuleAggregate`; a set pattern with no
        action yields :class:`SimpleTokenRuleAggregate`; neither present
        yields :class:`SyntheticTokenRuleAggregate`.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped simple, complex, or synthetic token rule aggregate.
        :rtype: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate, SyntheticTokenRuleAggregate]
        '''

        # Serialize via the to_model role without dropping None fields so
        # domain construction — not the mapper — rejects corrupted values.
        data = self.to_primitive(role='to_model', exclude_none=False)
        data.update(overrides)

        # Construct the complex aggregate when an action is present.
        if data.get('action') is not None:
            return ComplexTokenRuleAggregate(
                name=data['name'],
                grammar_id=data['grammar_id'],
                pattern=data['pattern'],
                action=data['action'],
            )

        # Construct the simple aggregate when a pattern is present with no action.
        if data.get('pattern') is not None:
            return SimpleTokenRuleAggregate(
                name=data['name'],
                grammar_id=data['grammar_id'],
                pattern=data['pattern'],
            )

        # Construct the synthetic aggregate when neither pattern nor action is present.
        return SyntheticTokenRuleAggregate(
            name=data['name'],
            grammar_id=data['grammar_id'],
        )

    # * method: from_model
    @classmethod
    def from_model(cls, token: TokenRule, **overrides) -> 'TokenRuleConfigObject':
        '''
        Create a TokenRuleConfigObject from a token rule model or aggregate.

        :param token: The token rule domain object or aggregate.
        :type token: TokenRule
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The constructed TokenRuleConfigObject.
        :rtype: TokenRuleConfigObject
        '''

        # Dump the model and let TransferObject construct the config entry.
        return super().from_model(token, **overrides)
