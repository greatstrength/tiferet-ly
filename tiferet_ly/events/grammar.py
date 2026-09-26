"""Tiferet Ly Grammar Events"""

# *** imports

# ** app
from tiferet import DomainEvent
from tiferet_ly.interfaces.grammar import GrammarService
from tiferet_ly.interfaces.production import ProductionService
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ProductionRuleAggregate
from tiferet_ly.utils.grammar import GrammarRuleSelector
from .. import assets as a

# *** events

# ** event: grammar_event
class GrammarEvent(DomainEvent):
    '''
    Shared grammar access for writes that must resolve a candidate start.

    Start resolution asks whether this grammar's start names an effective
    production. It does not scan every persisted grammar for its own start.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(self, grammar_service: GrammarService) -> None:
        '''
        Initialize with the grammar service.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        '''

        # Set the grammar service dependency.
        self.grammar_service = grammar_service

    # * method: _verify_start_resolves
    def _verify_start_resolves(
            self,
            grammar: GrammarAggregate,
            grammars: list[GrammarAggregate],
            productions: list[ProductionRuleAggregate],
        ) -> None:
        '''
        Verify the candidate start names an effective production.

        :param grammar: The candidate grammar to resolve.
        :type grammar: GrammarAggregate
        :param grammars: The grammar catalogue passed to selection.
        :type grammars: list[GrammarAggregate]
        :param productions: The production catalogue passed to selection.
        :type productions: list[ProductionRuleAggregate]
        :return: None
        :rtype: None
        '''

        # Select effective productions for this candidate only.
        selected = GrammarRuleSelector.select_productions(
            grammar,
            grammars,
            productions,
        )

        # The candidate start must name one of those productions.
        self.verify(
            any(production.name == grammar.start for production in selected),
            a.grammar.GRAMMAR_START_NOT_FOUND_ID,
            message=f'Grammar {grammar.id} start {grammar.start} does not resolve.',
            id=grammar.id,
            start=grammar.start,
        )

# ** event: add_grammar
class AddGrammar(GrammarEvent):
    '''
    Add a grammar after parent, cycle, and candidate-start checks.

    A missing parent or a cycle is rejected before save. A production that
    names the new grammar is visible to start resolution even when that
    grammar is not yet in the stored catalogue.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(
            self,
            grammar_service: GrammarService,
            production_service: ProductionService,
        ) -> None:
        '''
        Initialize with grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service.
        :type production_service: ProductionService
        '''

        # Keep the shared grammar service on the base.
        super().__init__(grammar_service)

        # Productions are read only to resolve the candidate start.
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'start'])
    def execute(
            self,
            id: str,
            start: str,
            parent_ids: list[str] | None = None,
            **kwargs,
        ) -> GrammarAggregate:
        '''
        Add a grammar when its parents, graph, and start are sound.

        :param id: The grammar identifier.
        :type id: str
        :param start: The declared start-production name.
        :type start: str
        :param parent_ids: The ordered parent identifiers, if any.
        :type parent_ids: list[str] | None
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Reject an identifier that is already stored.
        self.verify(
            not self.grammar_service.exists(id),
            a.grammar.GRAMMAR_ALREADY_EXISTS_ID,
            message=f'Grammar {id} already exists.',
            id=id,
        )

        # Omitted and None both become an empty parent list.
        parent_ids = parent_ids or []

        # A missing parent fails before the cycle check.
        # The candidate is not stored yet, so a self-parent is a cycle.
        for parent_id in parent_ids:
            self.verify(
                parent_id == id or self.grammar_service.exists(parent_id),
                a.grammar.GRAMMAR_PARENT_NOT_FOUND_ID,
                message=f'Grammar parent {parent_id} was not found.',
                parent_id=parent_id,
            )

        # Cycle against the stored catalogue. Do not insert the candidate.
        grammars = self.grammar_service.list()
        self.verify(
            not GrammarRuleSelector.has_cycle(id, parent_ids, grammars),
            a.grammar.GRAMMAR_CYCLE_DETECTED_ID,
            message=f'Grammar {id} would cycle.',
            id=id,
        )

        # Build the candidate before start resolution or save.
        grammar = GrammarAggregate(
            id=id,
            parent_ids=parent_ids,
            start=start,
        )

        # Resolve start for this candidate only.
        self._verify_start_resolves(
            grammar,
            grammars,
            self.production_service.list(),
        )

        # Persist and return the same aggregate.
        self.grammar_service.save(grammar)
        return grammar

# ** event: set_grammar_parent_ids
class SetGrammarParentIds(GrammarEvent):
    '''
    Replace a grammar's parents after existence, cycle, and start checks.

    The candidate parent list is the cycle frontier, not the persisted
    parents. Start resolution still checks only this grammar.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(
            self,
            grammar_service: GrammarService,
            production_service: ProductionService,
        ) -> None:
        '''
        Initialize with grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service.
        :type production_service: ProductionService
        '''

        # Keep the shared grammar service on the base.
        super().__init__(grammar_service)

        # Productions are read only to resolve the candidate start.
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'parent_ids'])
    def execute(
            self,
            id: str,
            parent_ids: list[str],
            **kwargs,
        ) -> GrammarAggregate:
        '''
        Replace parent identifiers when the candidate graph still resolves.

        :param id: The grammar identifier.
        :type id: str
        :param parent_ids: The candidate parent identifiers, in declared order.
        :type parent_ids: list[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # A missing grammar is not updated.
        grammar = self.grammar_service.get(id)
        self.verify(
            grammar is not None,
            a.grammar.GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar {id} was not found.',
            id=id,
        )

        # A missing parent fails before the cycle check.
        for parent_id in parent_ids:
            self.verify(
                parent_id == id or self.grammar_service.exists(parent_id),
                a.grammar.GRAMMAR_PARENT_NOT_FOUND_ID,
                message=f'Grammar parent {parent_id} was not found.',
                parent_id=parent_id,
            )

        # The frontier is the candidate list, not the persisted parents.
        self.verify(
            not GrammarRuleSelector.has_cycle(
                id,
                parent_ids,
                self.grammar_service.list(),
            ),
            a.grammar.GRAMMAR_CYCLE_DETECTED_ID,
            message=f'Grammar {id} would cycle.',
            id=id,
        )

        # Mutate first so start resolution sees the candidate parents.
        grammar.set_parent_ids(parent_ids)

        # Resolve start for this candidate only. Do not save on failure.
        self._verify_start_resolves(
            grammar,
            self.grammar_service.list(),
            self.production_service.list(),
        )

        # Persist and return the mutated aggregate.
        self.grammar_service.save(grammar)
        return grammar

# ** event: set_grammar_start
class SetGrammarStart(GrammarEvent):
    '''
    Replace a grammar's start name when that name resolves.

    The check uses the current effective productions for this grammar.
    It does not revisit parents or other grammars' start names.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(
            self,
            grammar_service: GrammarService,
            production_service: ProductionService,
        ) -> None:
        '''
        Initialize with grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service.
        :type production_service: ProductionService
        '''

        # Keep the shared grammar service on the base.
        super().__init__(grammar_service)

        # Productions are read only to resolve the candidate start.
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'start'])
    def execute(self, id: str, start: str, **kwargs) -> GrammarAggregate:
        '''
        Replace the start name when it names an effective production.

        :param id: The grammar identifier.
        :type id: str
        :param start: The new start-production name.
        :type start: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The saved grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # A missing grammar is not updated.
        grammar = self.grammar_service.get(id)
        self.verify(
            grammar is not None,
            a.grammar.GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar {id} was not found.',
            id=id,
        )

        # Apply the candidate start before resolving it.
        grammar.set_start(start)

        # Resolve start for this candidate only. Do not save on failure.
        self._verify_start_resolves(
            grammar,
            self.grammar_service.list(),
            self.production_service.list(),
        )

        # Persist and return the mutated aggregate.
        self.grammar_service.save(grammar)
        return grammar
