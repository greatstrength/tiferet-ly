"""Tiferet Ly Lexeme-Stream Layout Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** app
from tiferet_ly.domain.layout import LayoutProfile
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils import layout as layout_utils
from tiferet_ly.utils.layout import (
    LayoutFilter,
    find_column,
)

# *** functions

# ** function: python_like_profile
def python_like_profile(**overrides) -> LayoutProfile:
    '''
    Build a Python-like layout profile, with field overrides.

    :param overrides: Field values that replace the defaults.
    :type overrides: dict
    :return: The layout profile.
    :rtype: LayoutProfile
    '''

    # Start from the shared defaults, then apply overrides.
    defaults = {
        'block_tokens': ['IF'],
        'open_delimiters': ['LPAREN'],
        'close_delimiters': ['RPAREN'],
        'newline_token': 'NEWLINE',
        'suppress_newline_in_delimiters': True,
        'indent_token': 'INDENT',
        'dedent_token': 'DEDENT',
        'tab_size': 4,
    }
    defaults.update(overrides)
    return LayoutProfile(**defaults)

# ** function: stream
def _stream(*specs: tuple) -> list[LexemeAggregate]:
    '''
    Build recognized lexemes from (type, value, lineno, lexpos) tuples.

    :param specs: The lexeme fields, in LexemeAggregate.new order.
    :type specs: tuple
    :return: The recognized lexemes.
    :rtype: list[LexemeAggregate]
    '''

    # Every recognized input goes through new, with a string value.
    return [LexemeAggregate.new(lexeme_type, value, lineno, lexpos) for lexeme_type, value, lineno, lexpos in specs]

# ** function: imported_modules
def _imported_modules(tree: ast.AST) -> list[str]:
    '''
    Collect imported module names from a parsed module.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Imported module names.
    :rtype: list[str]
    '''

    # Walk import and import-from nodes only.
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules

# *** tests

# ** test: find_column
def test_find_column():
    '''
    Resolve 0-based columns from the last preceding newline only.
    '''

    # Position zero and a text without a newline count from the start.
    assert find_column(0, 'abc') == 0
    assert find_column(0, '') == 0
    assert find_column(2, 'abc') == 2

    # The newline at the position itself does not precede it.
    text = 'if x:\n    y'
    assert find_column(5, text) == 5
    assert find_column(10, text) == 4

    # Columns count from the last newline before the position.
    assert find_column(3, 'ab\ncd') == 0
    assert find_column(4, 'ab\ncd') == 1
    assert find_column(3, 'a\n\nb') == 0

# ** test: apply_with_no_layout_features_is_identity
def test_apply_with_no_layout_features_is_identity():
    '''
    Return a stream equal to the input when the profile declares no features.
    '''

    # Only the two required names are declared.
    profile = LayoutProfile(indent_token='INDENT', dedent_token='DEDENT')
    lexemes = [
        LexemeAggregate.new('IDENTIFIER', 'x', 1, 0),
        LexemeAggregate.new('IDENTIFIER', 'y', 2, 2),
    ]
    assert LayoutFilter.apply(lexemes, profile, 'x\ny') == lexemes

# ** test: apply_empty_stream_returns_empty
def test_apply_empty_stream_returns_empty():
    '''
    Return an empty stream for an empty input without raising.
    '''

    # No lexemes, no injected lexemes.
    assert LayoutFilter.apply([], python_like_profile(), '') == []

# ** test: apply_injects_nested_indent_and_dedent
def test_apply_injects_nested_indent_and_dedent():
    '''
    Inject one indent per pending block and one dedent per exited level.
    '''

    # Two nested blocks, then a return to each outer level.
    text = 'if x:\n    y\n    if z:\n        w\n    v\nq'
    lexemes = _stream(
        ('IF', 'if', 1, 0),
        ('IDENTIFIER', 'x', 1, 3),
        ('COLON', ':', 1, 4),
        ('NEWLINE', '\n', 1, 5),
        ('IDENTIFIER', 'y', 2, 10),
        ('NEWLINE', '\n', 2, 11),
        ('IF', 'if', 3, 16),
        ('IDENTIFIER', 'z', 3, 19),
        ('COLON', ':', 3, 20),
        ('NEWLINE', '\n', 3, 21),
        ('IDENTIFIER', 'w', 4, 30),
        ('NEWLINE', '\n', 4, 31),
        ('IDENTIFIER', 'v', 5, 36),
        ('NEWLINE', '\n', 5, 37),
        ('IDENTIFIER', 'q', 6, 38),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), text)

    # The type sequence carries the injected lexemes in place.
    assert [lexeme.type for lexeme in result] == [
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'NEWLINE',
        'IF', 'IDENTIFIER', 'COLON', 'NEWLINE',
        'INDENT', 'IDENTIFIER', 'NEWLINE',
        'DEDENT', 'IDENTIFIER', 'NEWLINE',
        'DEDENT', 'IDENTIFIER',
    ]

    # Injected lexemes carry the upcoming lexeme's span and no value.
    injected = [lexeme for lexeme in result if lexeme.type in ('INDENT', 'DEDENT')]
    assert [(lexeme.type, lexeme.lineno, lexeme.lexpos) for lexeme in injected] == [
        ('INDENT', 2, 10),
        ('INDENT', 4, 30),
        ('DEDENT', 5, 36),
        ('DEDENT', 6, 38),
    ]
    for lexeme in injected:
        assert lexeme.value is None

    # Recognized lexemes are passed through as the same objects, and the input is not mutated.
    assert [lexeme for lexeme in result if lexeme.type not in ('INDENT', 'DEDENT')] == lexemes
    assert len(lexemes) == 15

# ** test: apply_suppresses_newline_inside_open_delimiter
def test_apply_suppresses_newline_inside_open_delimiter():
    '''
    Drop a newline while a delimiter is open, with no layout lexemes.
    '''

    # The newline sits between the open and the close.
    lexemes = _stream(
        ('IDENTIFIER', 'f', 1, 0),
        ('LPAREN', '(', 1, 1),
        ('NEWLINE', '\n', 1, 2),
        ('NUMBER', '1', 2, 3),
        ('RPAREN', ')', 2, 4),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), 'f(\n1)')
    assert [lexeme.type for lexeme in result] == [
        'IDENTIFIER',
        'LPAREN',
        'NUMBER',
        'RPAREN',
    ]

# ** test: apply_keeps_newline_after_delimiter_closes
def test_apply_keeps_newline_after_delimiter_closes():
    '''
    Keep a newline once the matching close has lowered the depth to zero.
    '''

    # The inner newline is dropped; the one after the close remains.
    lexemes = _stream(
        ('IDENTIFIER', 'f', 1, 0),
        ('LPAREN', '(', 1, 1),
        ('NEWLINE', '\n', 1, 2),
        ('NUMBER', '1', 2, 3),
        ('RPAREN', ')', 2, 4),
        ('NEWLINE', '\n', 2, 5),
        ('NUMBER', '2', 3, 6),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), 'f(\n1)\n2')
    assert [lexeme.type for lexeme in result] == [
        'IDENTIFIER',
        'LPAREN',
        'NUMBER',
        'RPAREN',
        'NEWLINE',
        'NUMBER',
    ]

# ** test: apply_flushes_trailing_dedents_at_end_of_stream
def test_apply_flushes_trailing_dedents_at_end_of_stream():
    '''
    Close indentation still open at the end with dedents on the last lexeme's span.
    '''

    # The stream ends inside the block.
    lexemes = _stream(
        ('IF', 'if', 1, 0),
        ('IDENTIFIER', 'x', 1, 3),
        ('COLON', ':', 1, 4),
        ('NEWLINE', '\n', 1, 5),
        ('IDENTIFIER', 'y', 2, 10),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), 'if x:\n    y')
    assert [lexeme.type for lexeme in result] == [
        'IF',
        'IDENTIFIER',
        'COLON',
        'NEWLINE',
        'INDENT',
        'IDENTIFIER',
        'DEDENT',
    ]

    # The flushed dedent takes the last input lexeme's span. No newline is synthesized.
    last = result[-1]
    assert last.type == 'DEDENT'
    assert last.lineno == 2
    assert last.lexpos == 10
    assert last.value is None

# ** test: apply_counts_levels_by_tab_size
def test_apply_counts_levels_by_tab_size():
    '''
    Inject one indent for a two-level rise and two dedents for the drop.
    '''

    # Eight spaces before y, then back to column 0.
    lexemes = _stream(
        ('IF', 'if', 1, 0),
        ('IDENTIFIER', 'x', 1, 3),
        ('COLON', ':', 1, 4),
        ('NEWLINE', '\n', 1, 5),
        ('IDENTIFIER', 'y', 2, 14),
        ('NEWLINE', '\n', 2, 15),
        ('IDENTIFIER', 'z', 3, 16),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), 'if x:\n        y\nz')
    assert [lexeme.type for lexeme in result] == [
        'IF',
        'IDENTIFIER',
        'COLON',
        'NEWLINE',
        'INDENT',
        'IDENTIFIER',
        'NEWLINE',
        'DEDENT',
        'DEDENT',
        'IDENTIFIER',
    ]

    # Exactly one indent, on the upcoming lexeme's span.
    indents = [lexeme for lexeme in result if lexeme.type == 'INDENT']
    assert len(indents) == 1
    assert (indents[0].lineno, indents[0].lexpos) == (2, 14)

    # Both dedents sit on z's span with no value.
    dedents = [lexeme for lexeme in result if lexeme.type == 'DEDENT']
    assert len(dedents) == 2
    for lexeme in dedents:
        assert (lexeme.lineno, lexeme.lexpos) == (3, 16)
        assert lexeme.value is None

# ** test: apply_indent_requires_a_pending_block_start
def test_apply_indent_requires_a_pending_block_start():
    '''
    Inject no indent, and no trailing dedent, without a pending block start.
    '''

    # The column rises with no block token before it.
    lexemes = _stream(
        ('IDENTIFIER', 'x', 1, 0),
        ('NEWLINE', '\n', 1, 1),
        ('IDENTIFIER', 'y', 2, 6),
    )
    result = LayoutFilter.apply(lexemes, python_like_profile(), 'x\n    y')
    assert [lexeme.type for lexeme in result] == [
        'IDENTIFIER',
        'NEWLINE',
        'IDENTIFIER',
    ]

# ** test: module_does_not_import_ply
def test_module_does_not_import_ply():
    '''
    Import no PLY, domain, or event module from the layout utility.
    '''

    # Read the utility's own import statements.
    tree = ast.parse(Path(layout_utils.__file__).read_text())
    for module in _imported_modules(tree):
        assert module != 'ply' and not module.startswith('ply.')
        assert module != 'tiferet_ly.domain' and not module.startswith('tiferet_ly.domain.')
        assert module != 'tiferet_ly.events' and not module.startswith('tiferet_ly.events.')
