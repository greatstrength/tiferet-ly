"""Tests for Tiferet-Ly Grammar Rule Selection Utility"""

# *** imports

# ** app
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import SimpleProductionRuleAggregate
from tiferet_ly.mappers.token import SimpleTokenRuleAggregate
from tiferet_ly.utils.grammar import GrammarRuleSelector, walk_ancestry

# *** functions

# ** function: grammar
def grammar(id: str, parent_ids=None, start: str = 'expression') -> GrammarAggregate:
    '''
    Construct a GrammarAggregate for selector tests.

    :param id: The grammar id.
    :type id: str
    :param parent_ids: Optional ordered parent ids.
    :type parent_ids: list | None
    :param start: The start symbol.
    :type start: str
    :return: The constructed grammar aggregate.
    :rtype: GrammarAggregate
    '''

    # Construct a lean grammar with the given composition.
    return GrammarAggregate(
        id=id,
        parent_ids=list(parent_ids or []),
        start=start,
    )

# ** function: token
def token(name: str, grammar_id: str, pattern: str = r'\s+') -> SimpleTokenRuleAggregate:
    '''
    Construct a simple token aggregate for selector tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :return: The constructed token aggregate.
    :rtype: SimpleTokenRuleAggregate
    '''

    # Construct a simple token under the given grammar.
    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
    )

# ** function: production
def production(
        name: str,
        grammar_id: str,
        spec: str = 'expression : term') -> SimpleProductionRuleAggregate:
    '''
    Construct a simple production aggregate for selector tests.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :return: The constructed production aggregate.
    :rtype: SimpleProductionRuleAggregate
    '''

    # Construct a simple production under the given grammar.
    return SimpleProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )

# *** tests

# ** test: walk_ancestry_empty_parents
def test_walk_ancestry_empty_parents() -> None:
    '''
    Test that a root grammar resolves to only its own id.
    '''

    # Walk a grammar with no parents.
    root = grammar('core')

    # Assert the target is the only resolved id.
    assert walk_ancestry(root, []) == ['core']

# ** test: walk_ancestry_single_parent_chain
def test_walk_ancestry_single_parent_chain() -> None:
    '''
    Test that a single-parent chain resolves most-fundamental first.
    '''

    # Walk X -> Y -> Z.
    z = grammar('Z')
    y = grammar('Y', ['Z'])
    x = grammar('X', ['Y'])

    # Assert the chain is most-fundamental first, target last.
    assert walk_ancestry(x, [x, y, z]) == ['Z', 'Y', 'X']

# ** test: walk_ancestry_diamond
def test_walk_ancestry_diamond() -> None:
    '''
    Test that a diamond keeps the shared ancestor once at a stable position.
    '''

    # Walk X -> [Y, Z], both of which extend W.
    w = grammar('W')
    y = grammar('Y', ['W'])
    z = grammar('Z', ['W'])
    x = grammar('X', ['Y', 'Z'])

    # Assert the exact diamond order from RFP-004.
    assert walk_ancestry(x, [w, y, z, x]) == ['Y', 'W', 'Z', 'X']

# ** test: walk_ancestry_unrelated_parents_later_declared_wins
def test_walk_ancestry_unrelated_parents_later_declared_wins() -> None:
    '''
    Test that a later-declared unrelated parent sits at a higher index.
    '''

    # Walk X -> [Y, Z] with both parents childless.
    y = grammar('Y')
    z = grammar('Z')
    x = grammar('X', ['Y', 'Z'])

    # Assert Z is more precedent than Y.
    result = walk_ancestry(x, [y, z, x])
    assert result.index('Z') > result.index('Y')
    assert result[-1] == 'X'

# ** test: walk_ancestry_dangling_parent_is_skipped
def test_walk_ancestry_dangling_parent_is_skipped() -> None:
    '''
    Test that an unresolvable parent_ids entry is skipped without raising.
    '''

    # Walk a grammar whose only parent is missing from the catalogue.
    x = grammar('X', ['missing'])

    # Assert the dangling parent contributes nothing.
    assert walk_ancestry(x, [x]) == ['X']

# ** test: select_tokens_filters_and_preserves_order
def test_select_tokens_filters_and_preserves_order() -> None:
    '''
    Test that out-of-scope tokens are dropped and survivor order is kept.
    '''

    # Select for arithmetic from a mixed, non-alphabetical catalogue.
    arithmetic = grammar('arithmetic')
    other = grammar('other')
    tokens = [
        token('ZETA', 'other', 'z'),
        token('PLUS', 'arithmetic', r'\+'),
        token('NUMBER', 'arithmetic', r'\d+'),
        token('COLON', 'other', ':'),
    ]

    # Assert only arithmetic tokens survive, in their original relative order.
    selected = GrammarRuleSelector.select_tokens(arithmetic, [arithmetic, other], tokens)
    assert [(item.name, item.grammar_id) for item in selected] == [
        ('PLUS', 'arithmetic'),
        ('NUMBER', 'arithmetic'),
    ]

# ** test: select_tokens_whitespace_collision_base_declared_first
def test_select_tokens_whitespace_collision_base_declared_first() -> None:
    '''
    Test the WHITESPACE example when the base token is declared first.
    '''

    # Select for the comments dialect with the base WHITESPACE first.
    arithmetic = grammar('arithmetic')
    comments = grammar('arithmetic_with_comments', ['arithmetic'])
    tokens = [
        token('PLUS', 'arithmetic', r'\+'),
        token('WHITESPACE', 'arithmetic', r'\s+'),
        token('WHITESPACE', 'arithmetic_with_comments', r'(\s+|#.*)'),
    ]

    # Assert the dialect WHITESPACE wins and keeps its filtered position.
    selected = GrammarRuleSelector.select_tokens(
        comments,
        [arithmetic, comments],
        tokens,
    )
    assert [(item.name, item.grammar_id) for item in selected] == [
        ('PLUS', 'arithmetic'),
        ('WHITESPACE', 'arithmetic_with_comments'),
    ]

# ** test: select_tokens_whitespace_collision_winner_declared_first
def test_select_tokens_whitespace_collision_winner_declared_first() -> None:
    '''
    Test that ancestor precedence, not file order, resolves token names.
    '''

    # Reverse the WHITESPACE declaration order so the winner appears first.
    arithmetic = grammar('arithmetic')
    comments = grammar('arithmetic_with_comments', ['arithmetic'])
    tokens = [
        token('PLUS', 'arithmetic', r'\+'),
        token('WHITESPACE', 'arithmetic_with_comments', r'(\s+|#.*)'),
        token('WHITESPACE', 'arithmetic', r'\s+'),
    ]

    # Assert the dialect token still wins despite appearing earlier.
    selected = GrammarRuleSelector.select_tokens(
        comments,
        [arithmetic, comments],
        tokens,
    )
    assert [(item.name, item.grammar_id) for item in selected] == [
        ('PLUS', 'arithmetic'),
        ('WHITESPACE', 'arithmetic_with_comments'),
    ]

# ** test: select_productions_filter_only_keeps_same_name
def test_select_productions_filter_only_keeps_same_name() -> None:
    '''
    Test that same-named productions across grammars all survive.
    '''

    # Select productions spanning two in-scope grammars plus one outsider.
    arithmetic = grammar('arithmetic')
    names = grammar('arithmetic_with_names', ['arithmetic'])
    other = grammar('other')
    productions = [
        production('expression', 'arithmetic', 'expression : term'),
        production('name', 'other', 'name : IDENTIFIER'),
        production('expression', 'arithmetic_with_names', 'expression : NAME'),
        production('term', 'arithmetic', 'term : NUMBER'),
    ]

    # Assert both expression alternatives survive in input order.
    selected = GrammarRuleSelector.select_productions(
        names,
        [arithmetic, names, other],
        productions,
    )
    assert [(item.name, item.grammar_id) for item in selected] == [
        ('expression', 'arithmetic'),
        ('expression', 'arithmetic_with_names'),
        ('term', 'arithmetic'),
    ]

# ** test: has_cycle_direct_self_reference
def test_has_cycle_direct_self_reference() -> None:
    '''
    Test that a grammar listing itself as a parent is a cycle.
    '''

    # Check a one-hop self-reference.
    assert GrammarRuleSelector.has_cycle('X', ['X'], []) is True

# ** test: has_cycle_transitive
def test_has_cycle_transitive() -> None:
    '''
    Test that a grammar reachable through an intermediate parent is a cycle.
    '''

    # Check X -> Y -> X via Y's persisted parent list.
    y = grammar('Y', ['X'])

    # Assert the transitive self-reachability is detected.
    assert GrammarRuleSelector.has_cycle('X', ['Y'], [y]) is True

# ** test: has_cycle_false_for_diamond_and_dangling
def test_has_cycle_false_for_diamond_and_dangling() -> None:
    '''
    Test that a well-formed diamond and dangling parents are not cycles.
    '''

    # Check the diamond shape and a missing parent id.
    w = grammar('W')
    y = grammar('Y', ['W'])
    z = grammar('Z', ['W'])

    # Assert neither the diamond nor a dangling ref is a cycle.
    assert GrammarRuleSelector.has_cycle('X', ['Y', 'Z'], [w, y, z]) is False
    assert GrammarRuleSelector.has_cycle('X', ['missing'], [w, y, z]) is False
    assert GrammarRuleSelector.has_cycle('X', ['Y'], [y, grammar('Y_extra', ['missing'])]) is False
