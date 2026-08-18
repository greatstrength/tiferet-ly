"""Tests for Tiferet-Ly PLY Lexer and Parser Utilities"""

# *** imports

# ** core
from pathlib import Path

# ** infra
import pytest
import yaml

# ** app
from tiferet import App
from tiferet.interfaces.core import ServiceError
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.utils.reader import (
    ACTION_EXECUTION_FAILED_ID,
    GRAMMAR_NOT_FOUND_ID,
    LEX_ERROR_ID,
    PARSE_ERROR_ID,
    PlyLexer,
    PlyParser,
    READER_BUILD_FAILED_ID,
    unique_production_attr,
)

# *** functions

# ** function: grammar
def grammar(id: str = 'arith', start: str = 'expr', parent_ids=None) -> GrammarAggregate:
    '''
    Construct a GrammarAggregate for reader tests.

    :param id: The grammar id.
    :type id: str
    :param start: The start symbol.
    :type start: str
    :param parent_ids: Optional parent ids.
    :type parent_ids: list | None
    :return: The constructed grammar.
    :rtype: GrammarAggregate
    '''

    # Construct a lean grammar.
    return GrammarAggregate(id=id, parent_ids=list(parent_ids or []), start=start)


# ** function: number_token
def number_token(grammar_id: str = 'arith') -> ComplexTokenRuleAggregate:
    '''
    Construct the NUMBER token used by the arithmetic grammar.

    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The NUMBER token.
    :rtype: ComplexTokenRuleAggregate
    '''

    # NUMBER converts the matched digits to an int.
    return ComplexTokenRuleAggregate(
        name='NUMBER',
        grammar_id=grammar_id,
        pattern=r'\d+',
        action='t.value = int(t.value)\nreturn t',
    )


# ** function: plus_token
def plus_token(grammar_id: str = 'arith') -> SimpleTokenRuleAggregate:
    '''
    Construct the PLUS token.

    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The PLUS token.
    :rtype: SimpleTokenRuleAggregate
    '''

    # PLUS is a bare plus sign.
    return SimpleTokenRuleAggregate(
        name='PLUS',
        grammar_id=grammar_id,
        pattern=r'\+',
    )


# ** function: ignore_token
def ignore_token(grammar_id: str = 'arith') -> ComplexTokenRuleAggregate:
    '''
    Construct a token that discards whitespace.

    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The ignore token.
    :rtype: ComplexTokenRuleAggregate
    '''

    # Returning None tells ply to drop the match.
    return ComplexTokenRuleAggregate(
        name='WS',
        grammar_id=grammar_id,
        pattern=r'\s+',
        action='return None',
    )


# ** function: arith_productions
def arith_productions(grammar_id: str = 'arith') -> list:
    '''
    Construct additive productions for the arithmetic grammar.

    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The production list.
    :rtype: list
    '''

    # Two alternatives of expr plus a number pass-through.
    return [
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id=grammar_id,
            spec='expr : expr PLUS term',
            action='p[0] = p[1] + p[3]',
        ),
        SimpleProductionRuleAggregate(
            name='expr',
            grammar_id=grammar_id,
            spec='expr : term',
        ),
        SimpleProductionRuleAggregate(
            name='term',
            grammar_id=grammar_id,
            spec='term : NUMBER',
        ),
    ]


# *** tests

# ** test: unique_production_attr_suffixes_repeats
def test_unique_production_attr_suffixes_repeats() -> None:
    '''
    Test that same-name productions become p_name, p_name_2, ...
    '''

    # Allocate two attribute names for the same production.
    used = {}
    first = unique_production_attr('expr', used)
    second = unique_production_attr('expr', used)

    # Assert the first keeps the bare name and the second is suffixed.
    assert first == 'p_expr'
    assert second == 'p_expr_2'


# ** test: tokenize_returns_lexeme_aggregates
def test_tokenize_returns_lexeme_aggregates() -> None:
    '''
    Test that tokenize returns LexemeAggregates with span fields.
    '''

    # Tokenize a single number.
    result = PlyLexer().tokenize(
        'arith',
        [grammar()],
        [number_token()],
        '42',
    )

    # Assert a single NUMBER lexeme with lineno and lexpos.
    assert len(result) == 1
    assert isinstance(result[0], LexemeAggregate)
    assert result[0].type == 'NUMBER'
    assert result[0].value == 42
    assert result[0].lineno == 1
    assert result[0].lexpos == 0


# ** test: tokenize_honors_whitespace_override
def test_tokenize_honors_whitespace_override() -> None:
    '''
    Test that tokenize matches the selected WHITESPACE, not a dropped ancestor.
    '''

    # Dialect WHITESPACE swallows comments; the base one does not.
    arith = grammar('arith')
    comments = grammar('comments', start='expr', parent_ids=['arith'])
    tokens = [
        number_token('arith'),
        ComplexTokenRuleAggregate(
            name='WS',
            grammar_id='arith',
            pattern=r'\s+',
            action='return None',
        ),
        ComplexTokenRuleAggregate(
            name='WS',
            grammar_id='comments',
            pattern=r'(\s+|#.*)',
            action='return None',
        ),
    ]

    # Tokenize text that only the dialect ignore pattern can consume.
    result = PlyLexer().tokenize(
        'comments',
        [arith, comments],
        tokens,
        '1 # comment\n2',
    )

    # Assert both numbers are recognized and the comment is dropped.
    assert [lexeme.value for lexeme in result] == [1, 2]


# ** test: tokenize_unknown_grammar_does_not_call_lex
def test_tokenize_unknown_grammar_does_not_call_lex(monkeypatch) -> None:
    '''
    Test that an unknown grammar_id raises before lex.lex.
    '''

    # Patch lex.lex so a successful path would be visible.
    called = {'lex': False}

    def fail_if_called(*_args, **_kwargs):
        called['lex'] = True
        raise AssertionError('lex.lex should not be called')

    monkeypatch.setattr('tiferet_ly.utils.reader.lex.lex', fail_if_called)

    # Tokenize against an empty grammar catalogue.
    with pytest.raises(ServiceError) as raised:
        PlyLexer().tokenize('missing', [], [number_token()], '1')

    # Assert GRAMMAR_NOT_FOUND and that ply was not invoked.
    assert raised.value.error_code == GRAMMAR_NOT_FOUND_ID
    assert called['lex'] is False


# ** test: tokenize_illegal_character_raises_lex_error
def test_tokenize_illegal_character_raises_lex_error() -> None:
    '''
    Test that an unrecognized character raises LEX_ERROR_ID with span keys.
    '''

    # Tokenize a character the NUMBER rule cannot match.
    with pytest.raises(ServiceError) as raised:
        PlyLexer().tokenize('arith', [grammar()], [number_token()], 'x')

    # Assert the structured lex error names the span.
    assert raised.value.error_code == LEX_ERROR_ID
    assert raised.value.kwargs['grammar_id'] == 'arith'
    assert raised.value.kwargs['value'] == 'x'
    assert raised.value.kwargs['lineno'] == 1
    assert 'lexpos' in raised.value.kwargs


# ** test: parse_two_alternatives
def test_parse_two_alternatives() -> None:
    '''
    Test that both same-name production alternatives are installed.
    '''

    # Parse an addition that needs both expr alternatives.
    result = PlyParser().parse(
        'arith',
        [grammar()],
        [number_token(), plus_token(), ignore_token()],
        arith_productions(),
        '1+2',
    )

    # Assert the start action produced the sum.
    assert result == 3


# ** test: parse_preserves_token_order
def test_parse_preserves_token_order() -> None:
    '''
    Test that derive_tokens order is the selected-token order.
    '''

    # A later simple token must not sort ahead of an earlier complex one.
    tokens = [
        ComplexTokenRuleAggregate(
            name='ID',
            grammar_id='arith',
            pattern=r'[A-Za-z]+',
            action='return t',
        ),
        SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='arith',
            pattern=r'\+',
        ),
    ]
    productions = [
        ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='arith',
            spec='expr : ID PLUS ID',
            action='p[0] = (p[1], p[3])',
        ),
    ]

    # Parse text that only this declared order can accept as ID + ID.
    result = PlyParser().parse(
        'arith',
        [grammar()],
        tokens,
        productions,
        'a+b',
    )

    # Assert both identifiers were recognized in source order.
    assert result == ('a', 'b')


# ** test: parse_does_not_write_tables
def test_parse_does_not_write_tables(tmp_path, monkeypatch) -> None:
    '''
    Test that yacc is invoked with write_tables=False and writes no tables.
    '''

    # Run parse from an empty working directory.
    monkeypatch.chdir(tmp_path)
    PlyParser().parse(
        'arith',
        [grammar()],
        [number_token(), plus_token(), ignore_token()],
        arith_productions(),
        '1+2',
    )

    # Assert no parsetab or lextab leaked into the working tree.
    names = {path.name for path in tmp_path.iterdir()}
    assert 'parsetab.py' not in names
    assert 'lextab.py' not in names


# ** test: parse_unknown_grammar_does_not_call_yacc
def test_parse_unknown_grammar_does_not_call_yacc(monkeypatch) -> None:
    '''
    Test that an unknown grammar_id raises before yacc.yacc.
    '''

    # Patch yacc.yacc so a successful path would be visible.
    called = {'yacc': False}

    def fail_if_called(*_args, **_kwargs):
        called['yacc'] = True
        raise AssertionError('yacc.yacc should not be called')

    monkeypatch.setattr('tiferet_ly.utils.reader.yacc.yacc', fail_if_called)

    # Parse against an empty grammar catalogue.
    with pytest.raises(ServiceError) as raised:
        PlyParser().parse(
            'missing',
            [],
            [number_token()],
            arith_productions(),
            '1',
        )

    # Assert GRAMMAR_NOT_FOUND and that ply was not invoked.
    assert raised.value.error_code == GRAMMAR_NOT_FOUND_ID
    assert called['yacc'] is False


# ** test: parse_syntax_error_raises
def test_parse_syntax_error_raises() -> None:
    '''
    Test that a syntax error raises PARSE_ERROR_ID with Lexeme span keys.
    '''

    # Parse a plus with no following term.
    with pytest.raises(ServiceError) as raised:
        PlyParser().parse(
            'arith',
            [grammar()],
            [number_token(), plus_token(), ignore_token()],
            arith_productions(),
            '1+',
        )

    # Assert the structured parse error names the grammar.
    assert raised.value.error_code == PARSE_ERROR_ID
    assert raised.value.kwargs['grammar_id'] == 'arith'


# ** test: parse_build_failure_raises
def test_parse_build_failure_raises() -> None:
    '''
    Test that a ply build failure raises READER_BUILD_FAILED_ID.
    '''

    # Reference a token the catalogue does not declare.
    productions = [
        SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arith',
            spec='expr : MISSING',
        ),
    ]

    # Parse with an empty token list so yacc cannot build.
    with pytest.raises(ServiceError) as raised:
        PlyParser().parse(
            'arith',
            [grammar()],
            [],
            productions,
            '1',
        )

    # Assert the structured build failure names the grammar.
    assert raised.value.error_code == READER_BUILD_FAILED_ID
    assert raised.value.kwargs['grammar_id'] == 'arith'


# ** test: tokenize_action_failure_raises
def test_tokenize_action_failure_raises() -> None:
    '''
    Test that a compiled token action exception is ACTION_EXECUTION_FAILED_ID.
    '''

    # NUMBER action raises at runtime.
    tokens = [
        ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='arith',
            pattern=r'\d+',
            action='raise ValueError("boom")',
        ),
    ]

    # Tokenize text that matches the exploding action.
    with pytest.raises(ServiceError) as raised:
        PlyLexer().tokenize('arith', [grammar()], tokens, '1')

    # Assert the structured action-execution failure.
    assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
    assert raised.value.kwargs['grammar_id'] == 'arith'


# ** test: ply_import_is_isolated
def test_ply_import_is_isolated() -> None:
    '''
    Test that only the reader util module imports ply.
    '''

    # Import the thin events and confirm they do not pull ply into their module.
    import tiferet_ly.events.lex as lex_events
    import tiferet_ly.events.parse as parse_events

    # Assert ply is absent from the event modules.
    assert 'ply' not in lex_events.__dict__
    assert 'ply' not in parse_events.__dict__


# ** test: features_lex_and_parse_arithmetic
def test_features_lex_and_parse_arithmetic(tmp_path, monkeypatch) -> None:
    '''
    Test that App().run executes lex and parse against a tmp_path catalogue.
    '''

    # Write the arithmetic catalogues and a session whose DI points at them.
    tokens_path = tmp_path / 'tokens.yml'
    productions_path = tmp_path / 'productions.yml'
    grammars_path = tmp_path / 'grammars.yml'
    tokens_path.write_text(
        yaml.safe_dump({
            'tokens': [
                {'NUMBER': {
                    'grammar_id': 'arith',
                    'pattern': r'\d+',
                    'action': 't.value = int(t.value)\nreturn t',
                }},
                {'PLUS': {
                    'grammar_id': 'arith',
                    'pattern': r'\+',
                }},
                {'WS': {
                    'grammar_id': 'arith',
                    'pattern': r'\s+',
                    'action': 'return None',
                }},
            ],
        }),
        encoding='utf-8',
    )
    productions_path.write_text(
        yaml.safe_dump({
            'production_rules': [
                {'expr': {
                    'grammar_id': 'arith',
                    'spec': 'expr : expr PLUS term',
                    'action': 'p[0] = p[1] + p[3]',
                }},
                {'expr': {
                    'grammar_id': 'arith',
                    'spec': 'expr : term',
                }},
                {'term': {
                    'grammar_id': 'arith',
                    'spec': 'term : NUMBER',
                }},
            ],
        }),
        encoding='utf-8',
    )
    grammars_path.write_text(
        yaml.safe_dump({
            'grammars': {
                'arith': {
                    'parent_ids': [],
                    'start': 'expr',
                },
            },
        }),
        encoding='utf-8',
    )

    # Point DI catalogue paths at the temporary files.
    assets = Path(__file__).resolve().parents[2] / 'tiferet_ly' / 'assets'
    di_path = tmp_path / 'di.yml'
    di_path.write_text(
        (assets / 'di.yml').read_text(encoding='utf-8')
        .replace('token_config: tokens.yml', f'token_config: {tokens_path}')
        .replace(
            'production_config: productions.yml',
            f'production_config: {productions_path}',
        )
        .replace('grammar_config: grammars.yml', f'grammar_config: {grammars_path}'),
        encoding='utf-8',
    )
    app_path = tmp_path / 'app.yml'
    app_path.write_text(
        (assets / 'app.yml').read_text(encoding='utf-8')
        .replace(
            'logging_config: tiferet_ly/assets/app.yml',
            f'logging_config: {assets / "app.yml"}',
        )
        .replace(
            'di_config: tiferet_ly/assets/di.yml',
            f'di_config: {di_path}',
        )
        .replace(
            'error_config: tiferet_ly/assets/error.yml',
            f'error_config: {assets / "error.yml"}',
        )
        .replace(
            'feature_config: tiferet_ly/assets/feature.yml',
            f'feature_config: {assets / "feature.yml"}',
        ),
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)

    # Run both Features through the wired app session.
    app = App('tiferet_ly', app_config=str(app_path))
    lexemes = app.run('lex.default', data={'grammar_id': 'arith', 'text': '1+2'})
    value = app.run('parse.default', data={'grammar_id': 'arith', 'text': '1+2'})

    # Assert lex returns NUMBER PLUS NUMBER and parse returns the sum.
    assert [lexeme.type for lexeme in lexemes] == ['NUMBER', 'PLUS', 'NUMBER']
    assert lexemes[0].lineno == 1
    assert lexemes[0].lexpos == 0
    assert value == 3
