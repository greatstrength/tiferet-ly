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

# ** test: layout_profile_rejects_non_positive_tab_size
@pytest.mark.parametrize('tab_size', [0, -1, False])
def test_layout_profile_rejects_non_positive_tab_size(tab_size) -> None:
    '''
    Test that a tab_size the field stores as an integer less than 1 raises
    ValidationError at construction.

    :param tab_size: The declared width under test.
    :type tab_size: int | bool
    '''

    # A width of zero, a negative width, and False (stored as 0) are refused.
    with pytest.raises(ValidationError):
        LayoutProfile(indent_token='INDENT', dedent_token='DEDENT', tab_size=tab_size)

# ** test: layout_profile_accepts_positive_tab_size
@pytest.mark.parametrize('tab_size, stored', [
    (1, 1),
    (True, 1),
    (4.0, 4),
    ('4', 4),
])
def test_layout_profile_accepts_positive_tab_size(tab_size, stored) -> None:
    '''
    Test that a tab_size the field already coerces to a positive integer
    still constructs and stores that integer.

    :param tab_size: The declared width under test.
    :type tab_size: int | bool | float | str
    :param stored: The integer the profile is expected to store.
    :type stored: int
    '''

    # Existing int coercion is unchanged for positive values.
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT', tab_size=tab_size)
    assert profile.tab_size == stored
    assert type(profile.tab_size) is int

# ** test: layout_profile_rejects_non_positive_tab_size_assignment
def test_layout_profile_rejects_non_positive_tab_size_assignment() -> None:
    '''
    Test that assigning a zero tab_size to an existing profile raises
    ValidationError and leaves the stored width unchanged.
    '''

    # Construct with the default width of 4.
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
    assert profile.tab_size == 4

    # Assignment re-validates and refuses zero.
    with pytest.raises(ValidationError):
        profile.tab_size = 0
    assert profile.tab_size == 4
