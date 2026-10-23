"""Integration tests for Tiferet-Ly GrammarConfigRepository"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import pytest
import yaml

# ** app
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.repos.grammar import GrammarConfigRepository

# *** fixtures

# ** fixture: grammar_repo
@pytest.fixture
def grammar_repo(tmp_path: Path) -> GrammarConfigRepository:
    '''
    Build a GrammarConfigRepository against a real temporary YAML file.

    :param tmp_path: Pytest temporary directory.
    :type tmp_path: Path
    :return: The repository under test.
    :rtype: GrammarConfigRepository
    '''

    # Seed an empty YAML document so the loader can open the file.
    config_path = tmp_path / 'grammars.yml'
    config_path.write_text('{}\n', encoding='utf-8')

    # Return the repository pointed at the temp file.
    return GrammarConfigRepository(grammar_config=str(config_path))

# *** tests

# ** test_int: grammar_repo_crud_five_methods
def test_int_grammar_repo_crud_five_methods(grammar_repo: GrammarConfigRepository) -> None:
    '''
    Prove exists/get/list/save/delete against a real temporary YAML file.
    '''

    # Save three grammars, including a multi-parent composition.
    core = GrammarAggregate(id='core', parent_ids=[], start='module')
    domain_extra = GrammarAggregate(id='domain_extra', parent_ids=[], start='attr_decl')
    composed = GrammarAggregate(
        id='tiferet_module',
        parent_ids=['core', 'domain_extra'],
        start='module',
    )
    grammar_repo.save(core)
    grammar_repo.save(domain_extra)
    grammar_repo.save(composed)

    # exists/get succeed for present keys.
    assert grammar_repo.exists('core') is True
    assert grammar_repo.exists('tiferet_module') is True
    loaded = grammar_repo.get('tiferet_module')
    assert isinstance(loaded, GrammarAggregate)
    assert loaded.parent_ids == ['core', 'domain_extra']
    assert loaded.start == 'module'

    # list returns every entry.
    listed_ids = {grammar.id for grammar in grammar_repo.list()}
    assert listed_ids == {'core', 'domain_extra', 'tiferet_module'}

    # get on an absent key returns None.
    assert grammar_repo.get('missing') is None
    assert grammar_repo.exists('missing') is False

    # delete removes a present key and is idempotent for an absent key.
    grammar_repo.delete('domain_extra')
    assert grammar_repo.get('domain_extra') is None
    grammar_repo.delete('domain_extra')
    grammar_repo.delete('missing')
    assert {grammar.id for grammar in grammar_repo.list()} == {'core', 'tiferet_module'}


# ** test_int: grammar_repo_serialized_yaml_shape
def test_int_grammar_repo_serialized_yaml_shape(
    grammar_repo: GrammarConfigRepository,
) -> None:
    '''
    Assert the on-disk grammars: YAML is a flat id-keyed mapping with id
    excluded from the body.
    '''

    # Save a root and a composed grammar.
    grammar_repo.save(GrammarAggregate(id='core', parent_ids=[], start='module'))
    grammar_repo.save(GrammarAggregate(
        id='tiferet_module',
        parent_ids=['core', 'domain_extra'],
        start='module',
    ))

    # Load the raw YAML and assert the literal expected shape.
    raw = yaml.safe_load(Path(grammar_repo.config_file).read_text(encoding='utf-8'))
    assert raw == {
        'grammars': {
            'core': {
                'parent_ids': [],
                'start': 'module',
            },
            'tiferet_module': {
                'parent_ids': ['core', 'domain_extra'],
                'start': 'module',
            },
        },
    }


# ** test_int: grammar_repo_fact_round_trip
def test_int_grammar_repo_fact_round_trip(
    grammar_repo: GrammarConfigRepository,
) -> None:
    '''
    Assert present grammar facts are written to the body and reload equal,
    and a cleared fact is omitted from the body and reloads as None.
    '''

    # Save a grammar with skip characters and a layout profile.
    profile = LayoutProfile(
        block_tokens=['COLON'],
        indent_token='INDENT',
        dedent_token='DEDENT',
        tab_size=2,
    )
    grammar = GrammarAggregate(
        id='core',
        parent_ids=[],
        start='module',
        ignore=' \t',
        layout=profile,
    )
    grammar_repo.save(grammar)

    # Assert the saved body carries the exact string and the profile's fields.
    raw = yaml.safe_load(Path(grammar_repo.config_file).read_text(encoding='utf-8'))
    body = raw['grammars']['core']
    assert body['ignore'] == ' \t'
    assert body['layout'] == profile.model_dump(exclude_none=True)

    # Assert get returns the exact string and an equal profile.
    loaded = grammar_repo.get('core')
    assert loaded.ignore == ' \t'
    assert isinstance(loaded.layout, LayoutProfile)
    assert loaded.layout.model_dump() == profile.model_dump()

    # Clear both facts, save, and assert the body omits them.
    loaded.set_ignore(None)
    loaded.set_layout(None)
    grammar_repo.save(loaded)
    raw = yaml.safe_load(Path(grammar_repo.config_file).read_text(encoding='utf-8'))
    assert raw['grammars']['core'] == {
        'parent_ids': [],
        'start': 'module',
    }
    reloaded = grammar_repo.get('core')
    assert reloaded.ignore is None
    assert reloaded.layout is None

