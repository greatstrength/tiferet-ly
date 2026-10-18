"""Tiferet Ly Token Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from pydantic import Field
from tiferet import (
    Aggregate,
    TransferObject,
)

# ** app
from tiferet_ly.domain import (
    ComplexTokenRule,
    SimpleTokenRule,
    SyntheticTokenRule,
    TokenRule,
)
from .core import NamedRuleAggregate

# *** mappers

# ** mapper: token_rule_aggregate
class TokenRuleAggregate(TokenRule, Aggregate):
    '''
    A mutable token rule that stores only name and grammar membership.

    The Simple and Complex variants still own pattern and action, and the
    Synthetic variant stores neither. This aggregate adds no catalogue
    validation of its own.
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

# ** mapper: synthetic_token_rule_aggregate
class SyntheticTokenRuleAggregate(SyntheticTokenRule, NamedRuleAggregate):
    '''
    A mutable synthetic token rule that stores only name and grammar membership.

    Renaming and grammar reassignment come from the shared named-rule
    aggregate. This variant stores no pattern and no action, and adds no
    pattern or action mutator.
    '''

# ** mapper: token_rule_config_object
class TokenRuleConfigObject(TransferObject):
    '''
    Configuration data for one declared token rule.

    A present action maps to a Complex token aggregate and still requires
    a pattern. A pattern with no action maps to a Simple token aggregate.
    Neither maps to a Synthetic token aggregate. The mapper does not
    resolve the owning grammar or reject an unknown grammar id. It does
    not compile an action and does not add a discriminator field.
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
        description=(
            'The declared token pattern. None, with no action, is the synthetic shape.'
        ),
    )

    # * attribute: action
    action: str | None = Field(
        default=None,
        description=(
            'Declared action source. A present action is Complex and still requires a pattern. '
            'None with a pattern is Simple. None with no pattern is Synthetic.'
        ),
    )

    # * method: map
    def map(self, **overrides) -> SimpleTokenRuleAggregate | ComplexTokenRuleAggregate | SyntheticTokenRuleAggregate:
        '''
        Map this configuration to a Simple, Complex, or Synthetic token aggregate.

        Declared fields present in ``overrides`` replace the stored values
        before the branch. Any other override is passed through to
        aggregate construction. A present action selects the Complex
        aggregate even when the pattern is missing. A pattern with no
        action selects the Simple aggregate, and action is not passed.
        Neither selects the Synthetic aggregate, and neither pattern nor
        action is passed.

        :param overrides: Field replacements and extra construction values.
        :type overrides: dict
        :return: The mapped token aggregate.
        :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate | SyntheticTokenRuleAggregate
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

        # A present action is Complex, even without a pattern.
        if values['action'] is not None:
            return ComplexTokenRuleAggregate(
                name=values['name'],
                grammar_id=values['grammar_id'],
                pattern=values['pattern'],
                action=values['action'],
                **extra,
            )

        # A pattern with no action is Simple. Do not pass action.
        if values['pattern'] is not None:
            return SimpleTokenRuleAggregate(
                name=values['name'],
                grammar_id=values['grammar_id'],
                pattern=values['pattern'],
                **extra,
            )

        # Neither is Synthetic. Do not pass pattern or action.
        return SyntheticTokenRuleAggregate(
            name=values['name'],
            grammar_id=values['grammar_id'],
            **extra,
        )

    # * method: from_model
    @classmethod
    def from_model(
            cls,
            model: SimpleTokenRule | ComplexTokenRule | SyntheticTokenRule,
            **overrides,
        ) -> 'TokenRuleConfigObject':
        '''
        Create token configuration data from a token rule or aggregate.

        Pattern is copied only from a simple or complex token rule. Action
        is copied only from a complex token rule. A synthetic token rule
        copies neither. Overrides are applied last.

        :param model: A simple, complex, or synthetic token rule, or an aggregate of one.
        :type model: SimpleTokenRule | ComplexTokenRule | SyntheticTokenRule
        :param overrides: Field values that replace the copied data.
        :type overrides: dict
        :return: The token configuration object.
        :rtype: TokenRuleConfigObject
        '''

        # Copy identity. Copy pattern only for a simple or complex rule,
        # and action only for a complex rule.
        data = {
            'name': model.name,
            'grammar_id': model.grammar_id,
            'pattern': model.pattern if isinstance(model, (SimpleTokenRule, ComplexTokenRule)) else None,
            'action': model.action if isinstance(model, ComplexTokenRule) else None,
        }

        # Apply overrides last so they replace copied fields.
        data.update(overrides)

        # Validate into configuration data. Do not reshape a catalogue.
        return cls.model_validate(data)
