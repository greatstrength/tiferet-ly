"""Tiferet-Ly Grammar Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict, List

# ** app
from tiferet import (
    Aggregate,
    TransferObject,
)
from ..domain.grammar import Grammar

# *** mappers

# ** mapper: grammar_aggregate
class GrammarAggregate(Grammar, Aggregate):
    '''
    Mutable aggregate for a Grammar.

    Mutators mirror the operations domain events will call when updating
    a grammar's identity structure (start symbol and parent composition).
    '''

    # * method: set_start
    def set_start(self, start: str) -> None:
        '''
        Set the start symbol.

        :param start: The new start symbol name.
        :type start: str
        :return: None
        :rtype: None
        '''

        # Update the start symbol; validate_assignment=True handles re-validation.
        self.start = start

    # * method: set_parent_ids
    def set_parent_ids(self, parent_ids: List[str]) -> None:
        '''
        Replace the ordered parent grammar ids.

        :param parent_ids: The new ordered parent ids list.
        :type parent_ids: List[str]
        :return: None
        :rtype: None
        '''

        # Replace the parent ids list in full.
        self.parent_ids = list(parent_ids)


# ** mapper: grammar_config_object
class GrammarConfigObject(Grammar, TransferObject):
    '''
    Configuration data representation of a Grammar.

    No branching (Grammar has exactly one shape) and no reshape mechanism:
    ``parent_ids`` is a plain ``List[str]`` and validates directly.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {
            'exclude': {
                'id',
            },
        },
    }

    # * method: map
    def map(self, **overrides) -> GrammarAggregate:
        '''
        Map the grammar configuration data to a GrammarAggregate.

        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The mapped GrammarAggregate.
        :rtype: GrammarAggregate
        '''

        # Serialize without dropping None fields so domain construction —
        # not the mapper — rejects corrupted values.
        data = self.to_primitive(role='to_model', exclude_none=False)
        data.update(overrides)

        # Construct the grammar aggregate.
        return GrammarAggregate(**data)

    # * method: from_model
    @classmethod
    def from_model(cls, grammar: Grammar, **overrides) -> 'GrammarConfigObject':
        '''
        Create a GrammarConfigObject from a Grammar model or aggregate.

        :param grammar: The Grammar domain object.
        :type grammar: Grammar
        :param overrides: Additional field overrides.
        :type overrides: dict
        :return: The constructed GrammarConfigObject.
        :rtype: GrammarConfigObject
        '''

        # Create a new GrammarConfigObject from the model.
        return super().from_model(grammar, **overrides)
