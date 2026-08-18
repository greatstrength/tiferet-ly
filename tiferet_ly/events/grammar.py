"""Tiferet-Ly Grammar Domain Events"""

# *** imports

# ** core
from typing import List, Optional

# ** app
from tiferet.events.core import DomainEvent
from .. import assets as a
from ..interfaces.grammar import GrammarService
from ..interfaces.production import ProductionService
from ..interfaces.token import TokenService
from ..mappers.grammar import GrammarAggregate
from ..utils.grammar import GrammarRuleSelector

# *** events

# ** event: grammar_event
class GrammarEvent(DomainEvent):
    '''
    Base event providing the shared GrammarService dependency.

    Cross-aggregate writers add ProductionService and, for delete, TokenService
    so cycle, parent, start, and still-referenced checks can run before save.
    '''

    # * attribute: grammar_service
    grammar_service: GrammarService

    # * init
    def __init__(self, grammar_service: GrammarService):
        '''
        Initialize the grammar event with its shared service dependency.

        :param grammar_service: The grammar service shared across grammar events.
        :type grammar_service: GrammarService
        '''

        # Set the grammar service dependency.
        self.grammar_service = grammar_service

    # * method: _require_grammar
    def _require_grammar(self, id: str) -> GrammarAggregate:
        '''
        Load a grammar by id and verify it exists.

        :param id: The grammar identifier.
        :type id: str
        :return: The loaded grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Retrieve the grammar by id.
        grammar = self.grammar_service.get(id)

        # Verify the grammar exists.
        self.verify(
            grammar is not None,
            a.error.GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar not found: {id}.',
            id=id,
        )

        # Return the loaded grammar.
        return grammar

    # * method: _verify_parents_exist
    def _verify_parents_exist(
            self,
            parent_ids: List[str],
            grammar_id: str = None) -> None:
        '''
        Verify every parent id already names a persisted grammar.

        The candidate's own id is skipped so a direct self-reference reaches
        the cycle check instead of being reported as a missing parent.

        :param parent_ids: The candidate ordered parent ids.
        :type parent_ids: List[str]
        :param grammar_id: The grammar that would own the parents.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Refuse any other parent that is not already persisted.
        for parent_id in parent_ids:
            if parent_id == grammar_id:
                continue
            self.verify(
                self.grammar_service.exists(parent_id),
                a.error.GRAMMAR_PARENT_NOT_FOUND_ID,
                message=f'Grammar parent not found: {parent_id}.',
                parent_id=parent_id,
            )

    # * method: _verify_no_cycle
    def _verify_no_cycle(self, grammar_id: str, parent_ids: List[str]) -> None:
        '''
        Verify the candidate parent list does not cycle back to the grammar.

        :param grammar_id: The grammar that would own the parents.
        :type grammar_id: str
        :param parent_ids: The candidate ordered parent ids.
        :type parent_ids: List[str]
        :return: None
        :rtype: None
        '''

        # Translate the selector's primitive cycle answer into a domain error.
        self.verify(
            not GrammarRuleSelector.has_cycle(
                grammar_id,
                parent_ids,
                self.grammar_service.list(),
            ),
            a.error.GRAMMAR_CYCLE_DETECTED_ID,
            message=f'Grammar cycle detected: {grammar_id}.',
            id=grammar_id,
        )

    # * method: _verify_start_resolves
    def _verify_start_resolves(self, grammar: GrammarAggregate) -> None:
        '''
        Verify the grammar's start names a production in its effective set.

        :param grammar: The candidate grammar, which need not be persisted yet.
        :type grammar: GrammarAggregate
        :return: None
        :rtype: None
        '''

        # Resolve the effective productions against the persisted catalogue.
        effective = GrammarRuleSelector.select_productions(
            grammar,
            self.grammar_service.list(),
            self.production_service.list(),
        )

        # Verify the start symbol is among those effective names.
        self.verify(
            any(production.name == grammar.start for production in effective),
            a.error.GRAMMAR_START_NOT_FOUND_ID,
            message=f'Grammar start not found: {grammar.start} on {grammar.id}.',
            id=grammar.id,
            start=grammar.start,
        )


# ** event: add_grammar
class AddGrammar(GrammarEvent):
    '''
    Event to persist a new grammar after parent, cycle, and start checks.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self,
            grammar_service: GrammarService,
            production_service: ProductionService):
        '''
        Initialize with the grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service used for the start check.
        :type production_service: ProductionService
        '''

        # Set both service dependencies.
        super().__init__(grammar_service)
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'start'])
    def execute(self,
            id: str,
            start: str,
            parent_ids: Optional[List[str]] = None,
            **kwargs) -> GrammarAggregate:
        '''
        Add a new grammar.

        :param id: The grammar identifier.
        :type id: str
        :param start: The start symbol name.
        :type start: str
        :param parent_ids: Optional ordered parent grammar ids.
        :type parent_ids: Optional[List[str]]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The created grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Verify the grammar id is free.
        self.verify(
            not self.grammar_service.exists(id),
            a.error.GRAMMAR_ALREADY_EXISTS_ID,
            message=f'Grammar already exists: {id}.',
            id=id,
        )

        # Treat a missing parent list as an empty root.
        resolved_parent_ids = parent_ids or []

        # Verify every parent exists and the candidate list is acyclic.
        self._verify_parents_exist(resolved_parent_ids, grammar_id=id)
        self._verify_no_cycle(id, resolved_parent_ids)

        # Construct the grammar without saving so the start check can use it.
        grammar = GrammarAggregate(
            id=id,
            parent_ids=resolved_parent_ids,
            start=start,
        )
        self._verify_start_resolves(grammar)

        # Persist and return the new grammar.
        self.grammar_service.save(grammar)
        return grammar


# ** event: get_grammar
class GetGrammar(GrammarEvent):
    '''
    Event to retrieve a grammar by id.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> GrammarAggregate:
        '''
        Retrieve a grammar by id.

        :param id: The grammar identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Load and return the grammar, raising when it is absent.
        return self._require_grammar(id)


# ** event: list_grammars
class ListGrammars(GrammarEvent):
    '''
    Event to list every grammar unfiltered.
    '''

    # * method: execute
    def execute(self, **kwargs) -> List[GrammarAggregate]:
        '''
        List every stored grammar.

        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: All stored grammar aggregates.
        :rtype: List[GrammarAggregate]
        '''

        # Return the unfiltered catalogue.
        return self.grammar_service.list()


# ** event: set_grammar_start
class SetGrammarStart(GrammarEvent):
    '''
    Event to replace a grammar's start symbol after the start check passes.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self,
            grammar_service: GrammarService,
            production_service: ProductionService):
        '''
        Initialize with the grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service used for the start check.
        :type production_service: ProductionService
        '''

        # Set both service dependencies.
        super().__init__(grammar_service)
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'start'])
    def execute(self, id: str, start: str, **kwargs) -> GrammarAggregate:
        '''
        Set a grammar's start symbol.

        :param id: The grammar identifier.
        :type id: str
        :param start: The new start symbol name.
        :type start: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Load the grammar, apply the start mutator, and re-check start.
        grammar = self._require_grammar(id)
        grammar.set_start(start)
        self._verify_start_resolves(grammar)

        # Persist and return the updated grammar.
        self.grammar_service.save(grammar)
        return grammar


# ** event: set_grammar_parent_ids
class SetGrammarParentIds(GrammarEvent):
    '''
    Event to replace a grammar's parents after parent, cycle, and start checks.
    '''

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self,
            grammar_service: GrammarService,
            production_service: ProductionService):
        '''
        Initialize with the grammar and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param production_service: The production service used for the start check.
        :type production_service: ProductionService
        '''

        # Set both service dependencies.
        super().__init__(grammar_service)
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id', 'parent_ids'])
    def execute(self, id: str, parent_ids: List[str], **kwargs) -> GrammarAggregate:
        '''
        Replace a grammar's ordered parent ids.

        :param id: The grammar identifier.
        :type id: str
        :param parent_ids: The new ordered parent ids.
        :type parent_ids: List[str]
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The updated grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Load the grammar and verify the candidate parent list.
        grammar = self._require_grammar(id)
        self._verify_parents_exist(parent_ids, grammar_id=id)
        self._verify_no_cycle(id, parent_ids)

        # Apply the parent mutator, then re-check start against the new ancestry.
        grammar.set_parent_ids(parent_ids)
        self._verify_start_resolves(grammar)

        # Persist and return the updated grammar.
        self.grammar_service.save(grammar)
        return grammar


# ** event: remove_grammar
class RemoveGrammar(GrammarEvent):
    '''
    Event to delete a grammar that is no longer referenced by parents or rules.
    '''

    # * attribute: token_service
    token_service: TokenService

    # * attribute: production_service
    production_service: ProductionService

    # * init
    def __init__(self,
            grammar_service: GrammarService,
            token_service: TokenService,
            production_service: ProductionService):
        '''
        Initialize with the grammar, token, and production services.

        :param grammar_service: The grammar service.
        :type grammar_service: GrammarService
        :param token_service: The token service used for still-referenced checks.
        :type token_service: TokenService
        :param production_service: The production service used for still-referenced checks.
        :type production_service: ProductionService
        '''

        # Set all three service dependencies.
        super().__init__(grammar_service)
        self.token_service = token_service
        self.production_service = production_service

    # * method: execute
    @DomainEvent.parameters_required(['id'])
    def execute(self, id: str, **kwargs) -> str:
        '''
        Delete a grammar when nothing still references it.

        :param id: The grammar identifier.
        :type id: str
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The identity that was requested for deletion.
        :rtype: str
        '''

        # Refuse delete when another grammar still lists this id as a parent.
        listed_as_parent = any(
            id in grammar.parent_ids
            for grammar in self.grammar_service.list()
        )

        # Refuse delete when a token or production is still declared under this id.
        referenced_by_token = any(
            token.grammar_id == id
            for token in self.token_service.list()
        )
        referenced_by_production = any(
            production.grammar_id == id
            for production in self.production_service.list()
        )
        self.verify(
            not (listed_as_parent or referenced_by_token or referenced_by_production),
            a.error.GRAMMAR_STILL_REFERENCED_ID,
            message=f'Grammar still referenced: {id}.',
            id=id,
        )

        # Delete is idempotent once the reference checks have nothing to refuse.
        self.grammar_service.delete(id)

        # Return the identity that was given.
        return id
