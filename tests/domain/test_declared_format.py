"""Tiferet Ly Declared Format Tests"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import yaml

# ** app
from tiferet_ly import domain

# *** constants

# ** constant: fixture_path
FIXTURE_PATH = (
    Path(__file__).parents[1] / 'fixtures' / 'declared_language.yml'
)

# *** functions

# ** function: assert_rule_sequence
def assert_rule_sequence(entries):
    '''
    Assert a rule catalogue is an ordered sequence of single-key mappings.

    :param entries: The declared rule catalogue.
    :type entries: list
    '''

    # The catalogue is a sequence, and every body names its grammar.
    assert isinstance(entries, list)
    assert entries
    for entry in entries:
        assert isinstance(entry, dict)
        assert len(entry) == 1
        body = next(iter(entry.values()))
        assert 'grammar_id' in body

# *** tests

# ** test: domain_exports
def test_domain_exports():
    '''
    Export exactly the seven declared-language domain classes.
    '''

    # The package surface is exactly the six rule classes and Grammar.
    assert domain.__all__ == [
        'TokenRule',
        'SimpleTokenRule',
        'ComplexTokenRule',
        'ProductionRule',
        'SimpleProductionRule',
        'ComplexProductionRule',
        'Grammar',
    ]
    for name in domain.__all__:
        assert getattr(domain, name).__name__ == name

# ** test: declared_format_shape
def test_declared_format_shape():
    '''
    Verify the fixture's root nodes and declared entry shape.
    '''

    # Load the declared language without mapping it to a model.
    document = yaml.safe_load(FIXTURE_PATH.read_text(encoding='utf-8'))

    # The root-node set is exactly the three frozen catalogues.
    assert set(document) == {'grammars', 'tokens', 'production_rules'}

    # Grammars are an identifier-keyed mapping, including a multi-parent entry.
    assert isinstance(document['grammars'], dict)
    assert document['grammars']['expr']['parent_ids'] == []
    assert document['grammars']['arith']['parent_ids'] == ['expr', 'factor']

    # Token entries are an ordered sequence of single-key mappings.
    assert_rule_sequence(document['tokens'])
    assert document['tokens'][0]['NUMBER']['pattern'] == '[0-9]+'
    assert 'action' not in document['tokens'][0]['NUMBER']
    assert document['tokens'][1]['PLUS']['action'] == 't.value = int(t.value)'

    # Production entries repeat a name as alternatives and cover both variants.
    assert_rule_sequence(document['production_rules'])
    assert list(document['production_rules'][0]) == ['expr']
    assert list(document['production_rules'][1]) == ['expr']
    assert document['production_rules'][0]['expr']['spec'] != (
        document['production_rules'][1]['expr']['spec']
    )
    assert 'action' in document['production_rules'][0]['expr']
    assert 'action' not in document['production_rules'][1]['expr']
