"""Integration tests for Tiferet-Ly TokenConfigRepository"""

# *** imports

# ** core
from pathlib import Path
from typing import List

# ** infra
import pytest
import yaml

# ** app
from tiferet_ly.domain.token import (
    ComplexTokenRule,
    SimpleTokenRule,
)
from tiferet_ly.repos.token import TokenConfigRepository

# *** fixtures

# ** fixture: token_repo
@pytest.fixture
def token_repo(tmp_path: Path) -> TokenConfigRepository:
    '''
    Build a TokenConfigRepository against a real temporary YAML file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: The repository under test.
    :rtype: TokenConfigRepository
    '''

    # Seed an empty YAML document so the loader can open the file.
    config_path = tmp_path / 'tokens.yml'
    config_path.write_text('{}\n', encoding='utf-8')

    # Return the repository pointed at the temp file.
    return TokenConfigRepository(token_config=str(config_path))

# *** functions

# ** function: names
def names(rules: List) -> List[str]:
    '''
    Collect rule names in list order.

    :param rules: The token rules.
    :type rules: List
    :return: The rule names.
    :rtype: List[str]
    '''

    # Return names in declared order.
    return [rule.name for rule in rules]

# *** tests

# ** test_int: token_repo_crud_five_methods
def test_int_token_repo_crud_five_methods(token_repo: TokenConfigRepository) -> None:
    '''
    Prove exists/get/list/save/delete against a real temporary YAML file.
    '''

    # Save a simple and a complex rule under different grammar_ids.
    simple = SimpleTokenRule(name='PLUS', grammar_id='core', pattern=r'\+')
    complex_rule = ComplexTokenRule(
        name='NUMBER',
        grammar_id='core',
        pattern=r'\d+',
        action='t.value = int(t.value)\nreturn t',
    )
    other_plus = SimpleTokenRule(name='PLUS', grammar_id='domain_extra', pattern=r'\+\+')
    token_repo.save(simple)
    token_repo.save(complex_rule)
    token_repo.save(other_plus)

    # exists/get succeed for present keys.
    assert token_repo.exists('PLUS', 'core') is True
    assert token_repo.exists('PLUS', 'domain_extra') is True
    assert token_repo.exists('NUMBER', 'core') is True
    loaded = token_repo.get('PLUS', 'core')
    assert isinstance(loaded, SimpleTokenRule)
    assert loaded.pattern == r'\+'
    loaded_complex = token_repo.get('NUMBER', 'core')
    assert isinstance(loaded_complex, ComplexTokenRule)
    assert loaded_complex.action == 't.value = int(t.value)\nreturn t'

    # list returns every entry unfiltered in declared order.
    assert names(token_repo.list()) == ['PLUS', 'NUMBER', 'PLUS']

    # get on an absent key returns None.
    assert token_repo.get('MISSING', 'core') is None
    assert token_repo.exists('MISSING', 'core') is False

    # delete removes a present key and is idempotent for an absent key.
    token_repo.delete('NUMBER', 'core')
    assert token_repo.get('NUMBER', 'core') is None
    token_repo.delete('NUMBER', 'core')
    token_repo.delete('ABSENT', 'core')
    assert names(token_repo.list()) == ['PLUS', 'PLUS']


# ** test_int: token_repo_order_preservation_across_grammar_ids
def test_int_token_repo_order_preservation_across_grammar_ids(
    token_repo: TokenConfigRepository,
) -> None:
    '''
    Declare tokens spanning more than one grammar_id in deliberately
    non-alphabetical order; save, get, and assert retrieved order.
    '''

    # Declare in deliberately non-alphabetical order across grammar_ids.
    declared = [
        SimpleTokenRule(name='ZETA', grammar_id='core', pattern='z'),
        SimpleTokenRule(name='PLUS', grammar_id='core', pattern=r'\+'),
        ComplexTokenRule(
            name='NUMBER',
            grammar_id='core',
            pattern=r'\d+',
            action='t.value = int(t.value)\nreturn t',
        ),
        SimpleTokenRule(name='COLON', grammar_id='domain_extra', pattern=':'),
        SimpleTokenRule(name='PLUS', grammar_id='domain_extra', pattern=r'\+\+'),
    ]
    for rule in declared:
        token_repo.save(rule)

    # Retrieved order must match declared order exactly.
    loaded = token_repo.list()
    assert [(r.name, r.grammar_id) for r in loaded] == [
        (r.name, r.grammar_id) for r in declared
    ]


# ** test_int: token_repo_save_replaces_in_place
def test_int_token_repo_save_replaces_in_place(token_repo: TokenConfigRepository) -> None:
    '''
    save() on an existing (name, grammar_id) replaces in the original
    list position without moving the entry to the end.
    '''

    # Declare three rules.
    first = SimpleTokenRule(name='A', grammar_id='core', pattern='a')
    middle = SimpleTokenRule(name='B', grammar_id='core', pattern='b')
    last = SimpleTokenRule(name='C', grammar_id='core', pattern='c')
    token_repo.save(first)
    token_repo.save(middle)
    token_repo.save(last)

    # Update the middle rule's pattern.
    updated = SimpleTokenRule(name='B', grammar_id='core', pattern='B_UPDATED')
    token_repo.save(updated)

    # Position is unchanged and fields reflect the update.
    loaded = token_repo.list()
    assert names(loaded) == ['A', 'B', 'C']
    assert loaded[1].pattern == 'B_UPDATED'


# ** test_int: token_repo_serialized_yaml_shape
def test_int_token_repo_serialized_yaml_shape(token_repo: TokenConfigRepository) -> None:
    '''
    Assert the on-disk tokens: YAML matches the sequence-of-single-key-
    mappings format exactly.
    '''

    # Save one simple and one complex rule.
    token_repo.save(SimpleTokenRule(name='PLUS', grammar_id='core', pattern=r'\+'))
    token_repo.save(ComplexTokenRule(
        name='NUMBER',
        grammar_id='core',
        pattern=r'\d+',
        action='return t',
    ))

    # Load the raw YAML and assert the literal expected shape.
    raw = yaml.safe_load(Path(token_repo.config_file).read_text(encoding='utf-8'))
    assert raw == {
        'tokens': [
            {
                'PLUS': {
                    'grammar_id': 'core',
                    'pattern': r'\+',
                },
            },
            {
                'NUMBER': {
                    'grammar_id': 'core',
                    'pattern': r'\d+',
                    'action': 'return t',
                },
            },
        ],
    }
