"""Tiferet Ly Production Events"""

# *** imports

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.interfaces.production import ProductionService
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)

# *** constants

# ** constant: production_already_exists_id
PRODUCTION_ALREADY_EXISTS_ID = 'PRODUCTION_ALREADY_EXISTS'

# ** constant: production_not_found_id
PRODUCTION_NOT_FOUND_ID = 'PRODUCTION_NOT_FOUND'

# ** constant: production_action_not_supported_id
PRODUCTION_ACTION_NOT_SUPPORTED_ID = 'PRODUCTION_ACTION_NOT_SUPPORTED'

# *** functions

# ** function: matching_triples
def _matching_triples(rows, name: str, grammar_id: str, spec: str) -> list:
    '''
    Return catalogue rows whose name, grammar, and spec match, in catalogue order.

    :param rows: The production catalogue in declared order.
    :type rows: list
    :param name: The declared production name.
    :type name: str
    :param grammar_id: The grammar that owns the production.
    :type grammar_id: str
    :param spec: The production specification.
    :type spec: str
    :return: Matching rows, in the order they were walked.
    :rtype: list
    '''

    # Walk the catalogue. Do not sort, and do not use pair lookup.
    return [
        row
        for row in rows
        if row.name == name and row.grammar_id == grammar_id and row.spec == spec
    ]

# ** function: one_triple
def _one_triple(event, name: str, grammar_id: str, spec: str):
    '''
    Return the single catalogue row for a production triple.

    :param event: The production event performing the scan.
    :type event: ProductionEvent
    :param name: The declared production name.
    :type name: str
    :param grammar_id: The grammar that owns the production.
    :type grammar_id: str
    :param spec: The stored specification.
    :type spec: str
    :return: The matching production aggregate.
    :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    '''

    # Walk the catalogue. Pair lookup would hide a sibling alternative.
    matches = _matching_triples(
        event.production_service.list(),
        name,
        grammar_id,
        spec,
    )
    event.verify(
        len(matches) > 0,
        PRODUCTION_NOT_FOUND_ID,
        message=f'Production not found: {name} in grammar {grammar_id} with spec {spec}.',
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )
    event.verify(
        len(matches) == 1,
        PRODUCTION_ALREADY_EXISTS_ID,
        message=f'Production already exists: {name} in grammar {grammar_id} with spec {spec}.',
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )

    # One row is the write target.
    return matches[0]

# *** events

# ** event: production_event
class ProductionEvent(DomainEvent):
    '''
    Shared access for a production addressed by name, grammar, and spec.

    A repeated name under one grammar is another alternative, not a
    duplicate. These events do not ask whether a grammar start still
    resolves.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self, production_service: ProductionService) -> None:
        '''
        Initialize with the production service.

        :param production_service: The production service.
        :type production_service: ProductionService
        '''

        # Set the production service dependency.
        self.production_service = production_service

# ** event: add_production
class AddProduction(ProductionEvent):
    '''
    Declare one production alternative without checking a grammar start.

    An omitted or missing action is a simple production. A string action
    is a complex production. The same name and grammar may be declared
    again when the specification differs.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            action: str | None = None,
            **kwargs,
        ) -> SimpleProductionRuleAggregate | ComplexProductionRuleAggregate:
        '''
        Add a production when its name, grammar, and spec are not already stored.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that will own the production.
        :type grammar_id: str
        :param spec: The declared production specification.
        :type spec: str
        :param action: Action source. None selects a simple production.
        :type action: str | None
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved production aggregate.
        :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        '''

        # The triple is the identity. A different spec is not a duplicate.
        matches = _matching_triples(
            self.production_service.list(),
            name,
            grammar_id,
            spec,
        )
        self.verify(
            not matches,
            PRODUCTION_ALREADY_EXISTS_ID,
            message=f'Production already exists: {name} in grammar {grammar_id} with spec {spec}.',
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )

        # A string action is complex. Omitted and None stay simple.
        if isinstance(action, str):
            production = ComplexProductionRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                spec=spec,
                action=action,
            )
        else:
            production = SimpleProductionRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                spec=spec,
            )

        # Persist and return the same aggregate.
        self.production_service.save(production)
        return production

# ** event: list_productions
class ListProductions(ProductionEvent):
    '''
    Return every stored production in declared order.

    The list is not filtered by grammar or collapsed by name.
    '''

    # * method: execute
    def execute(
            self,
            **kwargs,
        ) -> list[SimpleProductionRuleAggregate | ComplexProductionRuleAggregate]:
        '''
        Return the production catalogue in the order the service already has.

        :param kwargs: Additional keyword arguments. Grammar id is ignored.
        :type kwargs: dict
        :return: The stored production aggregates.
        :rtype: list[SimpleProductionRuleAggregate | ComplexProductionRuleAggregate]
        '''

        # Do not sort or drop rows. Declared order is the service order.
        return self.production_service.list()

# ** event: get_productions
class GetProductions(ProductionEvent):
    '''
    Read every alternative of one name and grammar pair.

    Pair lookup on the service returns only the first alternative, so
    this event walks the catalogue instead.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            **kwargs,
        ) -> list[SimpleProductionRuleAggregate | ComplexProductionRuleAggregate]:
        '''
        Return every stored alternative of the name and grammar pair.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The matching production aggregates, in catalogue order.
        :rtype: list[SimpleProductionRuleAggregate | ComplexProductionRuleAggregate]
        '''

        # Keep relative order. Do not ask the pair-scoped getter.
        matches = [
            row
            for row in self.production_service.list()
            if row.name == name and row.grammar_id == grammar_id
        ]
        self.verify(
            bool(matches),
            PRODUCTION_NOT_FOUND_ID,
            message=f'Production not found: {name} in grammar {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Return every alternative, not the first pair.
        return matches

# ** event: set_production_spec
class SetProductionSpec(ProductionEvent):
    '''
    Replace the specification of one stored production alternative.

    The old triple stays the lookup key. Changing the specification does
    not ask whether a grammar start still resolves.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_spec'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            new_spec: str,
            **kwargs,
        ) -> SimpleProductionRuleAggregate | ComplexProductionRuleAggregate:
        '''
        Replace one stored specification and write that row back by its old triple.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The stored specification to find.
        :type spec: str
        :param new_spec: The replacement specification.
        :type new_spec: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated production aggregate.
        :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        '''

        # A missing or repeated triple is not rewritten.
        row = _one_triple(self, name, grammar_id, spec)

        # Change the spec, then replace the old triple in place.
        row.set_spec(new_spec)
        self.production_service.replace(name, grammar_id, spec, row)
        return row

# ** event: set_production_action
class SetProductionAction(ProductionEvent):
    '''
    Replace the action source of one complex production alternative.

    A simple production has no action, so the write is refused before
    save. The grammar start is not rechecked.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'action'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            action: str,
            **kwargs,
        ) -> ComplexProductionRuleAggregate:
        '''
        Replace a complex production action and save it.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The stored specification of the alternative.
        :type spec: str
        :param action: The replacement action source.
        :type action: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved complex production aggregate.
        :rtype: ComplexProductionRuleAggregate
        '''

        # A missing or repeated triple is not rewritten.
        row = _one_triple(self, name, grammar_id, spec)

        # A simple production cannot take an action.
        self.verify(
            isinstance(row, ComplexProductionRuleAggregate),
            PRODUCTION_ACTION_NOT_SUPPORTED_ID,
            message=(
                f'Production action is not supported for simple production '
                f'{name} in grammar {grammar_id} with spec {spec}.'
            ),
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )

        # Replace the action, persist, and return the same aggregate.
        row.set_action(action)
        self.production_service.save(row)
        return row
