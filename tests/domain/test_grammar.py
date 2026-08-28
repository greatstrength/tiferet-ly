"""Tests for Tiferet-Ly Grammar Domain Model"""

# *** imports

# ** core
from typing import Any, Dict, List

# ** infra
import pytest
import yaml
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.grammar import Grammar
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.domain.production import ComplexProductionRule, ProductionRule, SimpleProductionRule
from tiferet_ly.domain.token import ComplexTokenRule, SimpleTokenRule, TokenRule

# *** constants
#
# A single worked YAML document covering all three root-node shapes this
# RFP specifies (`grammars:`, `tokens:`, `production_rules:`), every rule
# variant, and a multi-entry `parent_ids` composition (`tiferet_module`
# extends both `core` and `domain_extra`). Sufficient for RFP-002 to build
# per-type mappers against without further format design.

# ** constant: worked_yaml
WORKED_YAML = '''
grammars:
  core:
    parent_ids: []
    start: module
  domain_extra:
    parent_ids: []
    start: attr_decl
  tiferet_module:
    parent_ids: [core, domain_extra]
    start: module

tokens:
  - ZETA:
      grammar_id: core
      pattern: 'z'
  - PLUS:
      grammar_id: core
      pattern: '\\+'
  - NUMBER:
      grammar_id: core
      pattern: '\\d+'
      action: |
        t.value = int(t.value)
        return t
  - COLON:
      grammar_id: domain_extra
      pattern: ':'
  - PLUS:
      grammar_id: domain_extra
      pattern: '\\+\\+'

production_rules:
  - expression:
      grammar_id: core
      spec: 'expression : expression PLUS term'
      action: |
        p[0] = p[1] + p[3]
  - expression:
      grammar_id: core
      spec: 'expression : term'
  - attr_decl:
      grammar_id: domain_extra
      spec: 'attr_decl : IDENTIFIER COLON EQUALS NEWLINE'
'''

# *** functions
#
# The helpers below stand in for the mapper/TransferObject layer RFP-002
# will implement: they expand the RFP's YAML shapes into the domain
# objects TokenRule/ProductionRule/Grammar actually accept. None of these
# domain objects interprets this raw shape itself; the helpers exist only
# to prove the documented format is sufficient to build a mapper against.

# ** function: expand_keyed_entries
def expand_keyed_entries(entries: List[Any], key_field: str) -> List[Dict[str, Any]]:
    '''
    Expand a YAML-style sequence of single-key mappings (e.g. ``- PLUS:
    {pattern: '+'}``) into a sequence of flat dicts carrying ``key_field``.

    :param entries: The raw catalogue entries.
    :type entries: List[Any]
    :param key_field: The field name the single mapping key is injected under.
    :type key_field: str
    :return: The expanded, flat-dict entries.
    :rtype: List[Dict[str, Any]]
    '''

    # Expand each single-key YAML mapping into a flat dict.
    expanded = []
    for entry in entries or []:
        ((key, body),) = entry.items()
        expanded.append({key_field: key, **(body or {})})

    # Return the expanded entries.
    return expanded

# ** function: build_token_rules
def build_token_rules(entries: List[Any]) -> List[TokenRule]:
    '''
    Expand and construct the flat token rule catalogue, dispatching to the
    simple or complex variant by the presence of an action.

    :param entries: The raw tokens: catalogue entries.
    :type entries: List[Any]
    :return: The constructed TokenRule instances, in declared order.
    :rtype: List[TokenRule]
    '''

    # Construct the correct variant for each expanded entry.
    return [
        ComplexTokenRule(**entry) if 'action' in entry else SimpleTokenRule(**entry)
        for entry in expand_keyed_entries(entries, key_field='name')
    ]

# ** function: build_production_rules
def build_production_rules(entries: List[Any]) -> List[ProductionRule]:
    '''
    Expand and construct the flat production rule catalogue, dispatching
    to the simple or complex variant by the presence of an action.

    :param entries: The raw production_rules: catalogue entries.
    :type entries: List[Any]
    :return: The constructed ProductionRule instances, in declared order.
    :rtype: List[ProductionRule]
    '''

    # Construct the correct variant for each expanded entry.
    return [
        ComplexProductionRule(**entry) if 'action' in entry else SimpleProductionRule(**entry)
        for entry in expand_keyed_entries(entries, key_field='name')
    ]

# ** function: build_grammars
def build_grammars(grammars_node: Dict[str, Any]) -> List[Grammar]:
    '''
    Construct the flat, id-keyed grammars: root node into Grammar
    instances, mirroring how ErrorConfigRepository injects id from the
    mapping key.

    :param grammars_node: The raw grammars: mapping (id -> body).
    :type grammars_node: Dict[str, Any]
    :return: The constructed Grammar instances.
    :rtype: List[Grammar]
    '''

    # Construct a Grammar for each id-keyed entry, injecting id from the key.
    return [Grammar(id=grammar_id, **body) for grammar_id, body in (grammars_node or {}).items()]

# ** function: load_worked_document
def load_worked_document() -> Dict[str, Any]:
    '''
    Parse the module's worked YAML document.

    :return: The parsed document.
    :rtype: Dict[str, Any]
    '''

    # Parse and return the raw document.
    return yaml.safe_load(WORKED_YAML)

# *** tests

# ** test: grammar_construct_minimal
def test_grammar_construct_minimal() -> None:
    '''
    Test constructing a Grammar with only id and start; parent_ids
    defaults to an empty list.
    '''

    # Construct a root grammar with no ancestors.
    grammar = Grammar(id='core', start='module')

    # Assert the fields are set correctly.
    assert grammar.id == 'core'
    assert grammar.start == 'module'
    assert grammar.parent_ids == []

# ** test: grammar_construct_with_parent_ids
def test_grammar_construct_with_parent_ids() -> None:
    '''
    Test constructing a Grammar with an explicit, ordered parent_ids list.
    '''

    # Construct a grammar extending two parents in declared order.
    grammar = Grammar(id='tiferet_module', parent_ids=['core', 'domain_extra'], start='module')

    # Assert declared order is preserved exactly.
    assert grammar.parent_ids == ['core', 'domain_extra']

# ** test: no_subgrammar_or_grammar_declaration_type
def test_no_subgrammar_or_grammar_declaration_type() -> None:
    '''
    Test that the retired Subgrammar and GrammarDeclaration types no
    longer exist anywhere in the domain package.
    '''

    # Importing either retired type from the domain package must fail.
    with pytest.raises(ImportError):
        from tiferet_ly.domain import Subgrammar  # noqa: F401
    with pytest.raises(ImportError):
        from tiferet_ly.domain import GrammarDeclaration  # noqa: F401

    # The domain package itself must not expose either name.
    import tiferet_ly.domain as domain
    assert not hasattr(domain, 'Subgrammar')
    assert not hasattr(domain, 'GrammarDeclaration')

# ** test: grammar_has_exactly_five_fields
def test_grammar_has_exactly_five_fields() -> None:
    '''
    Test that Grammar carries exactly id, parent_ids, start, ignore, and
    layout — no token_rules, production_rules, or subgrammars field of
    any kind.
    '''

    # Assert the field set matches exactly.
    assert set(Grammar.model_fields) == {'id', 'parent_ids', 'start', 'ignore', 'layout'}

# ** test: grammar_forbids_extra_fields
def test_grammar_forbids_extra_fields() -> None:
    '''
    Test that an unknown field raises ValidationError, per DomainObject's extra='forbid' config.
    '''

    # An unrecognized field is rejected.
    with pytest.raises(ValidationError):
        Grammar(id='core', start='module', token_rules=[])

# ** test: grammar_requires_id
def test_grammar_requires_id() -> None:
    '''
    Test that constructing a Grammar without an id raises ValidationError.
    '''

    # Missing id raises ValidationError.
    with pytest.raises(ValidationError):
        Grammar(start='module')

# ** test: grammar_requires_start
def test_grammar_requires_start() -> None:
    '''
    Test that constructing a Grammar without a start symbol raises ValidationError.
    '''

    # Missing start raises ValidationError.
    with pytest.raises(ValidationError):
        Grammar(id='core')

# ** test: grammar_does_not_validate_unresolvable_parent_id
def test_grammar_does_not_validate_unresolvable_parent_id() -> None:
    '''
    Test that a Grammar naming a parent_ids entry that does not resolve
    to any other declared grammar does not raise. Grammar has no access
    to the full grammar set and performs no such check.
    '''

    # Construct with a parent id that names no other declared grammar.
    grammar = Grammar(id='tiferet_module', parent_ids=['nonexistent'], start='module')

    # Assert construction succeeded, proving no existence check ran.
    assert grammar.parent_ids == ['nonexistent']

# ** test: grammar_does_not_validate_empty_parent_ids
def test_grammar_does_not_validate_empty_parent_ids() -> None:
    '''
    Test that an explicitly empty parent_ids list is valid, representing
    a root grammar with no ancestors.
    '''

    # Construct with an explicitly empty parent_ids list.
    grammar = Grammar(id='core', parent_ids=[], start='module')

    # Assert construction succeeded with the empty list preserved.
    assert grammar.parent_ids == []

# ** test: grammar_does_not_detect_self_referential_cycles
def test_grammar_does_not_detect_self_referential_cycles() -> None:
    '''
    Test that a Grammar directly listing itself as its own parent does
    not raise. Cycle detection is a cross-aggregate concern belonging to
    whatever writes a Grammar (AddGrammar/UpdateGrammar), not to Grammar's
    own construction.
    '''

    # Construct a grammar that names itself as a parent.
    grammar = Grammar(id='core', parent_ids=['core'], start='module')

    # Assert construction succeeded, proving no cycle check ran.
    assert grammar.parent_ids == ['core']

# ** test: grammar_ignore_defaults_to_none
def test_grammar_ignore_defaults_to_none() -> None:
    '''
    Test that a Grammar with no declared ignore defaults to None.
    '''

    # Construct a grammar with no ignore declared.
    core = Grammar(id='core', start='module')

    # Assert ignore defaults to None.
    assert core.ignore is None

# ** test: grammar_ignore_construct
def test_grammar_ignore_construct() -> None:
    '''
    Test constructing a Grammar with a declared ignore pattern.
    '''

    # Construct a grammar that skips spaces and tabs before token matching.
    core = Grammar(id='core', start='module', ignore=' \t')

    # Assert the declared ignore pattern is set exactly.
    assert core.ignore == ' \t'

# ** test: grammar_layout_defaults_to_none
def test_grammar_layout_defaults_to_none() -> None:
    '''
    Test that a Grammar with no declared layout profile defaults to None.
    '''

    # Construct a grammar with no layout declared.
    core = Grammar(id='core', start='module')

    # Assert layout defaults to None.
    assert core.layout is None

# ** test: grammar_layout_construct
def test_grammar_layout_construct() -> None:
    '''
    Test constructing a Grammar with a declared LayoutProfile.
    '''

    # Construct a grammar declaring an indent/dedent layout profile.
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
    core = Grammar(id='core', start='module', layout=profile)

    # Assert the declared layout profile is set exactly.
    assert core.layout is profile
    assert core.layout.indent_token == 'INDENT'

# ** test: grammar_does_not_validate_start_against_any_production
def test_grammar_does_not_validate_start_against_any_production() -> None:
    '''
    Test that a start symbol naming no declared production anywhere does
    not raise. Grammar holds no production catalogue to check against;
    that validation belongs to whatever writes a Grammar.
    '''

    # Construct with a start symbol that names no production at all.
    grammar = Grammar(id='core', start='nonexistent_production')

    # Assert construction succeeded, proving no reference check ran.
    assert grammar.start == 'nonexistent_production'

# ** test: no_field_shaped_like_error_rule_or_precedence
def test_no_field_shaped_like_error_rule_or_precedence() -> None:
    '''
    Test that no TokenRule, ProductionRule, or Grammar field is named or
    shaped like an error-rule (t_error/p_error) or a precedence/
    associativity concept.
    '''

    # Collect every declared field name across the relevant models.
    field_names = {
        *TokenRule.model_fields,
        *ComplexTokenRule.model_fields,
        *ProductionRule.model_fields,
        *ComplexProductionRule.model_fields,
        *Grammar.model_fields,
    }

    # Assert no field name suggests an error-rule or precedence/associativity concept.
    assert not any('error' in name.lower() for name in field_names)
    assert not any(
        'precedence' in name.lower() or 'assoc' in name.lower()
        for name in field_names
    )

# ** test: worked_yaml_grammars_root_node_flat_id_keyed
def test_worked_yaml_grammars_root_node_flat_id_keyed() -> None:
    '''
    Test that the grammars: root node is a flat, id-keyed mapping (like
    errors:), with id injected from the mapping key rather than
    duplicated in the body.
    '''

    # Build every declared grammar from the worked document.
    grammars = build_grammars(load_worked_document()['grammars'])
    grammars_by_id = {grammar.id: grammar for grammar in grammars}

    # Assert all three declared grammars are locatable by their injected id.
    assert set(grammars_by_id) == {'core', 'domain_extra', 'tiferet_module'}

# ** test: worked_yaml_multi_entry_parent_ids_composition
def test_worked_yaml_multi_entry_parent_ids_composition() -> None:
    '''
    Test that a grammar's parent_ids may name more than one independent
    parent, in declared order, per the worked multi-parent example.
    '''

    # Build the declared grammars and locate the composing one.
    grammars = build_grammars(load_worked_document()['grammars'])
    tiferet_module = next(grammar for grammar in grammars if grammar.id == 'tiferet_module')

    # Assert both parents are present in declared order.
    assert tiferet_module.parent_ids == ['core', 'domain_extra']

# ** test: worked_yaml_token_rules_construct_all_variants
def test_worked_yaml_token_rules_construct_all_variants() -> None:
    '''
    Test that the tokens: root node's entries construct to the correct
    Simple/Complex variant by the presence of an action, each carrying
    its own grammar_id.
    '''

    # Build the flat token rule catalogue.
    token_rules = build_token_rules(load_worked_document()['tokens'])

    # Assert every rule variant constructed to its correct type with the right grammar_id.
    assert isinstance(token_rules[0], SimpleTokenRule) and token_rules[0].grammar_id == 'core'
    assert isinstance(token_rules[2], ComplexTokenRule) and token_rules[2].grammar_id == 'core'
    assert isinstance(token_rules[3], SimpleTokenRule) and token_rules[3].grammar_id == 'domain_extra'

# ** test: worked_yaml_token_rule_order_preserved_across_flat_catalogue
def test_worked_yaml_token_rule_order_preserved_across_flat_catalogue() -> None:
    '''
    Test that token rule iteration order matches the deliberately
    non-alphabetical declared order across the entire flat catalogue
    (ZETA before PLUS before NUMBER before COLON before the second PLUS),
    not re-sorted and not partitioned by grammar_id.
    '''

    # Build the flat token rule catalogue.
    token_rules = build_token_rules(load_worked_document()['tokens'])

    # Assert declared order is preserved exactly across the flat catalogue.
    assert [rule.name for rule in token_rules] == ['ZETA', 'PLUS', 'NUMBER', 'COLON', 'PLUS']

# ** test: worked_yaml_production_rules_construct_all_variants
def test_worked_yaml_production_rules_construct_all_variants() -> None:
    '''
    Test that the production_rules: root node's entries construct to the
    correct Simple/Complex variant by the presence of an action, each
    carrying its own grammar_id.
    '''

    # Build the flat production rule catalogue.
    production_rules = build_production_rules(load_worked_document()['production_rules'])

    # Assert every rule variant constructed to its correct type with the right grammar_id.
    assert isinstance(production_rules[0], ComplexProductionRule) and production_rules[0].grammar_id == 'core'
    assert isinstance(production_rules[1], SimpleProductionRule) and production_rules[1].grammar_id == 'core'
    assert isinstance(production_rules[2], SimpleProductionRule) and production_rules[2].grammar_id == 'domain_extra'

# ** test: worked_yaml_token_catalogue_tolerates_cross_grammar_name_reuse
def test_worked_yaml_token_catalogue_tolerates_cross_grammar_name_reuse() -> None:
    '''
    Test that the flat tokens: catalogue can hold two entries sharing the
    same name (PLUS) declared under different grammar_id values, each
    independently selectable by filtering on grammar_id.
    '''

    # Build the flat token rule catalogue.
    token_rules = build_token_rules(load_worked_document()['tokens'])

    # Filter each grammar's own PLUS rule out of the shared flat catalogue.
    core_plus = [rule for rule in token_rules if rule.name == 'PLUS' and rule.grammar_id == 'core']
    domain_extra_plus = [rule for rule in token_rules if rule.name == 'PLUS' and rule.grammar_id == 'domain_extra']

    # Assert both grammars' own PLUS rule is present and distinct.
    assert len(core_plus) == 1 and core_plus[0].pattern == r'\+'
    assert len(domain_extra_plus) == 1 and domain_extra_plus[0].pattern == r'\+\+'
