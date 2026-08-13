"""Integration tests for Tiferet-Ly ProductionConfigRepository"""

# *** imports

# ** core
from pathlib import Path
from typing import List

# ** infra
import pytest
import yaml

# ** app
from tiferet_ly.domain.production import (
    ComplexProductionRule,
    SimpleProductionRule,
)
from tiferet_ly.repos.production import ProductionConfigRepository

# *** fixtures

# ** fixture: production_repo
@pytest.fixture
def production_repo(tmp_path: Path) -> ProductionConfigRepository:
    '''
    Build a ProductionConfigRepository against a real temporary YAML file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: The repository under test.
    :rtype: ProductionConfigRepository
    '''

    # Seed an empty YAML document so the loader can open the file.
    config_path = tmp_path / 'production_rules.yml'
    config_path.write_text('{}\n', encoding='utf-8')

    # Return the repository pointed at the temp file.
    return ProductionConfigRepository(production_config=str(config_path))

# *** functions

# ** function: names
def names(rules: List) -> List[str]:
    '''
    Collect rule names in list order.

    :param rules: The production rules.
    :type rules: List
    :return: The rule names.
    :rtype: List[str]
    '''

    # Return names in declared order.
    return [rule.name for rule in rules]

# *** tests

# ** test_int: production_repo_crud_five_methods
def test_int_production_repo_crud_five_methods(
    production_repo: ProductionConfigRepository,
) -> None:
    '''
    Prove exists/get/list/save/delete against a real temporary YAML file.
    '''

    # Save simple and complex rules under distinct composite keys.
    # Repository identity is (name, grammar_id); alternatives that share
    # both are outside this repository's keying model.
    complex_rule = ComplexProductionRule(
        name='expression',
        grammar_id='core',
        spec='expression : expression PLUS term',
        action='p[0] = p[1] + p[3]',
    )
    simple = SimpleProductionRule(
        name='term',
        grammar_id='core',
        spec='term : NUMBER',
    )
    other = SimpleProductionRule(
        name='expression',
        grammar_id='domain_extra',
        spec='expression : attr_decl',
    )
    production_repo.save(complex_rule)
    production_repo.save(simple)
    production_repo.save(other)

    # exists/get succeed for present keys.
    assert production_repo.exists('expression', 'core') is True
    assert production_repo.exists('expression', 'domain_extra') is True
    assert production_repo.exists('term', 'core') is True
    loaded = production_repo.get('expression', 'core')
    assert isinstance(loaded, ComplexProductionRule)
    assert loaded.action == 'p[0] = p[1] + p[3]'
    loaded_simple = production_repo.get('term', 'core')
    assert isinstance(loaded_simple, SimpleProductionRule)
    assert loaded_simple.spec == 'term : NUMBER'

    # list returns every entry unfiltered in declared order.
    assert names(production_repo.list()) == ['expression', 'term', 'expression']

    # get on an absent key returns None.
    assert production_repo.get('MISSING', 'core') is None

    # delete removes a present key and is idempotent for an absent key.
    production_repo.delete('term', 'core')
    assert production_repo.get('term', 'core') is None
    production_repo.delete('term', 'core')
    production_repo.delete('ABSENT', 'core')
    assert names(production_repo.list()) == ['expression', 'expression']


# ** test_int: production_repo_order_preservation_across_grammar_ids
def test_int_production_repo_order_preservation_across_grammar_ids(
    production_repo: ProductionConfigRepository,
) -> None:
    '''
    Declare productions spanning more than one grammar_id in deliberately
    non-alphabetical order; save, get, and assert retrieved order.
    '''

    # Declare in deliberately non-alphabetical order across grammar_ids.
    declared = [
        ComplexProductionRule(
            name='zeta',
            grammar_id='core',
            spec='zeta : ZETA',
            action='p[0] = p[1]',
        ),
        SimpleProductionRule(name='expression', grammar_id='core', spec='expression : term'),
        SimpleProductionRule(name='attr_decl', grammar_id='domain_extra', spec='attr_decl : COLON'),
        SimpleProductionRule(name='expression', grammar_id='domain_extra', spec='expression : attr_decl'),
    ]
    for rule in declared:
        production_repo.save(rule)

    # Retrieved order must match declared order exactly.
    loaded = production_repo.list()
    assert [(r.name, r.grammar_id) for r in loaded] == [
        (r.name, r.grammar_id) for r in declared
    ]


# ** test_int: production_repo_save_replaces_in_place
def test_int_production_repo_save_replaces_in_place(
    production_repo: ProductionConfigRepository,
) -> None:
    '''
    save() on an existing (name, grammar_id) replaces in the original
    list position without moving the entry to the end.
    '''

    # Declare three rules with distinct names so composite keys differ.
    first = SimpleProductionRule(name='A', grammar_id='core', spec='A : a')
    middle = SimpleProductionRule(name='B', grammar_id='core', spec='B : b')
    last = SimpleProductionRule(name='C', grammar_id='core', spec='C : c')
    production_repo.save(first)
    production_repo.save(middle)
    production_repo.save(last)

    # Update the middle rule's spec.
    updated = SimpleProductionRule(name='B', grammar_id='core', spec='B : B_UPDATED')
    production_repo.save(updated)

    # Position is unchanged and fields reflect the update.
    loaded = production_repo.list()
    assert names(loaded) == ['A', 'B', 'C']
    assert loaded[1].spec == 'B : B_UPDATED'


# ** test_int: production_repo_serialized_yaml_shape
def test_int_production_repo_serialized_yaml_shape(
    production_repo: ProductionConfigRepository,
) -> None:
    '''
    Assert the on-disk production_rules: YAML matches the
    sequence-of-single-key-mappings format exactly.
    '''

    # Save one complex and one simple rule under distinct composite keys.
    production_repo.save(ComplexProductionRule(
        name='expression',
        grammar_id='core',
        spec='expression : expression PLUS term',
        action='p[0] = p[1] + p[3]',
    ))
    production_repo.save(SimpleProductionRule(
        name='term',
        grammar_id='core',
        spec='term : NUMBER',
    ))

    # Load the raw YAML and assert the literal expected shape.
    raw = yaml.safe_load(Path(production_repo.config_file).read_text(encoding='utf-8'))
    assert raw == {
        'production_rules': [
            {
                'expression': {
                    'grammar_id': 'core',
                    'spec': 'expression : expression PLUS term',
                    'action': 'p[0] = p[1] + p[3]',
                },
            },
            {
                'term': {
                    'grammar_id': 'core',
                    'spec': 'term : NUMBER',
                },
            },
        ],
    }
