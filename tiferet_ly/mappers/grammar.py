"""Tiferet Ly Grammar Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** app
from tiferet import (
    Aggregate,
    TransferObject,
)
from tiferet_ly.domain import Grammar

# *** mappers

# ** mapper: grammar_aggregate
class GrammarAggregate(Grammar, Aggregate):
    '''
    A mutable grammar that stores identity, ordered parents, and a start name.

    Changing those fields does not check that parents exist, that the graph
    is acyclic, or that the start name is a production.
    '''

    # * method: set_start
    def set_start(self, start: str) -> None:
        '''
        Replace the declared start-production name.

        :param start: The new start name.
        :type start: str
        :return: None
        :rtype: None
        '''

        # Assign the start name without resolving a production.
        self.start = start

    # * method: set_parent_ids
    def set_parent_ids(self, parent_ids: list[str]) -> None:
        '''
        Replace the ordered parent identifiers.

        :param parent_ids: The new parent identifiers, in declared order.
        :type parent_ids: list[str]
        :return: None
        :rtype: None
        '''

        # Store a new list so later caller mutation does not change parents.
        self.parent_ids = list(parent_ids)

# ** mapper: grammar_config_object
class GrammarConfigObject(Grammar, TransferObject):
    '''
    Configuration data for one declared grammar.

    Mapping keeps parent order and drops only the grammar id. It does not
    resolve parents or the start production.
    '''

    # * attribute: _ROLES
    _ROLES: ClassVar[Dict[str, Dict[str, Any]]] = {
        'to_model': {},
        'to_data': {
            'by_alias': True,
            'exclude': {'id'},
        },
    }

    # * method: map
    def map(self, **overrides) -> GrammarAggregate:
        '''
        Map this configuration to a grammar aggregate.

        :param overrides: Field replacements and extra construction values.
        :type overrides: dict
        :return: The mapped grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Delegate without querying another grammar or a rule catalogue.
        return super().map(GrammarAggregate, **overrides)

    # * method: from_model
    @classmethod
    def from_model(cls, model: Grammar, **overrides) -> 'GrammarConfigObject':
        '''
        Create grammar configuration data from a grammar or aggregate.

        :param model: A grammar domain object or grammar aggregate.
        :type model: Grammar
        :param overrides: Field values that replace the copied data.
        :type overrides: dict
        :return: The grammar configuration object.
        :rtype: GrammarConfigObject
        '''

        # Copy the lean fields. Do not reshape parents or resolve start.
        return super().from_model(model, **overrides)
