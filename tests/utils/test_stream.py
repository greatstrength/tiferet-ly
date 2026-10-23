"""Tiferet Ly Lexeme Stream Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils.stream import LexemeStream, LexemeToken

# *** functions

# ** function: imported_modules
def _imported_modules(path: Path) -> list[str]:
    '''
    Collect imported module names from one source file.

    :param path: The source file to parse.
    :type path: Path
    :return: Imported module names; a relative import without a module is ''.
    :rtype: list[str]
    '''

    # Walk import and import-from nodes only.
    modules = []
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or '')
    return modules

# *** tests

# ** test: token_yields_each_lexemes_four_fields_in_order
def test_token_yields_each_lexemes_four_fields_in_order():
    '''
    Return one new carrier per lexeme, in call order, copying the four fields.
    '''

    # Build two recognized lexemes and wrap them.
    lexemes = [
        LexemeAggregate.new('NUMBER', '1', 1, 0),
        LexemeAggregate.new('PLUS', '+', 1, 1),
    ]
    stream = LexemeStream(lexemes)

    # The first call carries the first lexeme's fields.
    first = stream.token()
    assert type(first) is LexemeToken
    assert first is not lexemes[0]
    assert first.type == 'NUMBER'
    assert first.value is lexemes[0].value
    assert first.value == '1'
    assert first.lineno == 1
    assert first.lexpos == 0

    # The second call carries the second lexeme's fields.
    second = stream.token()
    assert type(second) is LexemeToken
    assert second is not lexemes[1]
    assert second.type == 'PLUS'
    assert second.value is lexemes[1].value
    assert second.value == '+'
    assert second.lineno == 1
    assert second.lexpos == 1

# ** test: token_returns_none_at_exhaustion
def test_token_returns_none_at_exhaustion():
    '''
    Return None, without raising, on every call after the last lexeme.
    '''

    # Consume the only lexeme.
    stream = LexemeStream([LexemeAggregate.new('NUMBER', '1', 1, 0)])
    stream.token()

    # The next two calls are None.
    assert stream.token() is None
    assert stream.token() is None

# ** test: token_returns_none_for_an_empty_stream
def test_token_returns_none_for_an_empty_stream():
    '''
    Return None on the first call for an empty list, with no lexer methods.
    '''

    # An empty list yields no carrier.
    assert LexemeStream([]).token() is None

    # The adapter has no input or lex method.
    assert not hasattr(LexemeStream, 'input')
    assert not hasattr(LexemeStream, 'lex')

# ** test: does_not_import_ply
def test_does_not_import_ply():
    '''
    Import no PLY or event module from the stream utility or this test module.
    '''

    # Resolve both files from the repository root.
    root = Path(__file__).parents[2]
    stream_modules = _imported_modules(root / 'tiferet_ly' / 'utils' / 'stream.py')
    test_modules = _imported_modules(root / 'tests' / 'utils' / 'test_stream.py')

    # The stream utility imports no PLY, event, or domain module.
    for module in stream_modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert module != 'tiferet_ly.events' and not module.startswith('tiferet_ly.events.')
        assert module != 'tiferet_ly.domain' and not module.startswith('tiferet_ly.domain.')

    # This test module imports no PLY or event module.
    for module in test_modules:
        assert module != 'ply' and not module.startswith('ply.')
        assert module != 'tiferet_ly.events' and not module.startswith('tiferet_ly.events.')
