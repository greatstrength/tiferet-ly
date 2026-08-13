"""Tests for Tiferet-Ly Subgrammar Domain Model"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.subgrammar import Subgrammar

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
