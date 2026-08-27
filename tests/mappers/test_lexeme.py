"""Tests for Tiferet-Ly Lexeme Mappers"""

# *** imports

# ** core
from types import SimpleNamespace

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate

# *** tests

# ** test: from_ply_token_copies_span_fields
def test_from_ply_token_copies_span_fields() -> None:
    '''
    Test that from_ply_token copies type, value, lineno, and lexpos.
    '''

    # Map a stand-in ply token through the single factory.
    tok = SimpleNamespace(type='PLUS', value='+', lineno=2, lexpos=4)
    lexeme = LexemeAggregate.from_ply_token(tok)

    # Assert the aggregate carries the four span fields.
    assert isinstance(lexeme, LexemeAggregate)
    assert lexeme.type == 'PLUS'
    assert lexeme.value == '+'
    assert lexeme.lineno == 2
    assert lexeme.lexpos == 4

# ** test: synthesize_constructs_without_a_ply_token
def test_synthesize_constructs_without_a_ply_token() -> None:
    '''
    Test that synthesize constructs a lexeme from a bare span, defaulting
    value to None, with no PLY token involved.
    '''

    # Synthesize an INDENT lexeme with no explicit value.
    lexeme = LexemeAggregate.synthesize('INDENT', lineno=3, lexpos=12)

    # Assert the span fields are set exactly and value defaults to None.
    assert isinstance(lexeme, LexemeAggregate)
    assert lexeme.type == 'INDENT'
    assert lexeme.value is None
    assert lexeme.lineno == 3
    assert lexeme.lexpos == 12

# ** test: synthesize_accepts_an_explicit_value
def test_synthesize_accepts_an_explicit_value() -> None:
    '''
    Test that synthesize carries an explicitly supplied value.
    '''

    # Synthesize a lexeme with an explicit value.
    lexeme = LexemeAggregate.synthesize('DEDENT', lineno=5, lexpos=20, value='dedent')

    # Assert the explicit value is preserved.
    assert lexeme.value == 'dedent'
