"""Tiferet-Ly Production Rule Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional, Union

# ** infra
from pydantic import Field

# ** app
from tiferet import TransferObject
from ..domain.production import (
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)
from .core import NamedRuleAggregate

# *** mappers

# ** mapper: production_rule_aggregate
class ProductionRuleAggregate(ProductionRule, NamedRuleAggregate):
    '''
    Mutable aggregate base for a production rule.

    Shared name/grammar mutators come from :class:`NamedRuleAggregate`.
    ``set_spec`` is shared by both variants; ``set_action`` lives only
    on :class:`ComplexProductionRuleAggregate`.
    '''

    # * method: set_spec
    def set_spec(self, spec: str) -> None:
        '''
        Set the grammar-pattern string.

        :param spec: The new grammar-pattern string.
        :type spec: str
        :return: None
        :rtype: None
        '''

        # Update the spec; validate_assignment=True handles re-validation.
        self.spec = spec


# ** mapper: simple_production_rule_aggregate
class SimpleProductionRuleAggregate(SimpleProductionRule, ProductionRuleAggregate):
    '''
    Mutable aggregate for a simple production rule.
    '''

    pass


# ** mapper: complex_production_rule_aggregate
class ComplexProductionRuleAggregate(ComplexProductionRule, ProductionRuleAggregate):
    '''
    Mutable aggregate for a complex production rule.
    '''

    # * method: set_action
    def set_action(self, action: str) -> None:
        '''
        Set the encoded source fragment that runs when the production matches.

        :param action: The new action source fragment.
        :type action: str
        :return: None
        :rtype: None
        '''

        # Update the action; validate_assignment=True handles re-validation.
        self.action = action


# ** mapper: production_rule_config_object
class ProductionRuleConfigObject(TransferObject):
    '''
    Configuration data representation of a production rule.

    Deliberately does not subclass :class:`ProductionRule`, whose base
    carries no ``spec``: a config entry must represent either variant
    before it is known which one it is. ``.map()`` branches on ``action``'s
    presence with no separate discriminator field.
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
        description='The bare rule name PLY expects after its p_ prefix.',
    )

    # * attribute: grammar_id
    grammar_id: str = Field(
        ...,
        description='The id of the single Grammar this rule is declared under.',
    )

    # * attribute: spec
    spec: str = Field(
        ...,
        description="The grammar-pattern string in PLY's own docstring grammar notation.",
    )

    # * attribute: action
    action: Optional[str] = Field(
        default=None,
        description='An encoded source fragment that runs when the production matches.',
    )

    # * method: map
    def map(self, **overrides) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Map the production rule configuration data to a production rule aggregate.

        Branches on ``action``'s presence: a set action yields
        :class:`ComplexProductionRuleAggregate`, otherwise
        :class:`SimpleProductionRuleAggregate`.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped simple or complex production rule aggregate.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Serialize via the to_model role without dropping None fields so
        # domain construction — not the mapper — rejects corrupted values.
        data = self.to_primitive(role='to_model', exclude_none=False)
        data.update(overrides)

        # Construct the complex aggregate when an action is present.
        if data.get('action') is not None:
            return ComplexProductionRuleAggregate(
                name=data['name'],
                grammar_id=data['grammar_id'],
                spec=data['spec'],
                action=data['action'],
            )

        # Construct the simple aggregate otherwise (drop action if absent/None).
        return SimpleProductionRuleAggregate(
            name=data['name'],
            grammar_id=data['grammar_id'],
            spec=data['spec'],
        )

    # * method: from_model
    @classmethod
    def from_model(cls, production: ProductionRule, **overrides) -> 'ProductionRuleConfigObject':
        '''
        Create a ProductionRuleConfigObject from a production rule model or aggregate.

        :param production: The production rule domain object or aggregate.
        :type production: ProductionRule
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The constructed ProductionRuleConfigObject.
        :rtype: ProductionRuleConfigObject
        '''

        # Dump the model and let TransferObject construct the config entry.
        return super().from_model(production, **overrides)
