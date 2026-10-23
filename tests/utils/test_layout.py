"""Tests for Tiferet-Ly Lexeme-Stream Layout Utility"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path
from typing import List, Protocol

# ** app
import tiferet_ly.utils as utils_package
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils.layout import LayoutFilter, LayoutProfileView, find_column

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

# ** function: if_block_lexemes
def if_block_lexemes(text: str, block_type: str = 'IF') -> List[LexemeAggregate]:
    '''
    Hand-lex a small if-block source into lexemes: the leading "if" keyword,
    identifiers, a colon, and newlines, skipping spaces and tabs.

    :param text: The source text to lex.
    :type text: str
    :param block_type: The type given to the leading "if" keyword.
    :type block_type: str
    :return: The lexemes, with lineno and lexpos taken from the text.
    :rtype: List[LexemeAggregate]
    '''

    # Walk the text one character at a time, tracking the line number.
    lexemes = []
    lineno = 1
    for lexpos, char in enumerate(text):

        # Spaces and tabs are ignored; they only shape the measured column.
        if char in ' \t':
            continue

        # A newline is its own lexeme and ends the current line.
        if char == '\n':
            lexemes.append(LexemeAggregate(type='NEWLINE', value=char, lineno=lineno, lexpos=lexpos))
            lineno += 1
            continue

        # The "if" keyword spans two characters; its second one is skipped.
        if text.startswith('if', lexpos) and (lexpos == 0 or text[lexpos - 1] == '\n'):
            lexemes.append(LexemeAggregate(type=block_type, value='if', lineno=lineno, lexpos=lexpos))
            continue
        if char == 'f' and lexpos > 0 and text[lexpos - 1] == 'i':
            continue

        # A colon or a one-letter identifier.
        lexeme_type = 'COLON' if char == ':' else 'IDENTIFIER'
        lexemes.append(LexemeAggregate(type=lexeme_type, value=char, lineno=lineno, lexpos=lexpos))

    # Return the hand-lexed stream.
    return lexemes

# ** function: layout_types
def layout_types(text: str, **overrides) -> List[str]:
    '''
    Apply the Python-like profile to a hand-lexed if-block source and
    return the resulting lexeme types.

    :param text: The source text to lex and filter.
    :type text: str
    :param overrides: Profile field overrides.
    :type overrides: dict
    :return: The filtered lexeme types, in order.
    :rtype: List[str]
    '''

    # Filter the hand-lexed stream and keep only the types.
    result = LayoutFilter.apply(if_block_lexemes(text), python_like_profile(**overrides), text)
    return [lexeme.type for lexeme in result]

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

# ** test: if_block_lexemes_matches_rfp_positions
def test_if_block_lexemes_matches_rfp_positions() -> None:
    '''
    Test that the hand lexer places identifiers at the lexpos values the
    acceptance criteria name, so the criteria tests measure the right spans.
    '''

    # Each criteria source, paired with the identifier positions it names after line 1.
    expected = {
        'if x:\n        y': [14],
        'if x:\n   y\n    z': [9, 15],
        'if x:\n        y\n   z': [14, 19],
        'if x:\n\ty': [7],
        'if x:\n   \t   y': [13],
    }

    # Assert the hand lexer reproduces every named position.
    for text, positions in expected.items():
        lexemes = if_block_lexemes(text)
        assert [lexeme.lexpos for lexeme in lexemes if lexeme.type == 'IDENTIFIER' and lexeme.lineno > 1] == positions

# ** test: apply_eight_columns_enters_two_levels
def test_apply_eight_columns_enters_two_levels() -> None:
    '''
    Test that an authorized rise of eight columns with width 4 injects two
    INDENT lexemes and flushes two DEDENT lexemes at end of stream.
    '''

    # if x:\n        y with the identifier at lexpos 14, column 8, level 2.
    text = 'if x:\n        y'
    result = LayoutFilter.apply(if_block_lexemes(text), python_like_profile(), text)

    # Two indents before the identifier, two dedents after the stream.
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'INDENT', 'IDENTIFIER',
        'DEDENT', 'DEDENT',
    ]

    # Both indents carry the identifier's span; both dedents the last real lexeme's.
    assert [(lexeme.lineno, lexeme.lexpos) for lexeme in result[4:6]] == [(2, 14), (2, 14)]
    assert [(lexeme.lineno, lexeme.lexpos) for lexeme in result[7:]] == [(2, 14), (2, 14)]

# ** test: apply_increase_within_a_level_spends_block_start
def test_apply_increase_within_a_level_spends_block_start() -> None:
    '''
    Test that an authorized increase that enters no level injects nothing
    and spends the pending block start, so a later deeper line does not indent.
    '''

    # Column 3 is level 0; column 4 on the next line is unannounced.
    assert layout_types('if x:\n   y\n    z') == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'IDENTIFIER', 'NEWLINE',
        'IDENTIFIER',
    ]

# ** test: apply_decrease_leaves_level_difference
def test_apply_decrease_leaves_level_difference() -> None:
    '''
    Test that a decrease from column 8 to column 3 injects one dedent per
    level left (two), not the column-delta count (one), and none at the end.
    '''

    # Column 8 is level 2; column 3 is level 0.
    text = 'if x:\n        y\n   z'
    result = LayoutFilter.apply(if_block_lexemes(text), python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'INDENT', 'IDENTIFIER', 'NEWLINE',
        'DEDENT', 'DEDENT', 'IDENTIFIER',
    ]

    # The dedents carry the column-3 identifier's own span.
    assert [(lexeme.lineno, lexeme.lexpos) for lexeme in result[8:10]] == [(3, 19), (3, 19)]

# ** test: apply_tab_counts_as_one_width
def test_apply_tab_counts_as_one_width() -> None:
    '''
    Test that a single leading tab measures as one declared width, opening
    one level and flushing one dedent.
    '''

    # if x:\n\ty puts the identifier at lexpos 7, column 4, level 1.
    assert layout_types('if x:\n\ty') == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'DEDENT',
    ]

# ** test: apply_mixed_tab_prefix_is_fixed_width
def test_apply_mixed_tab_prefix_is_fixed_width() -> None:
    '''
    Test that three spaces, a tab, and three spaces measure as 3 + 4 + 3
    columns (level 2), not a tab stop at column 7 (level 1).
    '''

    # Two levels entered, two levels flushed.
    assert layout_types('if x:\n   \t   y') == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'INDENT', 'IDENTIFIER',
        'DEDENT', 'DEDENT',
    ]

# ** test: apply_eight_columns_without_block_token_injects_nothing
def test_apply_eight_columns_without_block_token_injects_nothing() -> None:
    '''
    Test that the eight-column source with no block token in the stream
    injects no INDENT and no DEDENT.
    '''

    # The leading keyword is lexed as a plain identifier, not a block token.
    text = 'if x:\n        y'
    result = LayoutFilter.apply(if_block_lexemes(text, block_type='IDENTIFIER'), python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IDENTIFIER', 'IDENTIFIER', 'COLON', 'NEWLINE', 'IDENTIFIER',
    ]

# ** test: apply_unaligned_column_floors_to_level
def test_apply_unaligned_column_floors_to_level() -> None:
    '''
    Test that column 6 with width 4 is level 1: one indent, one dedent.
    '''

    # Six spaces enter one level, not one and a half.
    assert layout_types('if x:\n      y') == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'DEDENT',
    ]

# ** test: apply_decrease_within_a_level_injects_nothing
def test_apply_decrease_within_a_level_injects_nothing() -> None:
    '''
    Test that a decrease that crosses no level boundary injects no dedent,
    and the flush still closes the one open level.
    '''

    # Column 6 then column 5: both level 1.
    assert layout_types('if x:\n      y\n     z') == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'NEWLINE',
        'IDENTIFIER', 'DEDENT',
    ]

# ** test: apply_decrease_keeps_block_start_pending
def test_apply_decrease_keeps_block_start_pending() -> None:
    '''
    Test that a decrease adopts the new column but does not clear a pending
    block start, so the next deeper line still indents.
    '''

    # The inner "if" arms a block start; the next line dedents instead.
    text = 'if a:\n    if b:\nc\n    d'
    lexemes = [
        LexemeAggregate(type='IF', value='if', lineno=1, lexpos=0),
        LexemeAggregate(type='IDENTIFIER', value='a', lineno=1, lexpos=3),
        LexemeAggregate(type='COLON', value=':', lineno=1, lexpos=4),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=5),
        LexemeAggregate(type='IF', value='if', lineno=2, lexpos=10),
        LexemeAggregate(type='IDENTIFIER', value='b', lineno=2, lexpos=13),
        LexemeAggregate(type='COLON', value=':', lineno=2, lexpos=14),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=2, lexpos=15),
        LexemeAggregate(type='IDENTIFIER', value='c', lineno=3, lexpos=16),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=3, lexpos=17),
        LexemeAggregate(type='IDENTIFIER', value='d', lineno=4, lexpos=22),
    ]

    # The pending inner block start authorizes the column-4 line after the dedent.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'DEDENT', 'IDENTIFIER', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'DEDENT',
    ]

# ** test: apply_unannounced_increase_keeps_tracked_column
def test_apply_unannounced_increase_keeps_tracked_column() -> None:
    '''
    Test that an unannounced deeper column leaves the tracked column, so a
    later return to that column injects no dedent and the flush emits none.
    '''

    # Column 8 with no block token, then back to column 0.
    text = 'x\n        y\nz'
    lexemes = [
        LexemeAggregate(type='IDENTIFIER', value='x', lineno=1, lexpos=0),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=1),
        LexemeAggregate(type='IDENTIFIER', value='y', lineno=2, lexpos=10),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=2, lexpos=11),
        LexemeAggregate(type='IDENTIFIER', value='z', lineno=3, lexpos=12),
    ]

    # Nothing injected anywhere.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IDENTIFIER', 'NEWLINE', 'IDENTIFIER', 'NEWLINE', 'IDENTIFIER',
    ]

# ** test: apply_tab_size_one_counts_tab_as_one_column
def test_apply_tab_size_one_counts_tab_as_one_column() -> None:
    '''
    Test that with width 1 a tab is one column and one level.
    '''

    # One tab is column 1, level 1 at width 1.
    assert layout_types('if x:\n\ty', tab_size=1) == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'DEDENT',
    ]

# ** test: find_column_default_counts_tab_as_one
def test_find_column_default_counts_tab_as_one() -> None:
    '''
    Test that find_column without a tab size keeps the 1.0.0b3 measure: a
    tab is one column and the column is the character distance.
    '''

    # Distance from the previous newline, or the raw lexpos without one.
    assert find_column(0, 'abc') == 0
    assert find_column(2, 'abc') == 2
    assert find_column(7, 'if x:\n\ty') == 1
    assert find_column(14, 'if x:\n        y') == 8

# ** test: find_column_counts_tab_as_tab_size
def test_find_column_counts_tab_as_tab_size() -> None:
    '''
    Test that find_column with a tab size counts each tab in the measured
    span as that width and every other character, including a carriage
    return, as one.
    '''

    # A tab before the lexpos counts as the width.
    assert find_column(7, 'if x:\n\ty', tab_size=4) == 4
    assert find_column(13, 'if x:\n   \t   y', tab_size=4) == 10
    assert find_column(2, '\t\tx', tab_size=4) == 8

    # A tab that is itself at the lexpos does not count toward its own column.
    assert find_column(7, 'if x:\n\t\ty', tab_size=4) == 4
    assert find_column(6, 'if x:\n\ty', tab_size=4) == 0

    # A carriage return is one ordinary character; lexpos 0 stays column 0.
    assert find_column(8, 'if x:\r\n\ty', tab_size=4) == 4
    assert find_column(2, 'a\rb', tab_size=4) == 2
    assert find_column(0, '\tx', tab_size=4) == 0

# ** test: layout_module_does_not_import_domain
def test_layout_module_does_not_import_domain() -> None:
    '''
    Test that the layout utility module imports neither tiferet_ly.domain
    nor ..domain.
    '''

    # Parse the module source and collect every imported module path.
    source = Path(inspect.getfile(LayoutFilter)).read_text()
    imported = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            imported.append('.' * node.level + (node.module or ''))
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    # No absolute or relative domain import.
    domain_imports = [
        name for name in imported
        if name.lstrip('.') == 'domain'
        or name.lstrip('.').startswith('domain.')
        or name == 'tiferet_ly.domain'
        or name.startswith('tiferet_ly.domain.')
    ]
    assert imported
    assert domain_imports == []

# ** test: layout_profile_view_is_a_structural_protocol
def test_layout_profile_view_is_a_structural_protocol() -> None:
    '''
    Test that LayoutProfileView is a typing.Protocol naming exactly the
    fields the filter reads, unrelated to LayoutProfile by inheritance,
    not exported from the utils package, and the annotation on apply.
    '''

    # A Protocol, not a subclass of the domain object.
    assert Protocol in LayoutProfileView.__mro__
    assert getattr(LayoutProfileView, '_is_protocol', False) is True
    assert not issubclass(LayoutProfileView, LayoutProfile)
    assert LayoutProfile not in LayoutProfileView.__mro__

    # The protocol names exactly the eight profile attributes the filter reads.
    assert set(LayoutProfileView.__annotations__) == {
        'block_tokens',
        'open_delimiters',
        'close_delimiters',
        'newline_token',
        'suppress_newline_in_delimiters',
        'indent_token',
        'dedent_token',
        'tab_size',
    }

    # LayoutFilter.apply annotates its profile parameter with the protocol.
    assert inspect.signature(LayoutFilter.apply).parameters['profile'].annotation is LayoutProfileView

    # The protocol is not exported from the utils package.
    assert 'LayoutProfileView' not in utils_package.__all__

# ** test: parse_module_does_not_reference_layout_filter
def test_parse_module_does_not_reference_layout_filter() -> None:
    '''
    Test that parse-driven reading does not apply the layout filter.
    '''

    # The parse utility source never names LayoutFilter.
    parse_source = (Path(inspect.getfile(LayoutFilter)).parent / 'parse.py').read_text()
    assert 'LayoutFilter' not in parse_source

# ** test: apply_increase_within_a_level_adopts_column
def test_apply_increase_within_a_level_adopts_column() -> None:
    '''
    Test that an authorized increase that enters no level still adopts the
    new column, so a later shallower line is a decrease that keeps a newly
    pending block start, and the next deeper line indents.
    '''

    # Column 3 (level 0, adopted), then column 2, then column 4.
    text = 'if a:\n   if b:\n  c\n    d'
    lexemes = [
        LexemeAggregate(type='IF', value='if', lineno=1, lexpos=0),
        LexemeAggregate(type='IDENTIFIER', value='a', lineno=1, lexpos=3),
        LexemeAggregate(type='COLON', value=':', lineno=1, lexpos=4),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=1, lexpos=5),
        LexemeAggregate(type='IF', value='if', lineno=2, lexpos=9),
        LexemeAggregate(type='IDENTIFIER', value='b', lineno=2, lexpos=12),
        LexemeAggregate(type='COLON', value=':', lineno=2, lexpos=13),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=2, lexpos=14),
        LexemeAggregate(type='IDENTIFIER', value='c', lineno=3, lexpos=17),
        LexemeAggregate(type='NEWLINE', value='\n', lineno=3, lexpos=18),
        LexemeAggregate(type='IDENTIFIER', value='d', lineno=4, lexpos=23),
    ]

    # The column-2 line is a decrease, so the inner block start stays pending
    # and authorizes the column-4 line, which opens one level.
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'IDENTIFIER', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'DEDENT',
    ]
