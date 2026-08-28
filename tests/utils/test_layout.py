"""Tests for Tiferet-Ly Lexeme-Stream Layout Utility"""

# *** imports

# ** app
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils.layout import LayoutFilter

# *** functions

# ** function: python_like_profile
def python_like_profile(**overrides) -> LayoutProfile:
    '''
    Construct a LayoutProfile modeling a Python-like layout policy
    (IF/FOR/... as block tokens, parens as delimiters, NEWLINE suppressed
    inside them).

    :param overrides: Field overrides applied on top of the defaults.
    :type overrides: dict
    :return: The constructed layout profile.
    :rtype: LayoutProfile
    '''

    # Build the profile with block/delimiter/newline defaults, then apply overrides.
    defaults = dict(
        block_tokens=['IF'],
        open_delimiters=['LPAREN'],
        close_delimiters=['RPAREN'],
        newline_token='NEWLINE',
        suppress_newline_in_delimiters=True,
        indent_token='INDENT',
        dedent_token='DEDENT',
        tab_size=4,
    )
    defaults.update(overrides)
    return LayoutProfile(**defaults)

# *** tests

# ** test: apply_with_no_layout_features_is_identity
def test_apply_with_no_layout_features_is_identity() -> None:
    '''
    Test that applying a profile with no block tokens, delimiters, or
    newline token configured returns the input lexemes unchanged.
    '''

    # A profile with every feature left at its default (empty/None).
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
    lexemes = [
        LexemeAggregate(type='IDENTIFIER', value='x', lineno=1, lexpos=0),
        LexemeAggregate(type='IDENTIFIER', value='y', lineno=2, lexpos=2),
    ]

    # Assert the output is the same sequence, unmodified.
    result = LayoutFilter.apply(lexemes, profile, 'x\ny')
    assert result == lexemes

# ** test: apply_empty_stream_returns_empty
def test_apply_empty_stream_returns_empty() -> None:
    '''
    Test that applying a profile to an empty lexeme stream returns an
    empty list without raising.
    '''

    # An empty stream has nothing to inject and nothing to flush.
    result = LayoutFilter.apply([], python_like_profile(), '')
    assert result == []

# ** test: apply_injects_nested_indent_and_dedent
def test_apply_injects_nested_indent_and_dedent() -> None:
    '''
    Test a worked, nested-block example: two IF blocks nesting and then
    fully unwinding, asserting the injected INDENT/DEDENT positions.

    Source:
        if x:
            y
            if z:
                w
            v
        q
    '''

    # The exact source text driving column resolution via lexpos.
    text = 'if x:\n    y\n    if z:\n        w\n    v\nq'
    lexemes = [
        LexemeAggregate(type='IF', value='if', lineno=1, lexpos=0),
        LexemeAggregate(type='IDENTIFIER', value='x', lineno=1, lexpos=3),
        LexemeAggregate(type='COLON', value=':', lineno=1, lexpos=4),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=5),
        LexemeAggregate(type='IDENTIFIER', value='y', lineno=2, lexpos=10),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=2, lexpos=11),
        LexemeAggregate(type='IF', value='if', lineno=3, lexpos=16),
        LexemeAggregate(type='IDENTIFIER', value='z', lineno=3, lexpos=19),
        LexemeAggregate(type='COLON', value=':', lineno=3, lexpos=20),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=3, lexpos=21),
        LexemeAggregate(type='IDENTIFIER', value='w', lineno=4, lexpos=30),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=4, lexpos=31),
        LexemeAggregate(type='IDENTIFIER', value='v', lineno=5, lexpos=36),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=5, lexpos=37),
        LexemeAggregate(type='IDENTIFIER', value='q', lineno=6, lexpos=38),
    ]

    # Apply the layout filter and assert the exact resulting type sequence.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'NEWLINE',
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'NEWLINE',
        'DEDENT', 'IDENTIFIER', 'NEWLINE',
        'DEDENT', 'IDENTIFIER',
    ]

    # Spot-check the injected lexemes carry the upcoming lexeme's own span.
    injected = [lexeme for lexeme in result if lexeme.type in ('INDENT', 'DEDENT')]
    assert [(lexeme.type, lexeme.lineno, lexeme.lexpos) for lexeme in injected] == [
        ('INDENT', 2, 10),
        ('INDENT', 4, 30),
        ('DEDENT', 5, 36),
        ('DEDENT', 6, 38),
    ]

# ** test: apply_suppresses_newline_inside_open_delimiter
def test_apply_suppresses_newline_inside_open_delimiter() -> None:
    '''
    Test that a newline occurrence is dropped while delimiter depth is
    nonzero, and that no indent/dedent injection is attempted inside it.
    '''

    # f(\n1) — a NEWLINE appears while a paren is still open.
    text = 'f(\n1)'
    lexemes = [
        LexemeAggregate(type='IDENTIFIER', value='f', lineno=1, lexpos=0),
        LexemeAggregate(type='LPAREN', value='(', lineno=1, lexpos=1),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=2),
        LexemeAggregate(type='NUMBER', value=1, lineno=2, lexpos=3),
        LexemeAggregate(type='RPAREN', value=')', lineno=2, lexpos=4),
    ]

    # Apply the layout filter and assert the newline was dropped, nothing injected.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == ['IDENTIFIER', 'LPAREN', 'NUMBER', 'RPAREN']

# ** test: apply_flushes_trailing_dedents_at_end_of_stream
def test_apply_flushes_trailing_dedents_at_end_of_stream() -> None:
    '''
    Test that a stream ending while still indented flushes the remaining
    open indentation levels as trailing dedents.
    '''

    # if x:\n    y — the stream ends indented, with no further dedent trigger.
    text = 'if x:\n    y'
    lexemes = [
        LexemeAggregate(type='IF', value='if', lineno=1, lexpos=0),
        LexemeAggregate(type='IDENTIFIER', value='x', lineno=1, lexpos=3),
        LexemeAggregate(type='COLON', value=':', lineno=1, lexpos=4),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=5),
        LexemeAggregate(type='IDENTIFIER', value='y', lineno=2, lexpos=10),
    ]

    # Apply the layout filter and assert a trailing DEDENT was flushed.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE', 'INDENT', 'IDENTIFIER', 'DEDENT',
    ]

    # The flushed dedent is attributed to the last real lexeme's own span.
    assert result[-1].lineno == 2
    assert result[-1].lexpos == 10

# ** test: apply_indent_requires_a_pending_block_start
def test_apply_indent_requires_a_pending_block_start() -> None:
    '''
    Test that a column increase with no preceding block-introducing token
    does not inject an INDENT.
    '''

    # A deeper column with no IF/block token preceding it is just data.
    text = 'x\n    y'
    lexemes = [
        LexemeAggregate(type='IDENTIFIER', value='x', lineno=1, lexpos=0),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=1),
        LexemeAggregate(type='IDENTIFIER', value='y', lineno=2, lexpos=6),
    ]

    # No INDENT is injected without a pending block start.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == ['IDENTIFIER', 'NEWLINE', 'IDENTIFIER']
