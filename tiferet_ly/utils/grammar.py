"""Tiferet Ly Grammar Selection"""

# *** imports

# ** app
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ProductionRuleAggregate
from tiferet_ly.mappers.token import TokenRuleAggregate

# *** functions

# ** function: grammar_index
def grammar_index(
        grammars: list[GrammarAggregate],
    ) -> dict[str, GrammarAggregate]:
    '''
    Map each grammar identifier to the supplied aggregate.

    An empty catalogue returns an empty dict. The list and the aggregates
    are left unchanged, and an identifier that was not supplied is absent.

    :param grammars: The declared grammar catalogue.
    :type grammars: list[GrammarAggregate]
    :return: A new mapping of grammar id to the same aggregate instance.
    :rtype: dict[str, GrammarAggregate]
    '''

    # Copy identifiers into a new dict. Do not mutate the catalogue.
    return {
        grammar.id: grammar
        for grammar in grammars
    }

# ** function: walk_ancestry
def walk_ancestry(
        grammar: GrammarAggregate,
        grammars: list[GrammarAggregate],
    ) -> list[str]:
    '''
    Return ancestor identifiers, most fundamental first, with this grammar last.

    A missing parent contributes nothing. An identifier already visited is
    skipped, including the target id. The walk does not raise.

    :param grammar: The grammar whose parents to walk. It need not be in the catalogue.
    :type grammar: GrammarAggregate
    :param grammars: The declared grammar catalogue.
    :type grammars: list[GrammarAggregate]
    :return: Ancestor identifiers, most fundamental first, ending with this grammar.
    :rtype: list[str]
    '''

    # Index the catalogue. Do not substitute it for the grammar argument.
    index = grammar_index(grammars)

    # Record the first visit of each present parent.
    recorded = []
    seen = set()

    def visit(parent_ids: list[str]) -> None:
        for parent_id in reversed(parent_ids):
            if parent_id in seen:
                continue
            parent = index.get(parent_id)
            if parent is None:
                continue
            seen.add(parent_id)
            recorded.append(parent_id)
            visit(parent.parent_ids)

    # Walk the argument's parents, then restore fundamental-first order.
    visit(grammar.parent_ids)
    recorded.reverse()
    recorded.append(grammar.id)
    return recorded

# *** utils

# ** util: grammar_rule_selector
class GrammarRuleSelector:
    '''
    Selects one grammar's effective rules from a declared-order catalogue.

    Membership is ancestry, not a re-sort. A shared token name keeps the
    closer declaration; a repeated production name stays additive.
    '''

    # * method: select_tokens (static)
    @staticmethod
    def select_tokens(
            grammar: GrammarAggregate,
            grammars: list[GrammarAggregate],
            tokens: list[TokenRuleAggregate],
        ) -> list[TokenRuleAggregate]:
        '''
        Keep in-scope tokens and drop a shared name's farther declarations.

        Survivors stay in input order. The winner is the token whose
        grammar sits highest in the ancestry list, not the later input.

        :param grammar: The grammar whose ancestry to apply.
        :type grammar: GrammarAggregate
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :param tokens: The declared token catalogue, in input order.
        :type tokens: list[TokenRuleAggregate]
        :return: The same token instances that remain in scope.
        :rtype: list[TokenRuleAggregate]
        '''

        # Membership is the ancestry id list, including this grammar.
        ancestry = walk_ancestry(grammar, grammars)
        ancestry_ids = set(ancestry)
        rank = {
            grammar_id: index
            for index, grammar_id in enumerate(ancestry)
        }

        # Drop out-of-scope tokens without reordering the rest.
        selected = [
            token
            for token in tokens
            if token.grammar_id in ancestry_ids
        ]

        # A shared name keeps the closer grammar and stays where it was.
        winning_index = {}
        for token in selected:
            token_index = rank[token.grammar_id]
            current = winning_index.get(token.name)
            if current is None or token_index > current:
                winning_index[token.name] = token_index

        # Drop farther declarations in place. Do not move the winner.
        return [
            token
            for token in selected
            if rank[token.grammar_id] == winning_index[token.name]
        ]

    # * method: select_productions (static)
    @staticmethod
    def select_productions(
            grammar: GrammarAggregate,
            grammars: list[GrammarAggregate],
            productions: list[ProductionRuleAggregate],
        ) -> list[ProductionRuleAggregate]:
        '''
        Keep in-scope productions in input order.

        Repeated names are alternatives, including across in-scope grammars.
        This filter does not drop by name.

        :param grammar: The grammar whose ancestry to apply.
        :type grammar: GrammarAggregate
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :param productions: The declared production catalogue, in input order.
        :type productions: list[ProductionRuleAggregate]
        :return: The same production instances that remain in scope.
        :rtype: list[ProductionRuleAggregate]
        '''

        # Membership is the ancestry id list. Do not deduplicate by name.
        ancestry_ids = set(walk_ancestry(grammar, grammars))
        return [
            production
            for production in productions
            if production.grammar_id in ancestry_ids
        ]

    # * method: has_cycle (static)
    @staticmethod
    def has_cycle(
            grammar_id: str,
            parent_ids: list[str],
            grammars: list[GrammarAggregate],
        ) -> bool:
        '''
        Report whether a candidate parent list would reach its own grammar.

        The candidate list is the frontier, not a persisted aggregate's
        parents. A missing identifier is a dead end. The check does not raise.

        :param grammar_id: The grammar identifier being composed.
        :type grammar_id: str
        :param parent_ids: The candidate parent identifiers, in declared order.
        :type parent_ids: list[str]
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :return: True when the candidate parents reach grammar_id.
        :rtype: bool
        '''

        # Index the catalogue. Do not start from a saved parent list.
        index = grammar_index(grammars)

        # Walk the candidate frontier. A missing id ends that branch.
        seen = set()

        def visit(frontier: list[str]) -> bool:
            for parent_id in frontier:
                if parent_id == grammar_id:
                    return True
                if parent_id in seen:
                    continue
                seen.add(parent_id)
                parent = index.get(parent_id)
                if parent is None:
                    continue
                if visit(parent.parent_ids):
                    return True
            return False

        # Exhausting the frontier without meeting the target is acyclic.
        return visit(parent_ids)
