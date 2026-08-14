"""Tiferet-Ly Grammar Rule Selection Utility"""

# *** imports

# ** core
from typing import Dict, List

# ** app
from ..mappers.grammar import GrammarAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate

# *** functions

# ** function: grammar_index
def grammar_index(grammars: List[GrammarAggregate]) -> Dict[str, GrammarAggregate]:
    '''
    Index grammars by id for ancestor lookup.

    :param grammars: The full grammar catalogue.
    :type grammars: List[GrammarAggregate]
    :return: Grammars keyed by id.
    :rtype: Dict[str, GrammarAggregate]
    '''

    # Index each grammar by its own id.
    return {grammar.id: grammar for grammar in grammars}

# ** function: walk_ancestry
def walk_ancestry(
        grammar: GrammarAggregate,
        grammars: List[GrammarAggregate]) -> List[str]:
    '''
    Resolve a grammar's ancestor ids, most fundamental first.

    :param grammar: The target grammar whose ancestry is walked.
    :type grammar: GrammarAggregate
    :param grammars: The catalogue used to resolve ancestor parent_ids.
    :type grammars: List[GrammarAggregate]
    :return: Ancestor ids with the target id last.
    :rtype: List[str]
    '''

    # Index the catalogue; the target itself is never looked up by id.
    by_id = grammar_index(grammars)
    recorded = []
    visited = set()

    # Record each reachable ancestor the first time it is visited.
    def visit(grammar_id: str) -> None:

        # Skip already-visited ids so diamonds stay stable and cycles terminate.
        if grammar_id in visited:
            return

        # Treat an unresolvable parent as a dead end.
        resolved = by_id.get(grammar_id)
        if resolved is None:
            return

        # Record on first visit, then walk this grammar's parents last-first.
        visited.add(grammar_id)
        recorded.append(grammar_id)
        for parent_id in reversed(resolved.parent_ids):
            visit(parent_id)

    # Walk the target's parents in reverse declared order.
    for parent_id in reversed(grammar.parent_ids):
        visit(parent_id)

    # Reverse so the most-fundamental ancestor is first, then append the target.
    recorded.reverse()
    recorded.append(grammar.id)

    # Return the resolved ancestor id list.
    return recorded

# *** utils

# ** util: grammar_rule_selector
class GrammarRuleSelector:
    '''
    Resolves one grammar's effective, ancestor-composed rule set from a
    flat catalogue so a reader can consume a single ordered list without
    re-deriving DAG precedence itself.
    '''

    # * method: select_tokens (static)
    @staticmethod
    def select_tokens(
            grammar: GrammarAggregate,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate]) -> List[TokenRuleAggregate]:
        '''
        Filter tokens to one grammar's ancestry and resolve name collisions.

        :param grammar: The target grammar being selected for.
        :type grammar: GrammarAggregate
        :param grammars: The catalogue used to resolve ancestry.
        :type grammars: List[GrammarAggregate]
        :param tokens: The flat token catalogue in declared order.
        :type tokens: List[TokenRuleAggregate]
        :return: In-scope tokens with same-name collisions resolved.
        :rtype: List[TokenRuleAggregate]
        '''

        # Resolve ancestry and keep only tokens declared under those grammars.
        ancestor_ids = walk_ancestry(grammar, grammars)
        ancestor_index = {
            grammar_id: index
            for index, grammar_id in enumerate(ancestor_ids)
        }
        filtered = [
            token for token in tokens
            if token.grammar_id in ancestor_index
        ]

        # For each token name, keep the contributor closest to the target.
        winners = {}
        for token in filtered:
            current = winners.get(token.name)
            if (
                current is None
                or ancestor_index[token.grammar_id] > ancestor_index[current]
            ):
                winners[token.name] = token.grammar_id

        # Drop losing same-named entries without re-sorting survivors.
        return [
            token for token in filtered
            if winners[token.name] == token.grammar_id
        ]

    # * method: select_productions (static)
    @staticmethod
    def select_productions(
            grammar: GrammarAggregate,
            grammars: List[GrammarAggregate],
            productions: List[ProductionRuleAggregate]) -> List[ProductionRuleAggregate]:
        '''
        Filter productions to one grammar's ancestry without name resolution.

        :param grammar: The target grammar being selected for.
        :type grammar: GrammarAggregate
        :param grammars: The catalogue used to resolve ancestry.
        :type grammars: List[GrammarAggregate]
        :param productions: The flat production catalogue in declared order.
        :type productions: List[ProductionRuleAggregate]
        :return: In-scope productions in their original relative order.
        :rtype: List[ProductionRuleAggregate]
        '''

        # Resolve ancestry and keep every in-scope production, including repeats.
        ancestor_ids = set(walk_ancestry(grammar, grammars))

        # Filter only; same-named productions across grammars all survive.
        return [
            production for production in productions
            if production.grammar_id in ancestor_ids
        ]

    # * method: has_cycle (static)
    @staticmethod
    def has_cycle(
            grammar_id: str,
            parent_ids: List[str],
            grammars: List[GrammarAggregate]) -> bool:
        '''
        Return whether a candidate parent list would cycle back to a grammar.

        :param grammar_id: The grammar that would own the candidate parents.
        :type grammar_id: str
        :param parent_ids: The candidate ordered parent ids.
        :type parent_ids: List[str]
        :param grammars: The catalogue used to resolve ancestor parent_ids.
        :type grammars: List[GrammarAggregate]
        :return: True when grammar_id is reachable from parent_ids.
        :rtype: bool
        '''

        # Index the catalogue and walk reachability from the candidate parents.
        by_id = grammar_index(grammars)
        visited = set()

        # Return True as soon as the candidate grammar is reached.
        def reaches(current_id: str) -> bool:

            # A hit on the candidate grammar is a cycle, including a direct self-ref.
            if current_id == grammar_id:
                return True

            # Skip already-visited ids so unrelated cycles still terminate.
            if current_id in visited:
                return False

            # Treat an unresolvable parent as a dead end.
            visited.add(current_id)
            resolved = by_id.get(current_id)
            if resolved is None:
                return False

            # Recurse into this grammar's own parents.
            return any(reaches(parent_id) for parent_id in resolved.parent_ids)

        # A cycle exists if any candidate parent can reach the grammar.
        return any(reaches(parent_id) for parent_id in parent_ids)
