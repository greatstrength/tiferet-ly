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
