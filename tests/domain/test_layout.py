"""Tests for Tiferet-Ly Layout Profile Domain Model"""

# *** imports

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet_ly.domain.layout import LayoutProfile

# *** tests

# ** test: layout_profile_requires_indent_and_dedent_tokens
def test_layout_profile_requires_indent_and_dedent_tokens() -> None:
    '''
    Test that constructing a LayoutProfile without indent_token or
    dedent_token raises ValidationError.
    '''

    # Missing indent_token raises ValidationError.
    with pytest.raises(ValidationError):
        LayoutProfile(dedent_token='DEDENT')

    # Missing dedent_token raises ValidationError.
    with pytest.raises(ValidationError):
        LayoutProfile(indent_token='INDENT')

# ** test: layout_profile_construct_minimal
def test_layout_profile_construct_minimal() -> None:
    '''
    Test constructing a LayoutProfile with only the required indent and
    dedent token names; every other field defaults.
    '''

    # Construct with only the two required fields.
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')

    # Assert the required fields and every default.
    assert profile.indent_token == 'INDENT'
    assert profile.dedent_token == 'DEDENT'
    assert profile.block_tokens == []
    assert profile.open_delimiters == []
    assert profile.close_delimiters == []
    assert profile.newline_token is None
    assert profile.suppress_newline_in_delimiters is True
    assert profile.tab_size == 4

# ** test: layout_profile_construct_full
def test_layout_profile_construct_full() -> None:
    '''
    Test constructing a LayoutProfile with every field declared explicitly.
    '''

    # Construct a profile with every field set.
    profile = LayoutProfile(
        block_tokens=['IF', 'FOR', 'DEF'],
        open_delimiters=['LPAREN'],
        close_delimiters=['RPAREN'],
        newline_token='NEWLINE',
        suppress_newline_in_delimiters=True,
        indent_token='INDENT',
        dedent_token='DEDENT',
        tab_size=4,
    )

    # Assert every declared field is set exactly.
    assert profile.block_tokens == ['IF', 'FOR', 'DEF']
    assert profile.open_delimiters == ['LPAREN']
    assert profile.close_delimiters == ['RPAREN']
    assert profile.newline_token == 'NEWLINE'
    assert profile.suppress_newline_in_delimiters is True
    assert profile.indent_token == 'INDENT'
    assert profile.dedent_token == 'DEDENT'
    assert profile.tab_size == 4

# ** test: layout_profile_forbids_extra_fields
def test_layout_profile_forbids_extra_fields() -> None:
    '''
    Test that an unknown field raises ValidationError, per DomainObject's extra='forbid' config.
    '''

    # An unrecognized field is rejected.
    with pytest.raises(ValidationError):
        LayoutProfile(indent_token='INDENT', dedent_token='DEDENT', unknown='value')
