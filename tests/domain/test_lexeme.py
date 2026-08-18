"""Tests for Tiferet-Ly Lexeme Domain Model"""

# *** imports

# ** app
from tiferet.domain.core import DomainObject
from tiferet_ly.domain.lexeme import Lexeme

# *** tests

# ** test: lexeme_has_exactly_four_fields
def test_lexeme_has_exactly_four_fields() -> None:
    '''
    Test that Lexeme is a DomainObject with exactly type, value, lineno, lexpos.
    '''

    # Construct a lexeme with the four span fields.
    lexeme = Lexeme(type='NUMBER', value=3, lineno=1, lexpos=0)

    # Assert the four fields and no extra domain fields.
    assert isinstance(lexeme, DomainObject)
    assert set(Lexeme.model_fields) == {'type', 'value', 'lineno', 'lexpos'}
    assert lexeme.type == 'NUMBER'
    assert lexeme.value == 3
    assert lexeme.lineno == 1
    assert lexeme.lexpos == 0
