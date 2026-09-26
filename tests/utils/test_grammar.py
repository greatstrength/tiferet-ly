"""Tiferet Ly Grammar Selector Tests"""

# *** imports

# ** core
import ast
import inspect
import textwrap
from pathlib import Path

# ** app
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.production import ProductionRuleAggregate
from tiferet_ly.mappers.token import TokenRuleAggregate
from tiferet_ly.utils import grammar as grammar_utils
from tiferet_ly.utils.grammar import (
    GrammarRuleSelector,
    grammar_index,
    walk_ancestry,
)

# *** constants

# ** constant: utils_init
_UTILS_INIT = Path(grammar_utils.__file__).parents[0] / '__init__.py'

# *** functions

# ** function: grammar
def _grammar(grammar_id: str, parent_ids: list[str]) -> GrammarAggregate:
    '''
    Build a lean grammar aggregate.

    :param grammar_id: The grammar identifier.
    :type grammar_id: str
    :param parent_ids: The ordered parent identifiers.
    :type parent_ids: list[str]
    :return: A grammar aggregate.
    :rtype: GrammarAggregate
    '''

    # Start is required by construction and is not a selector input.
    return GrammarAggregate(
        id=grammar_id,
        parent_ids=parent_ids,
        start='start',
    )

# ** function: token
def _token(name: str, grammar_id: str) -> TokenRuleAggregate:
    '''
    Build a token aggregate from name and grammar membership only.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar identifier.
    :type grammar_id: str
    :return: A token aggregate.
    :rtype: TokenRuleAggregate
    '''

    return TokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
    )

# ** function: production
def _production(name: str, grammar_id: str) -> ProductionRuleAggregate:
    '''
    Build a production aggregate from name and grammar membership only.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar identifier.
    :type grammar_id: str
    :return: A production aggregate.
    :rtype: ProductionRuleAggregate
    '''

    return ProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
    )

# ** function: imported_modules
def _imported_modules(tree: ast.AST) -> list[str]:
    '''
    Collect imported module names from a parsed module.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Imported module names.
    :rtype: list[str]
    '''

    # Walk import and import-from nodes only.
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

# ** function: calls_name
def _calls_name(function) -> set[str]:
    '''
    Collect bare names called directly by a function.

    :param function: The function whose source to inspect.
    :type function: Callable
    :return: Called names.
    :rtype: set[str]
    '''

    # Read the function body, not the class indentation around it.
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    function_node = tree.body[0]
    called = set()
    for node in function_node.body:
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                called.add(child.func.id)
    return called

# ** function: dumps
def _dumps(items: list) -> list[dict]:
    '''
    Snapshot aggregate field values without retaining the instances.

    :param items: The aggregates to snapshot.
    :type items: list
    :return: Field dumps in input order.
    :rtype: list[dict]
    '''

    return [item.model_dump() for item in items]

# *** tests

# ** test: module_surface
def test_module_surface():
    '''
    Keep selection in the utils module and off the package marker.
    '''

    # The published functions and static methods live on the utils module.
    assert inspect.isfunction(grammar_index)
    assert inspect.isfunction(walk_ancestry)
    assert grammar_utils.grammar_index is grammar_index
    assert grammar_utils.walk_ancestry is walk_ancestry
    for name in ('select_tokens', 'select_productions', 'has_cycle'):
        assert isinstance(GrammarRuleSelector.__dict__[name], staticmethod)
        assert inspect.isfunction(getattr(GrammarRuleSelector, name))

    # Ancestry and the cycle check both index the catalogue.
    assert 'grammar_index' in _calls_name(walk_ancestry)
    assert 'grammar_index' in _calls_name(GrammarRuleSelector.has_cycle)
    assert 'walk_ancestry' not in _calls_name(GrammarRuleSelector.has_cycle)
    assert 'walk_ancestry' in _calls_name(GrammarRuleSelector.select_tokens)
    assert 'walk_ancestry' in _calls_name(GrammarRuleSelector.select_productions)

    # Selector operations are typed on aggregates, not bare domain objects.
    token_hints = inspect.get_annotations(GrammarRuleSelector.select_tokens)
    production_hints = inspect.get_annotations(GrammarRuleSelector.select_productions)
    cycle_hints = inspect.get_annotations(GrammarRuleSelector.has_cycle)
    assert token_hints['grammar'] is GrammarAggregate
    assert token_hints['tokens'] == list[TokenRuleAggregate]
    assert token_hints['return'] == list[TokenRuleAggregate]
    assert production_hints['productions'] == list[ProductionRuleAggregate]
    assert production_hints['return'] == list[ProductionRuleAggregate]
    assert cycle_hints['grammars'] == list[GrammarAggregate]
    assert inspect.get_annotations(walk_ancestry)['grammar'] is GrammarAggregate
    assert inspect.get_annotations(grammar_index)['return'] == dict[str, GrammarAggregate]

# ** test: forbidden_imports
def test_forbidden_imports():
    '''
    Import neither PLY, domain, events, nor repositories from the selector.
    '''

    # The selector module stays on mapper aggregates.
    selector_modules = _imported_modules(ast.parse(Path(grammar_utils.__file__).read_text()))
    for module in selector_modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert not module.startswith('tiferet_ly.domain')
        assert not module.startswith('tiferet_ly.events')
        assert not module.startswith('tiferet_ly.repos')

    # The class is not an event or a service.
    tree = ast.parse(Path(grammar_utils.__file__).read_text())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ['GrammarRuleSelector']
    assert classes[0].bases == []

    # The package marker does not import PLY, events, or repositories.
    marker_modules = _imported_modules(ast.parse(_UTILS_INIT.read_text()))
    for module in marker_modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert not module.startswith('tiferet_ly.events')
        assert not module.startswith('tiferet_ly.repos')

    # This test module does not import those packages or assert a raise.
    test_tree = ast.parse(Path(__file__).read_text())
    for module in _imported_modules(test_tree):
        assert module != 'ply' and not module.startswith('ply.')
        parts = module.split('.')
        if parts[:1] == ['tiferet_ly'] and len(parts) > 1:
            assert parts[1] not in ('repos', 'events')
    raised = [
        node
        for node in ast.walk(test_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ('raises', 'assertRaises')
    ]
    assert raised == []

# ** test: grammar_index_maps_same_instances
def test_grammar_index_maps_same_instances():
    '''
    Index supplied grammars by id and leave an absent id out.
    '''

    # An empty catalogue is an empty dict.
    assert grammar_index([]) == {}

    # Each distinct id maps to that same aggregate.
    base = _grammar('base', [])
    child = _grammar('child', ['base'])
    grammars = [base, child]
    before = _dumps(grammars)
    indexed = grammar_index(grammars)
    assert indexed == {'base': base, 'child': child}
    assert indexed['base'] is base
    assert indexed['child'] is child
    assert 'missing' not in indexed
    assert grammars == [base, child]
    assert _dumps(grammars) == before

# ** test: walk_ancestry_orders_parents
def test_walk_ancestry_orders_parents():
    '''
    Walk the argument's parents, most fundamental first, without raising.
    '''

    # No parents yields the grammar id, even when it is absent from the catalogue.
    alone = _grammar('alone', [])
    assert walk_ancestry(alone, []) == ['alone']

    # The argument's parents win over a catalogue copy of the same id.
    catalogue_x = _grammar('X', [])
    argument_x = _grammar('X', ['Y'])
    childless_y = _grammar('Y', [])
    assert walk_ancestry(argument_x, [catalogue_x, childless_y]) == ['Y', 'X']

    # A single-parent chain is most fundamental first.
    zed = _grammar('Z', [])
    wye = _grammar('Y', ['Z'])
    ex = _grammar('X', ['Y'])
    assert walk_ancestry(ex, [zed, wye, ex]) == ['Z', 'Y', 'X']

    # A diamond records the shared ancestor once, at its first visit.
    double_u = _grammar('W', [])
    wye = _grammar('Y', ['W'])
    zed = _grammar('Z', ['W'])
    ex = _grammar('X', ['Y', 'Z'])
    assert walk_ancestry(ex, [double_u, wye, zed, ex]) == ['Y', 'W', 'Z', 'X']

    # Unrelated parents keep declared order, so the later parent has the higher index.
    wye = _grammar('Y', [])
    zed = _grammar('Z', [])
    ex = _grammar('X', ['Y', 'Z'])
    assert walk_ancestry(ex, [wye, zed, ex]) == ['Y', 'Z', 'X']

    # A missing parent contributes nothing and does not raise.
    missing_parent = _grammar('child', ['missing'])
    assert walk_ancestry(missing_parent, [missing_parent]) == ['child']

    # A parent chain that revisits an id, including the target, terminates.
    self_parent = _grammar('loop', ['loop'])
    assert walk_ancestry(self_parent, [self_parent]) == ['loop', 'loop']
    target = _grammar('X', ['Y'])
    parent = _grammar('Y', ['X'])
    assert walk_ancestry(target, [target, parent]) == ['X', 'Y', 'X']

# ** test: selector_does_not_mutate_inputs
def test_selector_does_not_mutate_inputs():
    '''
    Leave catalogues and aggregates unchanged.
    '''

    # Snapshot every list and aggregate the selector will read.
    base = _grammar('base', [])
    child = _grammar('child', ['base'])
    grammars = [base, child]
    tokens = [
        _token('PLUS', 'base'),
        _token('PLUS', 'other'),
    ]
    productions = [
        _production('expr', 'base'),
        _production('expr', 'other'),
    ]
    parent_ids = ['base']
    before = (
        _dumps(grammars),
        _dumps(tokens),
        _dumps(productions),
        list(parent_ids),
        list(child.parent_ids),
    )

    # Every operation returns without rewriting its arguments.
    grammar_index(grammars)
    walk_ancestry(child, grammars)
    GrammarRuleSelector.select_tokens(child, grammars, tokens)
    GrammarRuleSelector.select_productions(child, grammars, productions)
    GrammarRuleSelector.has_cycle('child', parent_ids, grammars)
    assert (
        _dumps(grammars),
        _dumps(tokens),
        _dumps(productions),
        parent_ids,
        child.parent_ids,
    ) == before

# ** test: select_tokens_keeps_closer_name
def test_select_tokens_keeps_closer_name():
    '''
    Filter by ancestry and keep the closer declaration of a shared token name.
    '''

    # The dialect composes the base grammar, so the base sits at the lower index.
    base = _grammar('arithmetic', [])
    dialect = _grammar('arithmetic_with_comments', ['arithmetic'])
    grammars = [base, dialect]
    assert walk_ancestry(dialect, grammars) == [
        'arithmetic',
        'arithmetic_with_comments',
    ]
    plus = _token('PLUS', 'arithmetic')
    base_space = _token('WHITESPACE', 'arithmetic')
    dialect_space = _token('WHITESPACE', 'arithmetic_with_comments')
    outside = _token('PLUS', 'other')

    # The later whitespace wins and stays after PLUS. The outside token drops.
    selected = GrammarRuleSelector.select_tokens(
        dialect,
        grammars,
        [plus, base_space, dialect_space, outside],
    )
    assert selected == [plus, dialect_space]
    assert selected[0] is plus
    assert selected[1] is dialect_space

    # The same winner stays in its earlier input position.
    reordered = GrammarRuleSelector.select_tokens(
        dialect,
        grammars,
        [dialect_space, plus, base_space],
    )
    assert reordered == [dialect_space, plus]
    assert reordered[0] is dialect_space
    assert reordered[1] is plus

    # Same-grammar repetitions of a name are not a farther declaration.
    first_plus = _token('PLUS', 'arithmetic')
    second_plus = _token('PLUS', 'arithmetic')
    repeated = GrammarRuleSelector.select_tokens(
        base,
        [base],
        [first_plus, second_plus],
    )
    assert repeated == [first_plus, second_plus]
    assert repeated[0] is first_plus
    assert repeated[1] is second_plus

# ** test: select_productions_keeps_repeated_names
def test_select_productions_keeps_repeated_names():
    '''
    Drop out-of-ancestry productions and keep repeated names.
    '''

    # Both grammars are in scope for the dialect.
    base = _grammar('arithmetic', [])
    dialect = _grammar('arithmetic_with_comments', ['arithmetic'])
    same_a = _production('expr', 'arithmetic')
    same_b = _production('expr', 'arithmetic')
    other_grammar = _production('expr', 'arithmetic_with_comments')
    outside = _production('expr', 'other')
    term = _production('term', 'arithmetic')

    # Order is input order. Name is not a uniqueness key.
    selected = GrammarRuleSelector.select_productions(
        dialect,
        [base, dialect],
        [outside, same_a, term, same_b, other_grammar],
    )
    assert selected == [same_a, term, same_b, other_grammar]
    assert selected[0] is same_a
    assert selected[1] is term
    assert selected[2] is same_b
    assert selected[3] is other_grammar

# ** test: has_cycle_uses_candidate_parents
def test_has_cycle_uses_candidate_parents():
    '''
    Answer the cycle question from the candidate parent list.
    '''

    # A direct self-parent is a cycle even when the id is not in the catalogue.
    assert GrammarRuleSelector.has_cycle('g', ['g'], []) is True

    # An intermediate grammar that names the candidate is a cycle.
    mid = _grammar('mid', ['new'])
    assert GrammarRuleSelector.has_cycle('new', ['mid'], [mid]) is True

    # The candidate frontier wins over the persisted parent list.
    safe = _grammar('safe', [])
    persisted = _grammar('g', ['safe'])
    looper = _grammar('looper', ['g'])
    assert GrammarRuleSelector.has_cycle(
        'g',
        ['looper'],
        [safe, persisted, looper],
    ) is True

    # A diamond that never names the target is not a cycle.
    double_u = _grammar('W', [])
    wye = _grammar('Y', ['W'])
    zed = _grammar('Z', ['W'])
    ex = _grammar('X', [])
    assert GrammarRuleSelector.has_cycle(
        'X',
        ['Y', 'Z'],
        [double_u, wye, zed, ex],
    ) is False
    assert GrammarRuleSelector.has_cycle('g', [], [persisted]) is False

    # A missing parent, or a missing parent of a present parent, is a dead end.
    assert GrammarRuleSelector.has_cycle('g', ['missing'], [persisted]) is False
    gap = _grammar('mid', ['gone'])
    assert GrammarRuleSelector.has_cycle('g', ['mid'], [gap]) is False
