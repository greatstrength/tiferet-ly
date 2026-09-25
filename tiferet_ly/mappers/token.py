"""Tiferet Ly Token Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from pydantic import Field

# ** app
from tiferet import (
    Aggregate,
    TransferObject,
)
from tiferet_ly.domain import (
    ComplexTokenRule,
    SimpleTokenRule,
    TokenRule,
)
from .core import NamedRuleAggregate

# *** mappers

# ** mapper: token_rule_aggregate
class TokenRuleAggregate(TokenRule, Aggregate):
    '''
    A mutable token rule that stores only name and grammar membership.

    Pattern and action stay on the Simple and Complex variants. This
    aggregate adds no catalogue validation of its own.
    '''

# ** mapper: simple_token_rule_aggregate
class SimpleTokenRuleAggregate(SimpleTokenRule, NamedRuleAggregate):
    '''
    A mutable simple token rule whose declaration is a pattern only.

    Renaming and grammar reassignment come from the shared named-rule
    aggregate. This variant stores no action.
    '''

    # * method: set_pattern
    def set_pattern(self, pattern: str) -> None:
        '''
        Replace the declared token pattern.

        :param pattern: The new pattern.
        :type pattern: str
        :return: None
        :rtype: None
        '''

        # Assign the pattern without resolving grammar membership.
        self.pattern = pattern

# ** mapper: complex_token_rule_aggregate
class ComplexTokenRuleAggregate(ComplexTokenRule, NamedRuleAggregate):
    '''
    A mutable complex token rule that stores pattern and action source.

    The action remains source text. Replacing it does not compile or
    execute the action, and does not resolve the owning grammar.
    '''

    # * method: set_pattern
    def set_pattern(self, pattern: str) -> None:
        '''
        Replace the declared token pattern.

        :param pattern: The new pattern.
        :type pattern: str
        :return: None
        :rtype: None
        '''

        # Assign the pattern without resolving grammar membership.
        self.pattern = pattern

    # * method: set_action
    def set_action(self, action: str) -> None:
        '''
        Replace the declared action source.

        :param action: The new action source.
        :type action: str
        :return: None
        :rtype: None
        '''

        # Assign the action source without compiling it.
        self.action = action

# ** mapper: token_rule_config_object
class TokenRuleConfigObject(TransferObject):
    '''
    Configuration data for one declared token rule.

    A missing action maps to a Simple token aggregate. A present action
    maps to a Complex token aggregate. The mapper does not resolve the
    owning grammar or reject an unknown grammar id.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {
            'by_alias': True,
        },
    }

    # * attribute: name
    name: str | None = Field(
        default=None,
        description='The declared token name.',
    )

    # * attribute: grammar_id
    grammar_id: str | None = Field(
        default=None,
        description='The identifier of the one grammar that owns the rule.',
    )

    # * attribute: pattern
    pattern: str | None = Field(
        default=None,
        description='The declared token pattern.',
    )

    # * attribute: action
    action: str | None = Field(
        default=None,
        description='Declared action source; None means a Simple rule.',
    )

    # * method: map
    def map(self, **overrides) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate:
        '''
        Map this configuration to a Simple or Complex token aggregate.

        Declared fields present in ``overrides`` replace the stored values.
        Any other override is passed through to aggregate construction.
        A resulting action of ``None`` selects the Simple aggregate and is
        not passed to it.

        :param overrides: Field replacements and extra construction values.
        :type overrides: dict
        :return: The mapped token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
        '''

        # Read the declared fields, then apply overrides for those keys.
        values = {
            'name': self.name,
            'grammar_id': self.grammar_id,
            'pattern': self.pattern,
            'action': self.action,
        }
        for key in ('name', 'grammar_id', 'pattern', 'action'):
            if key in overrides:
                values[key] = overrides[key]

        # Keep every other override for aggregate construction.
        extra = {
            key: value
            for key, value in overrides.items()
            if key not in values
        }

        # A present action is Complex; a missing action is Simple.
        if values['action'] is not None:
            return ComplexTokenRuleAggregate(
                name=values['name'],
                grammar_id=values['grammar_id'],
                pattern=values['pattern'],
                action=values['action'],
                **extra,
            )

        # Do not pass action into the Simple aggregate.
        return SimpleTokenRuleAggregate(
            name=values['name'],
            grammar_id=values['grammar_id'],
            pattern=values['pattern'],
            **extra,
        )

    # * method: from_model
    @classmethod
    def from_model(
            cls,
            model: SimpleTokenRule | ComplexTokenRule,
            **overrides,
        ) -> 'TokenRuleConfigObject':
        '''
        Create token configuration data from a token rule or aggregate.

        Action is copied only from a complex token rule. Overrides are
        applied last.

        :param model: A simple or complex token rule, or either aggregate.
        :type model: SimpleTokenRule | ComplexTokenRule
        :param overrides: Field values that replace the copied data.
        :type overrides: dict
        :return: The token configuration object.
        :rtype: TokenRuleConfigObject
        '''

        # Copy identity and pattern. Copy action only for a complex rule.
        data = {
            'name': model.name,
            'grammar_id': model.grammar_id,
            'pattern': model.pattern,
            'action': model.action if isinstance(model, ComplexTokenRule) else None,
        }

        # Apply overrides last so they replace copied fields.
        data.update(overrides)

        # Validate into configuration data. Do not reshape a catalogue.
        return cls.model_validate(data)
