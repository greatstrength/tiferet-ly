"""Tests for Tiferet-Ly Grammar Declaration Domain Model"""

# *** imports

# ** infra
import pytest
import yaml
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.grammar import GrammarDeclaration
from tiferet_ly.domain.production import ComplexProductionRule, ProductionRule, SimpleProductionRule
from tiferet_ly.domain.subgrammar import Subgrammar
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

# ** function: load_grammar
def load_grammar(yaml_text: str, grammar_id: str) -> dict:
    '''
    Parse raw YAML text and extract the entry for one declared grammar id
    from its `grammars:` root node, injecting `id` from the mapping key,
    mirroring the ConfigurationRepository lookup RFP-002 will implement.

    :param yaml_text: The raw YAML document text.
    :type yaml_text: str
    :param grammar_id: The id of the grammar declaration to extract.
    :type grammar_id: str
    :return: The declaration body with `id` injected.
    :rtype: dict
    '''

    # Parse the YAML document and locate the entry by id.
    data = yaml.safe_load(yaml_text)
    entry = data['grammars'][grammar_id]

    # Return the entry with the id injected from the mapping key.
    return {'id': grammar_id, **entry}

# *** tests

# ** test: grammar_declaration_construct_from_worked_example
def test_grammar_declaration_construct_from_worked_example() -> None:
    '''
    Test constructing a GrammarDeclaration from a worked YAML example
    covering all four rule variants.
    '''

    # Load and construct the declaration.
    declaration = GrammarDeclaration(**load_grammar(ARITHMETIC_YAML, 'arithmetic'))

    # Assert the id and start symbol are set correctly.
    assert declaration.id == 'arithmetic'
    assert declaration.start == 'expression'

    # Assert every rule variant constructed to its correct type.
    assert isinstance(declaration.token_rules[0], SimpleTokenRule)
    assert isinstance(declaration.token_rules[2], ComplexTokenRule)
    assert isinstance(declaration.production_rules[0], ComplexProductionRule)
    assert isinstance(declaration.production_rules[1], SimpleProductionRule)

# ** test: grammar_declaration_multi_grammar_root_node
def test_grammar_declaration_multi_grammar_root_node() -> None:
    '''
    Test that a `grammars:` root node holding more than one declaration
    can be looked up by id, with id injected rather than duplicated.
    '''

    # Merge two documents' grammars: root nodes, as one multi-language file would hold.
    combined_grammars = {
        **yaml.safe_load(ARITHMETIC_YAML)['grammars'],
        **yaml.safe_load(MULTI_SUBGRAMMAR_YAML)['grammars'],
    }

    # Both entries are locatable by id, with id injected from the mapping key.
    arithmetic = GrammarDeclaration(id='arithmetic', **combined_grammars['arithmetic'])
    tiferet_module = GrammarDeclaration(id='tiferet_module', **combined_grammars['tiferet_module'])

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
    declaration = GrammarDeclaration(**load_grammar(ARITHMETIC_YAML, 'arithmetic'))

    # Assert declared order is preserved exactly, not re-sorted.
    assert [rule.name for rule in declaration.token_rules] == ['ZETA', 'PLUS', 'NUMBER']

# ** test: grammar_declaration_requires_valid_start
def test_grammar_declaration_requires_valid_start() -> None:
    '''
    Test that a start naming no declared production raises ValidationError.
    '''

    # Build declaration data with a start that names no production.
    data = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    data['start'] = 'nonexistent'

    # Constructing with an invalid start raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**data)

# ** test: grammar_declaration_rejects_malformed_rule
def test_grammar_declaration_rejects_malformed_rule() -> None:
    '''
    Test that a token rule with neither action nor pattern raises
    ValidationError rather than silently producing a partial rule.
    '''

    # Build declaration data with a malformed token rule (no pattern, no action).
    data = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    data['token_rules'] = [{'MALFORMED': {}}]

    # Constructing with the malformed rule raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**data)

# ** test: grammar_declaration_rejects_duplicate_token_names
def test_grammar_declaration_rejects_duplicate_token_names() -> None:
    '''
    Test that declaring the same token rule name twice raises ValidationError.
    '''

    # Build declaration data with a duplicated token rule name.
    data = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    data['token_rules'] = [{'PLUS': {'pattern': '+'}}, {'PLUS': {'pattern': '++'}}]

    # Constructing with duplicate token names raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**data)

# ** test: grammar_declaration_requires_non_empty_subgrammars
def test_grammar_declaration_requires_non_empty_subgrammars() -> None:
    '''
    Test that an empty subgrammars list raises ValidationError.
    '''

    # Build declaration data with an empty subgrammars list.
    data = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    data['subgrammars'] = []

    # Constructing with an empty subgrammars list raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**data)

# ** test: grammar_declaration_rejects_undeclared_subgrammar_reference
def test_grammar_declaration_rejects_undeclared_subgrammar_reference() -> None:
    '''
    Test that a rule tagged with a subgrammar absent from `subgrammars`
    raises ValidationError.
    '''

    # Build declaration data with a rule referencing an undeclared subgrammar.
    data = load_grammar(ARITHMETIC_YAML, 'arithmetic')
    data['token_rules'][0]['ZETA']['subgrammar'] = 'nonexistent'

    # Constructing with the undeclared subgrammar reference raises ValidationError.
    with pytest.raises(ValidationError):
        GrammarDeclaration(**data)

# ** test: grammar_declaration_multi_subgrammar_common_and_tagged_rules
def test_grammar_declaration_multi_subgrammar_common_and_tagged_rules() -> None:
    '''
    Test a worked example with at least one common rule (subgrammar
    unset) and at least one subgrammar-tagged rule in the same catalogue.
    '''

    # Load and construct the multi-subgrammar declaration.
    declaration = GrammarDeclaration(**load_grammar(MULTI_SUBGRAMMAR_YAML, 'tiferet_module'))

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
    declaration = GrammarDeclaration(**load_grammar(MULTI_SUBGRAMMAR_YAML, 'tiferet_module'))

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
