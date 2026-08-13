"""Tiferet-Ly Production Rule Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, Optional, Union

# ** infra
from pydantic import Field

# ** app
from tiferet.mappers.core import (
    Aggregate,
    TransferObject,
)
from ..domain.production import (
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)

# *** mappers

# ** mapper: production_rule_aggregate
class ProductionRuleAggregate(ProductionRule, Aggregate):
    '''
    Mutable aggregate for a production rule.

    Carries no domain-specific mutators beyond the inherited
    ``set_attribute`` / ``to_dict`` surface; nothing in the current
    roadmap edits a loaded rule in place. Concrete simple/complex field
    sets live on the domain variants produced by
    :meth:`ProductionRuleConfigObject.map`.
    '''

    pass


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
    def map(self, **overrides) -> Union[SimpleProductionRule, ComplexProductionRule]:
        '''
        Map the production rule configuration data to a domain production rule.

        Branches on ``action``'s presence: a set action yields
        :class:`ComplexProductionRule`, otherwise
        :class:`SimpleProductionRule`.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped simple or complex production rule.
        :rtype: Union[SimpleProductionRule, ComplexProductionRule]
        '''

        # Serialize via the to_model role without dropping None fields so
        # domain construction — not the mapper — rejects corrupted values.
        data = self.to_primitive(role='to_model', exclude_none=False)
        data.update(overrides)

        # Construct the complex variant when an action is present.
        if data.get('action') is not None:
            return ComplexProductionRule(
                name=data['name'],
                grammar_id=data['grammar_id'],
                spec=data['spec'],
                action=data['action'],
            )

        # Construct the simple variant otherwise (drop action if absent/None).
        return SimpleProductionRule(
            name=data['name'],
            grammar_id=data['grammar_id'],
            spec=data['spec'],
        )

    # * method: from_model
    @classmethod
    def from_model(cls, production: ProductionRule, **overrides) -> 'ProductionRuleConfigObject':
        '''
        Create a ProductionRuleConfigObject from a production rule model or aggregate.

        :param production: The production rule domain object.
        :type production: ProductionRule
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The constructed ProductionRuleConfigObject.
        :rtype: ProductionRuleConfigObject
        '''

        # Dump the model and let TransferObject construct the config entry.
        return super().from_model(production, **overrides)
