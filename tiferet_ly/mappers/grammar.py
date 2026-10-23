"""Tiferet Ly Grammar Mappers"""

# *** imports

# ** core
from typing import Any, ClassVar, Dict

# ** infra
from tiferet import (
    Aggregate,
    TransferObject,
)

# ** app
from tiferet_ly.domain import Grammar

# *** mappers

# ** mapper: grammar_aggregate
class GrammarAggregate(Grammar, Aggregate):
    '''
    A mutable grammar that stores identity, ordered parents, a start name,
    an optional ignore string, and the grammar-own layout profile inherited
    from Grammar.

    Changing those fields does not check that parents exist, that the graph
    is acyclic, that the start name is a production, or that ignore is a
    valid expression. Ignore is this grammar's own value. It is not taken
    from parent_ids. Changing start or parent_ids does not copy layout or
    ignore from parent_ids.
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

    Mapping keeps parent order and a declared ignore string, and drops only
    the grammar id. A missing or null ignore stays None and is omitted when
    serialized. Mapping does not resolve parents, the start production, or
    ignore. A declared layout profile is copied as stored; a missing or null
    layout stays None, is omitted when serialized, and is never invented or
    taken from parent_ids.
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

        A declared ignore string is passed through; a missing ignore is left
        to the aggregate default None. A declared layout profile is kept, and
        a missing one is left to the default None; no profile is invented.
        Mapping does not resolve parents, the start production, or a parent's
        layout or ignore.

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

        Ignore is copied as stored on the model and is not composed from
        parent_ids. Layout is copied when the model has one, and none is
        invented when it does not. Parents are not reshaped and start is not
        resolved.

        :param model: A grammar domain object or grammar aggregate.
        :type model: Grammar
        :param overrides: Field values that replace the copied data.
        :type overrides: dict
        :return: The grammar configuration object.
        :rtype: GrammarConfigObject
        '''

        # Copy the lean fields. Do not reshape parents or resolve start.
        return super().from_model(model, **overrides)
