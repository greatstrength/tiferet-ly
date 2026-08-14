"""Tiferet-Ly Token Rule Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional, Union

# ** infra
from pydantic import Field

# ** app
from tiferet import (
    Aggregate,
    TransferObject,
)
from ..domain.token import (
    ComplexTokenRule,
    SimpleTokenRule,
    TokenRule,
)

# *** mappers

# ** mapper: token_rule_aggregate
class TokenRuleAggregate(TokenRule, Aggregate):
    '''
    Mutable aggregate for a token rule.

    Carries no domain-specific mutators beyond the inherited
    ``set_attribute`` / ``to_dict`` surface; nothing in the current
    roadmap edits a loaded rule in place. Concrete simple/complex field
    sets live on the domain variants produced by
    :meth:`TokenRuleConfigObject.map`.
    '''

    pass


# ** mapper: token_rule_config_object
class TokenRuleConfigObject(TransferObject):
    '''
    Configuration data representation of a token rule.

    Deliberately does not subclass :class:`TokenRule`, whose base carries
    no ``pattern``: a config entry must represent either variant before it
    is known which one it is. ``.map()`` branches on ``action``'s presence
    with no separate discriminator field.
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
    pattern: str = Field(
        ...,
        description='The regular expression pattern PLY matches this token against.',
    )

    # * attribute: action
    action: Optional[str] = Field(
        default=None,
        description='An encoded source fragment that runs whenever the rule matches.',
    )

    # * method: map
    def map(self, **overrides) -> Union[SimpleTokenRule, ComplexTokenRule]:
        '''
        Map the token rule configuration data to a domain token rule.

        Branches on ``action``'s presence: a set action yields
        :class:`ComplexTokenRule`, otherwise :class:`SimpleTokenRule`.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped simple or complex token rule.
        :rtype: Union[SimpleTokenRule, ComplexTokenRule]
        '''

        # Serialize via the to_model role without dropping None fields so
        # domain construction — not the mapper — rejects corrupted values.
        data = self.to_primitive(role='to_model', exclude_none=False)
        data.update(overrides)

        # Construct the complex variant when an action is present.
        if data.get('action') is not None:
            return ComplexTokenRule(
                name=data['name'],
                grammar_id=data['grammar_id'],
                pattern=data['pattern'],
                action=data['action'],
            )

        # Construct the simple variant otherwise (drop action if absent/None).
        return SimpleTokenRule(
            name=data['name'],
            grammar_id=data['grammar_id'],
            pattern=data['pattern'],
        )

    # * method: from_model
    @classmethod
    def from_model(cls, token: TokenRule, **overrides) -> 'TokenRuleConfigObject':
        '''
        Create a TokenRuleConfigObject from a token rule model or aggregate.

        :param token: The token rule domain object.
        :type token: TokenRule
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The constructed TokenRuleConfigObject.
        :rtype: TokenRuleConfigObject
        '''

        # Dump the model and let TransferObject construct the config entry.
        return super().from_model(token, **overrides)
