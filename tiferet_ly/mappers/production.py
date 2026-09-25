"""Tiferet Ly Production Mappers"""

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
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)
from .core import NamedRuleAggregate

# *** mappers

# ** mapper: production_rule_aggregate
class ProductionRuleAggregate(ProductionRule, Aggregate):
    '''
    A mutable production rule that stores only name and grammar membership.

    Specification and action stay on the Simple and Complex variants. This
    aggregate adds no catalogue validation of its own.
    '''

# ** mapper: simple_production_rule_aggregate
class SimpleProductionRuleAggregate(SimpleProductionRule, NamedRuleAggregate):
    '''
    A mutable simple production whose declaration is a specification only.

    Renaming and grammar reassignment come from the shared named-rule
    aggregate. This variant stores no action.
    '''

    # * method: set_spec
    def set_spec(self, spec: str) -> None:
        '''
        Replace the declared production specification.

        :param spec: The new specification.
        :type spec: str
        :return: None
        :rtype: None
        '''

        # Assign the specification without resolving grammar membership.
        self.spec = spec

# ** mapper: complex_production_rule_aggregate
class ComplexProductionRuleAggregate(ComplexProductionRule, NamedRuleAggregate):
    '''
    A mutable complex production that stores specification and action source.

    The action remains source text. Replacing it does not compile or
    execute the action, and does not resolve the owning grammar.
    '''

    # * method: set_spec
    def set_spec(self, spec: str) -> None:
        '''
        Replace the declared production specification.

        :param spec: The new specification.
        :type spec: str
        :return: None
        :rtype: None
        '''

        # Assign the specification without resolving grammar membership.
        self.spec = spec

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

# ** mapper: production_rule_config_object
class ProductionRuleConfigObject(TransferObject):
    '''
    Configuration data for one declared production rule.

    A missing action maps to a Simple production aggregate. A present
    action maps to a Complex production aggregate. The mapper does not
    resolve the owning grammar or reject an unknown grammar id.
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
        description='The declared production name.',
    )

    # * attribute: grammar_id
    grammar_id: str | None = Field(
        default=None,
        description='The identifier of the one grammar that owns the production.',
    )

    # * attribute: spec
    spec: str | None = Field(
        default=None,
        description='The declared production specification.',
    )

    # * attribute: action
    action: str | None = Field(
        default=None,
        description='Declared action source; None means a Simple production.',
    )

    # * method: map
    def map(self, **overrides) -> SimpleProductionRuleAggregate | ComplexProductionRuleAggregate:
        '''
        Map this configuration to a Simple or Complex production aggregate.

        Declared fields present in ``overrides`` replace the stored values.
        Any other override is passed through to aggregate construction.
        A resulting action of ``None`` selects the Simple aggregate and is
        not passed to it.

        :param overrides: Field replacements and extra construction values.
        :type overrides: dict
        :return: The mapped production aggregate.
        :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        '''

        # Read the declared fields, then apply overrides for those keys.
        values = {
            'name': self.name,
            'grammar_id': self.grammar_id,
            'spec': self.spec,
            'action': self.action,
        }
        for key in ('name', 'grammar_id', 'spec', 'action'):
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
            return ComplexProductionRuleAggregate(
                name=values['name'],
                grammar_id=values['grammar_id'],
                spec=values['spec'],
                action=values['action'],
                **extra,
            )

        # Do not pass action into the Simple aggregate.
        return SimpleProductionRuleAggregate(
            name=values['name'],
            grammar_id=values['grammar_id'],
            spec=values['spec'],
            **extra,
        )

    # * method: from_model
    @classmethod
    def from_model(
            cls,
            model: SimpleProductionRule | ComplexProductionRule,
            **overrides,
        ) -> 'ProductionRuleConfigObject':
        '''
        Create production configuration data from a production rule or aggregate.

        Action is copied only from a complex production rule. Overrides are
        applied last.

        :param model: A simple or complex production rule, or either aggregate.
        :type model: SimpleProductionRule | ComplexProductionRule
        :param overrides: Field values that replace the copied data.
        :type overrides: dict
        :return: The production configuration object.
        :rtype: ProductionRuleConfigObject
        '''

        # Copy identity and specification. Copy action only for a complex rule.
        data = {
            'name': model.name,
            'grammar_id': model.grammar_id,
            'spec': model.spec,
            'action': model.action if isinstance(model, ComplexProductionRule) else None,
        }

        # Apply overrides last so they replace copied fields.
        data.update(overrides)

        # Validate into configuration data. Do not reshape a catalogue.
        return cls.model_validate(data)
