"""Tiferet Ly Production Events"""

# *** imports

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.interfaces.grammar import GrammarService
from tiferet_ly.interfaces.production import ProductionService
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.utils.grammar import GrammarRuleSelector
from .. import assets as a

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

# ** function: one_triple_in
def _one_triple_in(event, rows, name: str, grammar_id: str, spec: str):
    '''
    Return the single row for a production triple in an already loaded catalogue.

    :param event: The production event performing the scan.
    :type event: ProductionEvent
    :param rows: The production catalogue in declared order.
    :type rows: list
    :param name: The declared production name.
    :type name: str
    :param grammar_id: The grammar that owns the production.
    :type grammar_id: str
    :param spec: The stored specification.
    :type spec: str
    :return: The matching production aggregate.
    :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    '''

    # Walk the supplied catalogue. Pair lookup would hide a sibling alternative.
    matches = _matching_triples(
        rows,
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

    # Load the catalogue, then keep the same triple scan as a supplied list.
    return _one_triple_in(
        event,
        event.production_service.list(),
        name,
        grammar_id,
        spec,
    )

# ** function: projected_row
def _projected_row(row, **changes):
    '''
    Build a new aggregate of the same class with the given field changes.

    The loaded row is not mutated. A complex row keeps its action. A simple
    row is not given one.

    :param row: The loaded production aggregate.
    :type row: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    :param changes: Field values that replace the copied data.
    :type changes: dict
    :return: A new aggregate of the same class.
    :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    '''

    # Copy the stored fields, then apply only the requested changes.
    values = {
        'name': row.name,
        'grammar_id': row.grammar_id,
        'spec': row.spec,
    }
    values.update(changes)

    # A complex row keeps its action. A simple row has none to copy.
    if isinstance(row, ComplexProductionRuleAggregate):
        return type(row)(
            name=values['name'],
            grammar_id=values['grammar_id'],
            spec=values['spec'],
            action=row.action,
        )
    return type(row)(
        name=values['name'],
        grammar_id=values['grammar_id'],
        spec=values['spec'],
    )

# ** function: catalogue_with_row
def _catalogue_with_row(rows, matched, replacement=None) -> list:
    '''
    Return a new catalogue with the matched object omitted or replaced.

    Other rows keep their identity and relative order. The loaded aggregate
    is not mutated.

    :param rows: The production catalogue in declared order.
    :type rows: list
    :param matched: The loaded aggregate to omit or replace.
    :type matched: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    :param replacement: The aggregate to put in that position, if any.
    :type replacement: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate | None
    :return: The post-mutation catalogue.
    :rtype: list
    '''

    # Walk declared order. Identity, not equality, picks the matched row.
    catalogue = []
    for row in rows:
        if row is matched:
            if replacement is not None:
                catalogue.append(replacement)
            continue
        catalogue.append(row)
    return catalogue

# *** events

# ** event: production_event
class ProductionEvent(DomainEvent):
    '''
    Shared access for a production addressed by name, grammar, and spec.

    A repeated name under one grammar is another alternative, not a
    duplicate. Ordinary writes leave start resolution alone. Shrinking
    writes use this base to check every persisted grammar before they
    save or delete.
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

    # * method: _assert_starts_resolve
    def _assert_starts_resolve(self, productions: list, grammars: list) -> None:
        '''
        Verify every persisted grammar start still names an effective production.

        The scan follows the grammar list as given, including a dialect that
        inherited its start. It does not resolve one candidate grammar, and
        it does not save or delete.

        :param productions: The post-mutation production catalogue.
        :type productions: list
        :param grammars: The persisted grammar list, in list order.
        :type grammars: list
        :return: None
        :rtype: None
        '''

        # The first unresolved start stops the scan. Do not filter the list.
        for grammar in grammars:
            selected = GrammarRuleSelector.select_productions(
                grammar,
                grammars,
                productions,
            )
            self.verify(
                any(row.name == grammar.start for row in selected),
                a.grammar.GRAMMAR_START_NOT_FOUND_ID,
                message=(
                    f'Grammar start not found: {grammar.start} '
                    f'in grammar {grammar.id}.'
                ),
                grammar_id=grammar.id,
                start=grammar.start,
            )

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

# ** event: remove_production
class RemoveProduction(ProductionEvent):
    '''
    Remove one production alternative after every persisted start still resolves.

    A dialect can inherit the removed name. The check uses the catalogue
    without that row, and a failed check does not delete.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(
            self,
            production_service: ProductionService,
            grammar_service: GrammarService,
        ) -> None:
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        '''

        # Keep ordinary construction on the base.
        super().__init__(production_service)

        # Grammars are read only to resolve persisted starts.
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            **kwargs,
        ) -> tuple[str, str, str]:
        '''
        Delete one alternative when every persisted start still resolves.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The specification of the alternative to remove.
        :type spec: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The removed name, grammar, and spec.
        :rtype: tuple[str, str, str]
        '''

        # A missing or repeated triple is not deleted.
        rows = self.production_service.list()
        row = _one_triple_in(self, rows, name, grammar_id, spec)

        # Omit that object. Do not mutate it, and do not drop its siblings.
        catalogue = _catalogue_with_row(rows, row)
        self._assert_starts_resolve(
            catalogue,
            self.grammar_service.list(),
        )

        # Delete only this alternative, then return the triple.
        self.production_service.delete_alternative(name, grammar_id, spec)
        return (name, grammar_id, spec)

# ** event: rename_production
class RenameProduction(ProductionEvent):
    '''
    Rename one production alternative after every persisted start still resolves.

    The loaded row keeps its old name until the check returns. A failed
    check does not save or replace.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(
            self,
            production_service: ProductionService,
            grammar_service: GrammarService,
        ) -> None:
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        '''

        # Keep ordinary construction on the base.
        super().__init__(production_service)

        # Grammars are read only to resolve persisted starts.
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_name'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            new_name: str,
            **kwargs,
        ) -> SimpleProductionRuleAggregate | ComplexProductionRuleAggregate:
        '''
        Rename one alternative when every persisted start still resolves.

        :param name: The stored production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The stored specification.
        :type spec: str
        :param new_name: The replacement production name.
        :type new_name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The replaced production aggregate.
        :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        '''

        # A missing or repeated triple is not rewritten.
        rows = self.production_service.list()
        row = _one_triple_in(self, rows, name, grammar_id, spec)

        # Project the new name in place. Leave the loaded row unchanged.
        catalogue = _catalogue_with_row(
            rows,
            row,
            replacement=_projected_row(row, name=new_name),
        )
        self._assert_starts_resolve(
            catalogue,
            self.grammar_service.list(),
        )

        # Rename the loaded row, then replace the old triple.
        row.rename(new_name)
        self.production_service.replace(name, grammar_id, spec, row)
        return row

# ** event: reassign_production_grammar
class ReassignProductionGrammar(ProductionEvent):
    '''
    Move one production alternative after every persisted start still resolves.

    The destination need not name a stored grammar. The loaded row keeps
    its grammar until the check returns, and a failed check does not save.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(
            self,
            production_service: ProductionService,
            grammar_service: GrammarService,
        ) -> None:
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        '''

        # Keep ordinary construction on the base.
        super().__init__(production_service)

        # Grammars are read only to resolve persisted starts.
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_grammar_id'])
    def execute(
            self,
            name: str,
            grammar_id: str,
            spec: str,
            new_grammar_id: str,
            **kwargs,
        ) -> SimpleProductionRuleAggregate | ComplexProductionRuleAggregate:
        '''
        Reassign one alternative when every persisted start still resolves.

        :param name: The stored production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The stored specification.
        :type spec: str
        :param new_grammar_id: The replacement grammar identifier.
        :type new_grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The replaced production aggregate.
        :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
        '''

        # A missing or repeated triple is not rewritten.
        rows = self.production_service.list()
        row = _one_triple_in(self, rows, name, grammar_id, spec)

        # Project the new grammar in place. Leave the loaded row unchanged.
        catalogue = _catalogue_with_row(
            rows,
            row,
            replacement=_projected_row(row, grammar_id=new_grammar_id),
        )
        self._assert_starts_resolve(
            catalogue,
            self.grammar_service.list(),
        )

        # Reassign the loaded row, then replace the old triple.
        row.reassign_grammar(new_grammar_id)
        self.production_service.replace(name, grammar_id, spec, row)
        return row
