"""Tiferet-Ly Production Domain Events"""

# *** imports

# ** core
from typing import List, Optional, Union

# ** app
from tiferet.events.core import DomainEvent
from .. import assets as a
from ..interfaces.grammar import GrammarService
from ..interfaces.production import ProductionService
from ..mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from ..utils.grammar import GrammarRuleSelector

# *** functions

# ** function: production_matches
def production_matches(
        production: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate],
        name: str,
        grammar_id: str,
        spec: str) -> bool:
    '''
    Return whether a production is the ``(name, grammar_id, spec)`` triple.

    :param production: The production aggregate to compare.
    :type production: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
    :param name: The production name.
    :type name: str
    :param grammar_id: The grammar the rule is declared under.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :return: True when all three identity fields match.
    :rtype: bool
    '''

    # Compare the three identity fields.
    return (
        production.name == name
        and production.grammar_id == grammar_id
        and production.spec == spec
    )


# ** function: find_productions
def find_productions(
        productions: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]],
        name: str,
        grammar_id: str,
        spec: str) -> List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]:
    '''
    Return every catalogue entry matching the identity triple.

    :param productions: The unfiltered production catalogue.
    :type productions: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]
    :param name: The production name.
    :type name: str
    :param grammar_id: The grammar the rule is declared under.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :return: Matching productions in declared order.
    :rtype: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]
    '''

    # Scan the catalogue for the identity triple.
    return [
        production
        for production in productions
        if production_matches(production, name, grammar_id, spec)
    ]


# ** function: assert_starts_resolve
def assert_starts_resolve(
        event: DomainEvent,
        grammars: list,
        productions: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]) -> None:
    '''
    Verify every persisted grammar's start is still in its effective set.

    :param event: The domain event used to raise a structured error.
    :type event: DomainEvent
    :param grammars: The persisted grammar catalogue.
    :type grammars: list
    :param productions: The candidate post-mutation production catalogue.
    :type productions: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]
    :return: None
    :rtype: None
    '''

    # Check each persisted grammar against the post-mutation catalogue.
    for grammar in grammars:

        # Resolve the effective productions for this grammar's ancestry.
        effective = GrammarRuleSelector.select_productions(
            grammar,
            grammars,
            productions,
        )

        # Verify the grammar's start still names an effective production.
        event.verify(
            any(production.name == grammar.start for production in effective),
            a.error.GRAMMAR_START_NOT_FOUND_ID,
            message=f'Grammar start not found: {grammar.start} on {grammar.id}.',
            id=grammar.id,
            start=grammar.start,
        )


# *** events

# ** event: production_event
class ProductionEvent(DomainEvent):
    '''
    Base event providing the shared ProductionService dependency.

    Production identity is the triple ``(name, grammar_id, spec)`` because
    a name may repeat as alternatives inside one grammar.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self, production_service: ProductionService):
        '''
        Initialize the production event with its shared service dependency.

        :param production_service: The production service shared across events.
        :type production_service: ProductionService
        '''

        # Set the production service dependency.
        self.production_service = production_service

    # * method: _require_production
    def _require_production(
            self,
            name: str,
            grammar_id: str,
            spec: str) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Scan the catalogue for exactly one matching identity triple.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :return: The unique matching production.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Scan the unfiltered catalogue for the identity triple.
        matches = find_productions(
            self.production_service.list(),
            name,
            grammar_id,
            spec,
        )

        # Zero matches is not found; more than one is data that should not persist.
        self.verify(
            len(matches) > 0,
            a.error.PRODUCTION_NOT_FOUND_ID,
            message=f'Production not found: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )
        self.verify(
            len(matches) == 1,
            a.error.PRODUCTION_ALREADY_EXISTS_ID,
            message=f'Duplicate production triple: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )

        # Return the unique match.
        return matches[0]


# ** event: add_production
class AddProduction(ProductionEvent):
    '''
    Event to append a production alternative under a grammar.

    A new spec with an existing name is the normal case. The owning grammar
    need not exist yet, and this write does not re-check start.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec'])
    def execute(self,
            name: str,
            grammar_id: str,
            spec: str,
            action: Optional[str] = None,
            **kwargs) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Add a new production alternative.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :param action: Optional encoded action source for a complex production.
        :type action: Optional[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created production aggregate.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Reject an identical alternative already in the catalogue.
        matches = find_productions(
            self.production_service.list(),
            name,
            grammar_id,
            spec,
        )
        self.verify(
            len(matches) == 0,
            a.error.PRODUCTION_ALREADY_EXISTS_ID,
            message=f'Production already exists: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )

        # Construct the matching simple or complex aggregate.
        if action is None:
            production = SimpleProductionRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                spec=spec,
            )
        else:
            production = ComplexProductionRuleAggregate(
                name=name,
                grammar_id=grammar_id,
                spec=spec,
                action=action,
            )

        # Persist the new alternative.
        self.production_service.save(production)

        # Return the created production.
        return production


# ** event: get_productions
class GetProductions(ProductionEvent):
    '''
    Event to retrieve every alternative of a production name under a grammar.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id'])
    def execute(self,
            name: str,
            grammar_id: str,
            **kwargs) -> List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]:
        '''
        Retrieve every matching production alternative.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rules are declared under.
        :type grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: Matching productions in declared order.
        :rtype: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]
        '''

        # Filter the catalogue to this name under this grammar.
        matches = [
            production
            for production in self.production_service.list()
            if production.name == name and production.grammar_id == grammar_id
        ]

        # Verify at least one alternative exists.
        self.verify(
            len(matches) > 0,
            a.error.PRODUCTION_NOT_FOUND_ID,
            message=f'Production not found: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
        )

        # Return every matching alternative in declared order.
        return matches


# ** event: list_productions
class ListProductions(ProductionEvent):
    '''
    Event to list every production rule unfiltered, in declared order.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]:
        '''
        List every stored production rule.

        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: All stored production aggregates.
        :rtype: List[Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]]
        '''

        # Return the unfiltered catalogue.
        return self.production_service.list()


# ** event: set_production_spec
class SetProductionSpec(ProductionEvent):
    '''
    Event to replace one alternative's spec without changing its name.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_spec'])
    def execute(self,
            name: str,
            grammar_id: str,
            spec: str,
            new_spec: str,
            **kwargs) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Set a production alternative's spec.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The current production spec.
        :type spec: str
        :param new_spec: The new production spec.
        :type new_spec: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated production aggregate.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Load the unique alternative and apply the spec mutator.
        production = self._require_production(name, grammar_id, spec)
        production.set_spec(new_spec)
        self.production_service.save(production)

        # Return the updated production.
        return production


# ** event: set_production_action
class SetProductionAction(ProductionEvent):
    '''
    Event to replace a complex production's action source.

    Simple productions cannot gain an action in place; that is a remove-and-add.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'action'])
    def execute(self,
            name: str,
            grammar_id: str,
            spec: str,
            action: str,
            **kwargs) -> ComplexProductionRuleAggregate:
        '''
        Set a complex production alternative's action.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :param action: The new encoded action source.
        :type action: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated complex production aggregate.
        :rtype: ComplexProductionRuleAggregate
        '''

        # Load the unique alternative and verify it already carries an action.
        production = self._require_production(name, grammar_id, spec)
        self.verify(
            isinstance(production, ComplexProductionRuleAggregate),
            a.error.PRODUCTION_ACTION_NOT_SUPPORTED_ID,
            message=f'Production action is not supported: {name} under {grammar_id}.',
            name=name,
            grammar_id=grammar_id,
            spec=spec,
        )

        # Apply the action mutator and persist.
        production.set_action(action)
        self.production_service.save(production)

        # Return the updated production.
        return production


# ** event: remove_production
class RemoveProduction(ProductionEvent):
    '''
    Event to delete one production alternative after the start check passes.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(self,
            production_service: ProductionService,
            grammar_service: GrammarService):
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service used for the start check.
        :type grammar_service: GrammarService
        '''

        # Set both service dependencies.
        super().__init__(production_service)
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec'])
    def execute(self, name: str, grammar_id: str, spec: str, **kwargs) -> tuple:
        '''
        Delete one production alternative.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The identity that was requested for deletion.
        :rtype: tuple
        '''

        # Confirm the alternative exists before computing the post-mutation set.
        self._require_production(name, grammar_id, spec)

        # Build the catalogue as it would look after this delete.
        remaining = [
            production
            for production in self.production_service.list()
            if not production_matches(production, name, grammar_id, spec)
        ]

        # Refuse the delete when any persisted start would become unresolved.
        assert_starts_resolve(self, self.grammar_service.list(), remaining)

        # Persist the delete through the pair-keyed service surface.
        self.production_service.delete(name, grammar_id)

        # Return the identity that was given.
        return (name, grammar_id, spec)


# ** event: rename_production
class RenameProduction(ProductionEvent):
    '''
    Event to rename one production alternative after the start check passes.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(self,
            production_service: ProductionService,
            grammar_service: GrammarService):
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service used for the start check.
        :type grammar_service: GrammarService
        '''

        # Set both service dependencies.
        super().__init__(production_service)
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_name'])
    def execute(self,
            name: str,
            grammar_id: str,
            spec: str,
            new_name: str,
            **kwargs) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Rename one production alternative.

        :param name: The current production name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :param new_name: The new production name.
        :type new_name: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated production aggregate.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Load the unique alternative that will be renamed.
        production = self._require_production(name, grammar_id, spec)

        # Apply the rename on a copy of the catalogue, then check starts.
        production.rename(new_name)
        remaining = [
            item
            for item in self.production_service.list()
            if not production_matches(item, name, grammar_id, spec)
        ]
        remaining.append(production)
        assert_starts_resolve(self, self.grammar_service.list(), remaining)

        # Persist the renamed alternative.
        self.production_service.save(production)

        # Return the updated production.
        return production


# ** event: reassign_production_grammar
class ReassignProductionGrammar(ProductionEvent):
    '''
    Event to move one production alternative after the start check passes.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(self,
            production_service: ProductionService,
            grammar_service: GrammarService):
        '''
        Initialize with the production and grammar services.

        :param production_service: The production service.
        :type production_service: ProductionService
        :param grammar_service: The grammar service used for the start check.
        :type grammar_service: GrammarService
        '''

        # Set both service dependencies.
        super().__init__(production_service)
        self.grammar_service = grammar_service

    # * method: execute
    @DomainEvent.parameters_required(['name', 'grammar_id', 'spec', 'new_grammar_id'])
    def execute(self,
            name: str,
            grammar_id: str,
            spec: str,
            new_grammar_id: str,
            **kwargs) -> Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]:
        '''
        Reassign one production alternative to another grammar.

        :param name: The production name.
        :type name: str
        :param grammar_id: The grammar the rule is currently declared under.
        :type grammar_id: str
        :param spec: The production spec.
        :type spec: str
        :param new_grammar_id: The grammar the rule should be declared under.
        :type new_grammar_id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated production aggregate.
        :rtype: Union[SimpleProductionRuleAggregate, ComplexProductionRuleAggregate]
        '''

        # Load the unique alternative that will be reassigned.
        production = self._require_production(name, grammar_id, spec)

        # Apply the reassignment on a copy of the catalogue, then check starts.
        production.reassign_grammar(new_grammar_id)
        remaining = [
            item
            for item in self.production_service.list()
            if not production_matches(item, name, grammar_id, spec)
        ]
        remaining.append(production)
        assert_starts_resolve(self, self.grammar_service.list(), remaining)

        # Persist the reassigned alternative.
        self.production_service.save(production)

        # Return the updated production.
        return production
