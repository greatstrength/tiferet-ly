"""Tests for Tiferet-Ly Grammar Mappers"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
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
