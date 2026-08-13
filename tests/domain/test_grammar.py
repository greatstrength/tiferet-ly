"""Tests for Tiferet-Ly Grammar Declaration Domain Model"""

# *** imports

# ** core
from typing import Any, Dict, List

# ** infra
import pytest
import yaml
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.grammar import GrammarDeclaration, Subgrammar
from tiferet_ly.domain.production import ComplexProductionRule, ProductionRule, SimpleProductionRule
from tiferet_ly.domain.token import ComplexTokenRule, SimpleTokenRule, TokenRule

# *** constants

# ** constant: arithmetic_yaml
ARITHMETIC_YAML = '''
grammars:
  arithmetic:
    start: expression
    subgrammars:
      - core:
    token_rules:
      - ZETA:
          pattern: 'z'
      - PLUS:
          pattern: '\\+'
      - NUMBER:
          pattern: '\\d+'
          action: |
            t.value = int(t.value)
            return t
    production_rules:
      - expression:
          spec: 'expression : expression PLUS term'
          action: |
            p[0] = p[1] + p[3]
      - expression:
          spec: 'expression : term'
'''

# ** constant: multi_subgrammar_yaml
MULTI_SUBGRAMMAR_YAML = '''
grammars:
  tiferet_module:
    start: module
    subgrammars:
      - core:
      - domain:
          description: Adds initialized attribute declarations.
    token_rules:
      - CLASS:
          pattern: 'class'
      - COLON:
          pattern: ':'
          subgrammar: domain
      - EQUALS:
          pattern: '='
          subgrammar: domain
      - NEWLINE:
          pattern: '\\n'
    production_rules:
      - module:
          spec: 'module : CLASS NEWLINE'
      - attr_decl:
          spec: 'attr_decl : IDENTIFIER COLON EQUALS NEWLINE'
          subgrammar: domain
'''

# *** functions
#
# The helpers below stand in for the mapper/TransferObject layer RFP-002
# will implement: they expand the RFP's YAML sequence-of-single-key-
# mappings shape into the domain objects GrammarDeclaration actually
# accepts, and dispatch simple vs. complex construction. GrammarDeclaration
# itself never sees this raw shape; it is exercised here only to prove the
# documented format is sufficient to build a mapper against.

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
    Expand and construct the token rule catalogue, dispatching to the
    simple or complex variant by the presence of an action.

    :param entries: The raw token_rules catalogue entries.
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
    Expand and construct the production rule catalogue, dispatching to the
    simple or complex variant by the presence of an action.

    :param entries: The raw production_rules catalogue entries.
    :type entries: List[Any]
    :return: The constructed ProductionRule instances, in declared order.
    :rtype: List[ProductionRule]
    '''

    # Construct the correct variant for each expanded entry.
    return [
        ComplexProductionRule(**entry) if 'action' in entry else SimpleProductionRule(**entry)
        for entry in expand_keyed_entries(entries, key_field='name')
    ]

# ** function: build_subgrammars
def build_subgrammars(entries: List[Any]) -> List[Subgrammar]:
    '''
    Expand and construct the subgrammar registry.

    :param entries: The raw subgrammars catalogue entries.
    :type entries: List[Any]
    :return: The constructed Subgrammar instances, in declared order.
    :rtype: List[Subgrammar]
    '''

    # Construct a Subgrammar for each expanded entry.
    return [Subgrammar(**entry) for entry in expand_keyed_entries(entries, key_field='id')]

# ** function: load_grammar_kwargs
def load_grammar_kwargs(yaml_text: str, grammar_id: str) -> Dict[str, Any]:
    '''
    Parse raw YAML text, extract the entry for one declared grammar id
    from its `grammars:` root node (injecting `id` from the mapping key,
    mirroring the ConfigurationRepository lookup RFP-002 will implement),
    and expand it into the constructor kwargs GrammarDeclaration accepts.

    :param yaml_text: The raw YAML document text.
    :type yaml_text: str
    :param grammar_id: The id of the grammar declaration to extract.
    :type grammar_id: str
    :return: The constructor kwargs for GrammarDeclaration.
    :rtype: Dict[str, Any]
    '''

    # Parse the YAML document and locate the entry by id.
    entry = yaml.safe_load(yaml_text)['grammars'][grammar_id]

    # Expand each catalogue into constructed domain objects.
    return {
        'id': grammar_id,
        'start': entry['start'],
        'subgrammars': build_subgrammars(entry.get('subgrammars')),
        'token_rules': build_token_rules(entry.get('token_rules')),
        'production_rules': build_production_rules(entry.get('production_rules')),
    }

# ** function: load_grammar
def load_grammar(yaml_text: str, grammar_id: str) -> GrammarDeclaration:
    '''
    Construct a GrammarDeclaration from a worked YAML example.

    :param yaml_text: The raw YAML document text.
    :type yaml_text: str
    :param grammar_id: The id of the grammar declaration to construct.
    :type grammar_id: str
    :return: The constructed GrammarDeclaration.
    :rtype: GrammarDeclaration
    '''

    # Construct the declaration from the expanded kwargs.
    return GrammarDeclaration(**load_grammar_kwargs(yaml_text, grammar_id))

# *** tests

# ** test: subgrammar_construct_minimal
def test_subgrammar_construct_minimal() -> None:
    '''
    Test constructing a Subgrammar with only the required id.
    '''

    # Construct the subgrammar without a description.
    subgrammar = Subgrammar(id='core')

    # Assert the fields are set correctly.
    assert subgrammar.id == 'core'
    assert subgrammar.description is None

# ** test: subgrammar_construct_with_description
def test_subgrammar_construct_with_description() -> None:
    '''
    Test constructing a Subgrammar with an id and a description.
    '''

    # Construct the subgrammar with a description.
    subgrammar = Subgrammar(
        id='domain',
        description='Adds initialized attribute declarations.',
    )

    # Assert the fields are set correctly.
    assert subgrammar.id == 'domain'
    assert subgrammar.description == 'Adds initialized attribute declarations.'

# ** test: subgrammar_requires_id
def test_subgrammar_requires_id() -> None:
    '''
    Test that constructing a Subgrammar without an id raises ValidationError.
    '''

    # Missing id raises ValidationError.
    with pytest.raises(ValidationError):
        Subgrammar(description='Missing id.')

# ** test: grammar_declaration_construct_from_worked_example
def test_grammar_declaration_construct_from_worked_example() -> None:
    '''
    Test constructing a GrammarDeclaration from a worked YAML example
    covering all four rule variants.
    '''

    # Load and construct the declaration.
    declaration = load_grammar(ARITHMETIC_YAML, 'arithmetic')

    # Assert the id and start symbol are set correctly.
    assert declaration.id == 'arithmetic'
    assert declaration.start == 'expression'

    # Assert every rule variant constructed to its correct type.
    assert isinstance(declaration.token_rules[0], SimpleTokenRule)
    assert isinstance(declaration.token_rules[2], ComplexTokenRule)
    assert isinstance(declaration.production_rules[0], ComplexProductionRule)
    assert isinstance(declaration.production_rules[1], SimpleProductionRule)

# ** test: grammar_declaration_accepts_already_constructed_instances
def test_grammar_declaration_accepts_already_constructed_instances() -> None:
    '''
    Test that GrammarDeclaration can be constructed directly from
    already-built domain objects, with no YAML involved at all.
    '''

    # Construct the declaration purely from Python objects.
    declaration = GrammarDeclaration(
        id='minimal',
        start='expression',
        subgrammars=[Subgrammar(id='core')],
        token_rules=[SimpleTokenRule(name='PLUS', pattern=r'\+')],
        production_rules=[SimpleProductionRule(name='expression', spec='expression : PLUS')],
    )

    # Assert the declaration constructed successfully.
    assert declaration.id == 'minimal'
    assert declaration.token_rules[0].name == 'PLUS'

# ** test: grammar_declaration_rejects_raw_yaml_shaped_entries
def test_grammar_declaration_rejects_raw_yaml_shaped_entries() -> None:
    '''
    Test that GrammarDeclaration does not itself interpret the YAML
    sequence-of-single-key-mappings shape; passing raw, unexpanded entries
    raises ValidationError since they don't match TokenRule's own fields.
    This is the domain/mapper boundary the mapper layer is responsible for.
    '''

    # Build kwargs with a raw, unexpanded YAML-shaped token rule entry.
    kwargs = load_grammar_kwargs(ARITHMETIC_YAML, 'arithmetic')
    kwargs['token_rules'] = [{'MALFORMED': {}}]

    # Constructing with the raw shape raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**kwargs)

# ** test: grammar_declaration_multi_grammar_root_node
def test_grammar_declaration_multi_grammar_root_node() -> None:
    '''
    Test that a `grammars:` root node holding more than one declaration
    can be looked up by id, with id injected rather than duplicated.
    '''

    # Both entries are locatable by id, with id injected from the mapping key.
    arithmetic = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    tiferet_module = load_grammar(MULTI_SUBGRAMMAR_YAML, 'tiferet_module')

    # Assert both declarations constructed with their own id.
    assert arithmetic.id == 'arithmetic'
    assert tiferet_module.id == 'tiferet_module'

# ** test: token_rule_order_preserved_from_declaration
def test_token_rule_order_preserved_from_declaration() -> None:
    '''
    Test that token_rules iteration order matches the deliberately
    non-alphabetical declared order in the YAML document (ZETA before
    PLUS before NUMBER).
    '''

    # Construct the declaration from the worked example.
    declaration = load_grammar(ARITHMETIC_YAML, 'arithmetic')

    # Assert declared order is preserved exactly, not re-sorted.
    assert [rule.name for rule in declaration.token_rules] == ['ZETA', 'PLUS', 'NUMBER']

# ** test: grammar_declaration_requires_valid_start
def test_grammar_declaration_requires_valid_start() -> None:
    '''
    Test that a start naming no declared production raises ValidationError.
    '''

    # Build declaration kwargs with a start that names no production.
    kwargs = load_grammar_kwargs(ARITHMETIC_YAML, 'arithmetic')
    kwargs['start'] = 'nonexistent'

    # Constructing with an invalid start raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**kwargs)

# ** test: grammar_declaration_rejects_duplicate_token_names
def test_grammar_declaration_rejects_duplicate_token_names() -> None:
    '''
    Test that declaring the same token rule name twice raises ValidationError.
    '''

    # Build declaration kwargs with a duplicated token rule name.
    kwargs = load_grammar_kwargs(ARITHMETIC_YAML, 'arithmetic')
    kwargs['token_rules'] = [
        SimpleTokenRule(name='PLUS', pattern='+'),
        SimpleTokenRule(name='PLUS', pattern='++'),
    ]

    # Constructing with duplicate token names raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**kwargs)

# ** test: grammar_declaration_requires_non_empty_subgrammars
def test_grammar_declaration_requires_non_empty_subgrammars() -> None:
    '''
    Test that an empty subgrammars list raises ValidationError.
    '''

    # Build declaration kwargs with an empty subgrammars list.
    kwargs = load_grammar_kwargs(ARITHMETIC_YAML, 'arithmetic')
    kwargs['subgrammars'] = []

    # Constructing with an empty subgrammars list raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**kwargs)

# ** test: grammar_declaration_rejects_undeclared_subgrammar_reference
def test_grammar_declaration_rejects_undeclared_subgrammar_reference() -> None:
    '''
    Test that a rule tagged with a subgrammar absent from `subgrammars`
    raises ValidationError.
    '''

    # Build declaration kwargs with a rule referencing an undeclared subgrammar.
    kwargs = load_grammar_kwargs(ARITHMETIC_YAML, 'arithmetic')
    kwargs['token_rules'] = [SimpleTokenRule(name='ZETA', pattern='z', subgrammar='nonexistent')]

    # Constructing with the undeclared subgrammar reference raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**kwargs)

# ** test: grammar_declaration_multi_subgrammar_common_and_tagged_rules
def test_grammar_declaration_multi_subgrammar_common_and_tagged_rules() -> None:
    '''
    Test a worked example with at least one common rule (subgrammar
    unset) and at least one subgrammar-tagged rule in the same catalogue.
    '''

    # Load and construct the multi-subgrammar declaration.
    declaration = load_grammar(MULTI_SUBGRAMMAR_YAML, 'tiferet_module')

    # Assert the common and tagged rules are both present with correct tags.
    common_rules = [rule for rule in declaration.token_rules if rule.subgrammar is None]
    domain_rules = [rule for rule in declaration.token_rules if rule.subgrammar == 'domain']
    assert {rule.name for rule in common_rules} == {'CLASS', 'NEWLINE'}
    assert {rule.name for rule in domain_rules} == {'COLON', 'EQUALS'}

# ** test: grammar_declaration_filtering_preserves_declared_order
def test_grammar_declaration_filtering_preserves_declared_order() -> None:
    '''
    Test that filtering a catalogue down to "common plus one selected
    subgrammar" preserves the retained rules' original declared order.
    '''

    # Load the multi-subgrammar declaration.
    declaration = load_grammar(MULTI_SUBGRAMMAR_YAML, 'tiferet_module')

    # Filter to common-plus-domain rules, as a subgrammar-selecting consumer would.
    filtered = [
        rule for rule in declaration.token_rules
        if rule.subgrammar in (None, 'domain')
    ]

    # Assert the retained rules preserve their original declared order.
    assert [rule.name for rule in filtered] == ['CLASS', 'COLON', 'EQUALS', 'NEWLINE']

# ** test: grammar_declaration_has_no_error_rule_fields
def test_grammar_declaration_has_no_error_rule_fields() -> None:
    '''
    Test that no TokenRule, ProductionRule, or GrammarDeclaration model
    exposes an error-rule field of any kind (t_error/p_error equivalents).
    '''

    # Collect every declared field name across the relevant models.
    field_names = {
        *TokenRule.model_fields,
        *ComplexTokenRule.model_fields,
        *ProductionRule.model_fields,
        *ComplexProductionRule.model_fields,
        *GrammarDeclaration.model_fields,
        *Subgrammar.model_fields,
    }

    # Assert no field name suggests an error-rule concept.
    assert not any('error' in name.lower() for name in field_names)

# ** test: grammar_declaration_has_no_precedence_field
def test_grammar_declaration_has_no_precedence_field() -> None:
    '''
    Test that no precedence/associativity field exists anywhere in the
    model for v1.
    '''

    # Collect every declared field name across the relevant models.
    field_names = {
        *TokenRule.model_fields,
        *ComplexTokenRule.model_fields,
        *ProductionRule.model_fields,
        *ComplexProductionRule.model_fields,
        *GrammarDeclaration.model_fields,
        *Subgrammar.model_fields,
    }

    # Assert no field name suggests a precedence/associativity concept.
    assert not any(
        'precedence' in name.lower() or 'assoc' in name.lower()
        for name in field_names
    )
