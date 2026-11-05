"""Tests for Tiferet-Ly Grammar Mappers"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.grammar import (
    GrammarAggregate,
    GrammarConfigObject,
)

# *** constants

# ** constant: sample_grammar
SAMPLE_GRAMMAR = GrammarAggregate(
    id='tiferet_module',
    parent_ids=['core', 'domain_extra'],
    start='module',
)

# *** tests

# ** test: grammar_aggregate_and_config_object_exist
def test_grammar_aggregate_and_config_object_exist() -> None:
    '''
    Test that GrammarAggregate and GrammarConfigObject exist.
    '''

    # Assert inherited mutators and roles are present.
    assert 'set_attribute' in dir(GrammarAggregate)
    assert 'set_start' in dir(GrammarAggregate)
    assert 'set_parent_ids' in dir(GrammarAggregate)
    assert 'set_ignore' in dir(GrammarAggregate)
    assert 'set_layout' in dir(GrammarAggregate)
    assert 'to_model' in GrammarConfigObject._ROLES
    assert 'to_data' in GrammarConfigObject._ROLES

# ** test: grammar_round_trip
def test_grammar_round_trip() -> None:
    '''
    Test round-tripping a GrammarAggregate through ConfigObject.
    '''

    # Serialize through to_data (id excluded) and re-inject id on read.
    data = GrammarConfigObject.from_model(SAMPLE_GRAMMAR).to_primitive('to_data')
    assert data == {
        'parent_ids': ['core', 'domain_extra'],
        'start': 'module',
    }
    assert 'id' not in data

    # Map back with id injected from the mapping key.
    restored = GrammarConfigObject.model_validate({
        **data,
        'id': 'tiferet_module',
    }).map()

    # Assert field equality.
    assert isinstance(restored, GrammarAggregate)
    assert restored.model_dump() == SAMPLE_GRAMMAR.model_dump()

# ** test: grammar_map_raises_same_domain_error_on_corrupted_invariant
def test_grammar_map_raises_same_domain_error_on_corrupted_invariant() -> None:
    '''
    Test that a corrupted grammar config raises the same domain-level
    ValidationError at .map() time that RFP-001 construction would raise.
    '''

    # Build a config object that bypasses required-field validation.
    corrupted = GrammarConfigObject.model_construct(
        id='core',
        parent_ids=[],
        start=None,
    )

    # Domain construction of the same invariant raises ValidationError.
    with pytest.raises(ValidationError) as domain_error:
        GrammarAggregate(id='core', parent_ids=[], start=None)

    # .map() must raise the same class of domain-level error.
    with pytest.raises(ValidationError) as map_error:
        corrupted.map()

    # Both failures are ValidationError (mapper adds no validation of its own).
    assert type(map_error.value) is type(domain_error.value)

# ** test: grammar_aggregate_mutations
def test_grammar_aggregate_mutations() -> None:
    '''
    Test start and parent_ids mutators on GrammarAggregate.
    '''

    # Mutate start and parent composition.
    grammar = GrammarAggregate(id='core', parent_ids=[], start='module')
    grammar.set_start('expression')
    grammar.set_parent_ids(['base', 'extra'])
    assert grammar.start == 'expression'
    assert grammar.parent_ids == ['base', 'extra']

# ** test: grammar_aggregate_set_ignore_stores_exact_string
@pytest.mark.parametrize('ignore', [' \t', '', '[ \t]', None])
def test_grammar_aggregate_set_ignore_stores_exact_string(ignore) -> None:
    '''
    Test that set_ignore stores the given skip characters exactly, or None,
    and leaves start, parent_ids, and layout unchanged.
    '''

    # Build a grammar that carries both facts, then set ignore.
    layout = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
    grammar = GrammarAggregate(
        id='core',
        parent_ids=['base'],
        start='module',
        ignore='#',
        layout=layout,
    )
    grammar.set_ignore(ignore)

    # Assert the exact value is stored and nothing else changed.
    if ignore is None:
        assert grammar.ignore is None
    else:
        assert grammar.ignore == ignore
        assert type(grammar.ignore) is str
    assert grammar.start == 'module'
    assert grammar.parent_ids == ['base']
    assert grammar.layout == layout

# ** test: grammar_aggregate_set_layout_replaces_or_clears
def test_grammar_aggregate_set_layout_replaces_or_clears() -> None:
    '''
    Test that set_layout replaces the whole profile, clears on None, and
    leaves start, parent_ids, and ignore unchanged.
    '''

    # Build a grammar with a first profile and replace it whole.
    first = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT', tab_size=2)
    second = LayoutProfile(indent_token='IN', dedent_token='OUT')
    grammar = GrammarAggregate(
        id='core',
        parent_ids=['base'],
        start='module',
        ignore=' \t',
        layout=first,
    )
    grammar.set_layout(second)

    # Assert the new profile replaced the old one whole.
    assert grammar.layout == second
    assert grammar.layout.tab_size == 4
    assert grammar.ignore == ' \t'
    assert grammar.start == 'module'
    assert grammar.parent_ids == ['base']

    # Clear the profile and assert the other facts are unchanged.
    grammar.set_layout(None)
    assert grammar.layout is None
    assert grammar.ignore == ' \t'

# ** test: grammar_aggregate_set_ignore_rejects_non_string
@pytest.mark.parametrize('ignore', [5, 1.5, True, [' ']])
def test_grammar_aggregate_set_ignore_rejects_non_string(ignore) -> None:
    '''
    Test that set_ignore rejects a non-string, non-None value and keeps the
    previous skip characters.
    '''

    # Attempt to assign a non-string value.
    grammar = GrammarAggregate(id='core', start='module', ignore=' ')
    with pytest.raises(ValidationError):
        grammar.set_ignore(ignore)

    # Assert the stored value is unchanged.
    assert grammar.ignore == ' '

# ** test: grammar_aggregate_set_layout_rejects_non_positive_tab_size
@pytest.mark.parametrize('tab_size', [0, -1, False])
def test_grammar_aggregate_set_layout_rejects_non_positive_tab_size(tab_size) -> None:
    '''
    Test that set_layout runs LayoutProfile's own tab_size validation.
    '''

    # Attempt to assign a profile whose tab_size the field rejects.
    grammar = GrammarAggregate(id='core', start='module')
    with pytest.raises(ValidationError):
        grammar.set_layout({
            'indent_token': 'INDENT',
            'dedent_token': 'DEDENT',
            'tab_size': tab_size,
        })

    # Assert no profile was stored.
    assert grammar.layout is None

# ** test: grammar_config_object_to_data_excludes_only_id
def test_grammar_config_object_to_data_excludes_only_id() -> None:
    '''
    Test that the to_data role still excludes only id, so present facts are
    written and absent facts are omitted.
    '''

    # Assert the role shape is unchanged.
    assert GrammarConfigObject._ROLES['to_data'] == {'exclude': {'id'}}

    # Serialize a grammar with an empty ignore string and a profile.
    grammar = GrammarAggregate(
        id='core',
        start='module',
        ignore='',
        layout=LayoutProfile(indent_token='INDENT', dedent_token='DEDENT'),
    )
    data = GrammarConfigObject.from_model(grammar).to_primitive('to_data')

    # Assert the empty string is present and the profile is its field mapping.
    assert data['ignore'] == ''
    assert data['layout']['indent_token'] == 'INDENT'
    assert data['layout']['tab_size'] == 4

