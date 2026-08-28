"""Tests for Tiferet-Ly Lexeme Stream Utility"""

# *** imports

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils.stream import LexemeStream

# *** tests

# ** test: token_yields_each_lexemes_four_fields_in_order
def test_token_yields_each_lexemes_four_fields_in_order() -> None:
    '''
    Test that token() yields each lexeme's four span fields in order.
    '''

    # Construct the stream from a bare list, with no grammar or catalogue involved.
    lexemes = [
        LexemeAggregate.synthesize('NUMBER', lineno=1, lexpos=0, value=1),
        LexemeAggregate.synthesize('PLUS', lineno=1, lexpos=1, value='+'),
    ]
    stream = LexemeStream(lexemes)

    # Assert each call returns a carrier matching the source lexeme's fields.
    first = stream.token()
    assert first.type == 'NUMBER'
    assert first.value == 1
    assert first.lineno == 1
    assert first.lexpos == 0

    second = stream.token()
    assert second.type == 'PLUS'
    assert second.value == '+'
    assert second.lineno == 1
    assert second.lexpos == 1

# ** test: token_returns_none_at_exhaustion
def test_token_returns_none_at_exhaustion() -> None:
    '''
    Test that token() returns None once the stream is exhausted.
    '''

    # Construct a single-lexeme stream and exhaust it.
    stream = LexemeStream([
        LexemeAggregate.synthesize('NUMBER', lineno=1, lexpos=0, value=1),
    ])
    stream.token()

    # Assert exhaustion yields None, repeatably.
    assert stream.token() is None
    assert stream.token() is None

# ** test: token_returns_none_for_an_empty_stream
def test_token_returns_none_for_an_empty_stream() -> None:
    '''
    Test that an empty lexeme list yields None on the first call.
    '''

    # Construct an empty stream.
    stream = LexemeStream([])

    # Assert the very first call already reports exhaustion.
    assert stream.token() is None
