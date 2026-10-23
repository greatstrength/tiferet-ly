"""Tests for Tiferet-Ly Declared Token Order (PlyReader Install Loop)"""

# *** imports

# ** core
import inspect

# ** infra
import pytest
from tiferet.interfaces.core import ServiceError

# ** app
from tiferet_ly.interfaces.lexer import LexerService
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.mappers.production import ComplexProductionRuleAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    SyntheticTokenRuleAggregate,
)
from tiferet_ly.utils.core import (
    ACTION_EXECUTION_FAILED_ID,
    LEX_ERROR_ID,
    PARSE_ERROR_ID,
    READER_BUILD_FAILED_ID,
    PlyReader,
)
from tiferet_ly.utils.lex import PlyLexer
from tiferet_ly.utils.parse import PlyParser
from tiferet_ly.utils.translation import RuleTranslator

# *** functions

# ** function: grammar
def grammar(id: str = 'order', parent_ids=None) -> GrammarAggregate:
    '''
    Construct a GrammarAggregate for declared-order tests.

    :param id: The grammar id.
    :type id: str
    :param parent_ids: Optional parent ids.
    :type parent_ids: list | None
    :return: The constructed grammar.
    :rtype: GrammarAggregate
    '''

    # Construct a lean grammar with an expr start symbol.
    return GrammarAggregate(id=id, parent_ids=list(parent_ids or []), start='expr')

# ** function: complex_token
def complex_token(
        name: str,
        pattern: str = 'x',
        action: str = 'return t',
        grammar_id: str = 'order') -> ComplexTokenRuleAggregate:
    '''
    Construct a complex (function-based) token rule.

    :param name: The declared token name.
    :type name: str
    :param pattern: The token pattern.
    :type pattern: str
    :param action: The token action body.
    :type action: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The complex token rule.
    :rtype: ComplexTokenRuleAggregate
    '''

    # Construct the complex rule as declared.
    return ComplexTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
        action=action,
    )

# ** function: simple_token
def simple_token(
        name: str,
        pattern: str = 'x',
        grammar_id: str = 'order') -> SimpleTokenRuleAggregate:
    '''
    Construct a simple (pattern-only) token rule.

    :param name: The declared token name.
    :type name: str
    :param pattern: The token pattern.
    :type pattern: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :return: The simple token rule.
    :rtype: SimpleTokenRuleAggregate
    '''

    # Construct the pattern-only rule as declared.
    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
    )

# ** function: tokenize
def tokenize(
        tokens: list,
        text: str,
        target: GrammarAggregate = None,
        grammars: list = None) -> list:
    '''
    Tokenize text against a token catalogue with PlyLexer.

    :param tokens: The token catalogue.
    :type tokens: list
    :param text: The source text.
    :type text: str
    :param target: Optional target grammar.
    :type target: GrammarAggregate
    :param grammars: Optional grammar catalogue.
    :type grammars: list
    :return: The produced lexemes.
    :rtype: list
    '''

    # Default to the single order grammar.
    target = target or grammar()
    grammars = grammars or [target]
    return PlyLexer().tokenize(target.id, grammars, tokens, text)

# ** function: build_module
def build_module(tokens: list):
    '''
    Build a lexer module for the order grammar.

    :param tokens: The token catalogue.
    :type tokens: list
    :return: The throwaway module.
    :rtype: Any
    '''

    # Assemble via the shared reader.
    target = grammar()
    reader = PlyReader()
    _lexer, module = reader.build_lexer_module(
        target,
        [target],
        tokens,
        None,
        reader.make_t_error(target.id),
    )
    return module

# ** function: callable_t_attrs
def callable_t_attrs(module) -> list:
    '''
    List callable t_* attribute names on a module, t_error excluded.

    :param module: The throwaway module.
    :type module: Any
    :return: The callable t_* names.
    :rtype: list
    '''

    # Collect callables the way PLY collects rules.
    return [
        name for name in dir(module)
        if name.startswith('t_')
        and name != 't_error'
        and callable(getattr(module, name))
    ]

# ** function: types_of
def types_of(lexemes: list) -> list:
    '''
    Project lexemes to their types.

    :param lexemes: The lexemes.
    :type lexemes: list
    :return: The lexeme types.
    :rtype: list
    '''

    # Read the type of each lexeme.
    return [lexeme.type for lexeme in lexemes]

# *** tests

# ** test: complex_rules_match_in_selected_order
def test_complex_rules_match_in_selected_order() -> None:
    '''
    Test that the first selected complex rule wins over an alphabetically
    earlier name, and that reversing the catalogue reverses the winner.
    '''

    # Declare Z_FIRST before A_SECOND, both pattern x.
    tokens = [complex_token('Z_FIRST'), complex_token('A_SECOND')]

    # Tokenize one and two characters.
    one = tokenize(tokens, 'x')
    two = tokenize(tokens, 'xx')
    reversed_one = tokenize(list(reversed(tokens)), 'x')

    # Assert declared order picks the winner.
    assert len(one) == 1
    assert isinstance(one[0], LexemeAggregate)
    assert one[0].type == 'Z_FIRST'
    assert one[0].value == 'x'
    assert one[0].lineno == 1
    assert one[0].lexpos == 0
    assert types_of(two) == ['Z_FIRST', 'Z_FIRST']
    assert [lexeme.lexpos for lexeme in two] == [0, 1]
    assert types_of(reversed_one) == ['A_SECOND']

# ** test: keyword_and_identifier_follow_declared_order
def test_keyword_and_identifier_follow_declared_order() -> None:
    '''
    Test that keyword-versus-identifier follows declaration, not names.
    '''

    # Z_ID before A_IF yields Z_ID.
    assert types_of(tokenize(
        [complex_token('Z_ID', pattern='[a-z]+'), complex_token('A_IF', pattern='if')],
        'if',
    )) == ['Z_ID']

    # IF before ID yields IF.
    assert types_of(tokenize(
        [complex_token('IF', pattern='if'), complex_token('ID', pattern='[a-z]+')],
        'if',
    )) == ['IF']

    # ID before IF yields ID.
    assert types_of(tokenize(
        [complex_token('ID', pattern='[a-z]+'), complex_token('IF', pattern='if')],
        'if',
    )) == ['ID']

# ** test: keyword_prefix_then_identifier_rest
def test_keyword_prefix_then_identifier_rest() -> None:
    '''
    Test that IF declared before ID takes the if prefix of iffy, and ID
    takes the rest.
    '''

    # IF before ID on iffy.
    result = tokenize(
        [complex_token('IF', pattern='if'), complex_token('ID', pattern='[a-z]+')],
        'iffy',
    )

    # Assert IF 'if' then ID 'fy'.
    assert [(lexeme.type, lexeme.value) for lexeme in result] == [
        ('IF', 'if'),
        ('ID', 'fy'),
    ]

# ** test: non_matching_complex_rule_is_skipped
def test_non_matching_complex_rule_is_skipped() -> None:
    '''
    Test that a non-matching earlier rule is skipped for the next match.
    '''

    # Z_NO (y), then M_YES (x), then A_ALSO (x).
    tokens = [
        complex_token('Z_NO', pattern='y'),
        complex_token('M_YES', pattern='x'),
        complex_token('A_ALSO', pattern='x'),
    ]

    # Assert the first matching rule in order wins.
    assert types_of(tokenize(tokens, 'x')) == ['M_YES']

# ** test: walk_matches_at_lexpos_on_original_text
def test_walk_matches_at_lexpos_on_original_text() -> None:
    '''
    Test that the walk re-matches on the original text at t.lexpos, so a
    lookahead pattern still identifies its rule.
    '''

    # A consumes a only when b follows; B consumes b.
    tokens = [complex_token('A', pattern='a(?=b)'), complex_token('B', pattern='b')]

    # Assert both rules are identified.
    assert types_of(tokenize(tokens, 'ab')) == ['A', 'B']

# ** test: winner_returning_none_drops_match
def test_winner_returning_none_drops_match() -> None:
    '''
    Test that a winning action returning None drops the match and the later
    rule's action does not run.
    '''

    # A_SECOND would raise if it ever ran.
    tokens = [
        complex_token('Z_FIRST', action='return None'),
        complex_token('A_SECOND', action='raise ValueError("ran")'),
    ]

    # Assert nothing is emitted and nothing raised.
    assert tokenize(tokens, 'x') == []

# ** test: winner_action_failure_is_attributed
def test_winner_action_failure_is_attributed() -> None:
    '''
    Test that a raise in the winning action is ACTION_EXECUTION_FAILED with
    the t_<name> attribution and the original cause.
    '''

    # Z_FIRST raises; A_SECOND would succeed.
    tokens = [
        complex_token('Z_FIRST', action="raise ValueError('boom')"),
        complex_token('A_SECOND'),
    ]

    # Tokenize the shared text.
    with pytest.raises(ServiceError) as raised:
        tokenize(tokens, 'x')

    # Assert the structured failure names the winner.
    assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
    assert raised.value.kwargs['grammar_id'] == 'order'
    assert raised.value.kwargs['rule_name'] == 't_Z_FIRST'
    assert isinstance(raised.value.__cause__, ValueError)
    assert str(raised.value.__cause__) == 'boom'

# ** test: winner_action_sees_declared_type
def test_winner_action_sees_declared_type() -> None:
    '''
    Test that the winning action sees its declared name as t.type, keeps an
    assignment to another selected name, and an unknown type still fails
    with a null rule_name.
    '''

    # The action observes its declared name.
    result = tokenize(
        [complex_token('Z_FIRST', action='t.value = t.type\nreturn t')],
        'x',
    )
    assert types_of(result) == ['Z_FIRST']
    assert result[0].value == 'Z_FIRST'

    # The action reassigns t.type to a selected token that does not match.
    result = tokenize(
        [
            complex_token('Z_FIRST', action="t.type = 'A_SECOND'\nreturn t"),
            complex_token('A_SECOND', pattern='y'),
        ],
        'x',
    )
    assert types_of(result) == ['A_SECOND']

    # An unknown type fails after the action, with rule_name null.
    with pytest.raises(ServiceError) as raised:
        tokenize(
            [complex_token('Z_FIRST', action="t.type = 'NOPE'\nreturn t")],
            'x',
        )
    assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
    assert raised.value.kwargs['rule_name'] is None

# ** test: walk_without_rematch_falls_back_to_unknown_type
def test_walk_without_rematch_falls_back_to_unknown_type() -> None:
    '''
    Test the reachable fallback: a conditional-group pattern that the
    alternation matches but the walk does not re-match fails as
    ACTION_EXECUTION_FAILED with rule_name null.
    '''

    # The conditional refers to a group number the master renumbers.
    tokens = [complex_token('COND', pattern='(a)?(?(1)b|c)')]

    # Tokenize text only the master alternation accepts.
    with pytest.raises(ServiceError) as raised:
        tokenize(tokens, 'ac')

    # Assert the existing unknown-type failure with null attribution.
    assert raised.value.error_code == ACTION_EXECUTION_FAILED_ID
    assert raised.value.kwargs['rule_name'] is None

# ** test: winner_action_uses_default_rewrites
def test_winner_action_uses_default_rewrites() -> None:
    '''
    Test that the winning action's $ast shorthand builds an AstNodeAggregate
    through the default rewrite table, with rewrites omitted.
    '''

    # Z_FIRST builds a leaf; the later same-pattern rule would set 'later'.
    tokens = [
        complex_token('Z_FIRST', action="t.value = $ast.leaf('lit', t.value)\nreturn t"),
        complex_token('A_SECOND', action="t.value = 'later'\nreturn t"),
    ]

    # Tokenize with rewrites omitted.
    result = tokenize(tokens, 'x')

    # Assert one Z_FIRST lexeme carrying the leaf.
    assert types_of(result) == ['Z_FIRST']
    assert isinstance(result[0].value, AstNodeAggregate)
    assert result[0].value.kind == 'lit'
    assert result[0].value.value == 'x'

# ** test: pattern_only_rules_keep_ply_length_sort
def test_pattern_only_rules_keep_ply_length_sort() -> None:
    '''
    Test that pattern-only rules keep longest-first and PLY's same-length tie.
    '''

    # Longest pattern wins in either catalogue order.
    for tokens in (
        [simple_token('SHORT', pattern='x'), simple_token('LONG', pattern='xx')],
        [simple_token('LONG', pattern='xx'), simple_token('SHORT', pattern='x')],
    ):
        result = tokenize(tokens, 'xx')
        assert types_of(result) == ['LONG']
        assert result[0].value == 'xx'

    # A same-length tie stays PLY's tie in either catalogue order.
    for tokens in (
        [simple_token('Z_FIRST'), simple_token('A_SECOND')],
        [simple_token('A_SECOND'), simple_token('Z_FIRST')],
    ):
        assert types_of(tokenize(tokens, 'x')) == ['A_SECOND']

# ** test: complex_rules_stay_ahead_of_pattern_only_rules
def test_complex_rules_stay_ahead_of_pattern_only_rules() -> None:
    '''
    Test that the function-before-string split stays and a non-matching
    complex rule still falls through to a pattern-only rule.
    '''

    # A complex x beats a simple xx in either catalogue order.
    for tokens in (
        [complex_token('CX', pattern='x'), simple_token('SXX', pattern='xx')],
        [simple_token('SXX', pattern='xx'), complex_token('CX', pattern='x')],
    ):
        result = tokenize(tokens, 'xx')
        assert types_of(result) == ['CX', 'CX']
        assert [lexeme.value for lexeme in result] == ['x', 'x']

    # A complex y falls through to a simple x in either catalogue order.
    for tokens in (
        [complex_token('CY', pattern='y'), simple_token('SX', pattern='x')],
        [simple_token('SX', pattern='x'), complex_token('CY', pattern='y')],
    ):
        assert types_of(tokenize(tokens, 'x')) == ['SX']

# ** test: build_lexer_module_installs_one_dispatcher
def test_build_lexer_module_installs_one_dispatcher() -> None:
    '''
    Test that complex rules install as exactly one non-public dispatcher,
    including a set of one, and pattern-only sets install no function.
    '''

    # Two complex rules.
    module = build_module([complex_token('Z_FIRST'), complex_token('A_SECOND')])
    assert module.tokens == ['Z_FIRST', 'A_SECOND']
    assert not callable(getattr(module, 't_Z_FIRST', None))
    assert not callable(getattr(module, 't_A_SECOND', None))
    extra = callable_t_attrs(module)
    assert len(extra) == 1
    assert extra[0] not in (
        't_Z_FIRST', 't_A_SECOND', 't_error', 't_ignore', 't_eof',
    )
    assert extra[0][len('t_'):] not in module.tokens

    # A set of one complex rule has the same shape.
    module = build_module([complex_token('ONLY')])
    assert module.tokens == ['ONLY']
    assert not callable(getattr(module, 't_ONLY', None))
    assert len(callable_t_attrs(module)) == 1

    # Pattern-only rules install strings and no extra function.
    module = build_module([simple_token('SHORT', pattern='x'), simple_token('LONG', pattern='xx')])
    assert module.t_SHORT == 'x'
    assert module.t_LONG == 'xx'
    assert callable_t_attrs(module) == []

# ** test: dispatcher_name_avoids_selected_names
def test_dispatcher_name_avoids_selected_names() -> None:
    '''
    Test that the dispatcher is not named t_<name> for a selected token whose
    name would otherwise collide with it.
    '''

    # Find the dispatcher name, then declare a token with that bare name.
    probe = build_module([complex_token('Z_FIRST')])
    taken = callable_t_attrs(probe)[0][len('t_'):]
    module = build_module([complex_token('Z_FIRST'), complex_token(taken, pattern='y')])

    # Assert the dispatcher moved and is still a single non-token callable.
    extra = callable_t_attrs(module)
    assert len(extra) == 1
    assert extra[0][len('t_'):] not in module.tokens
    assert types_of(tokenize(
        [complex_token('Z_FIRST'), complex_token(taken, pattern='y')],
        'xy',
    )) == ['Z_FIRST', taken]

# ** test: synthetic_rule_is_not_a_candidate
def test_synthetic_rule_is_not_a_candidate() -> None:
    '''
    Test that a synthetic rule stays on module.tokens with no t_* attribute
    and is not a match candidate.
    '''

    # Z_FIRST, synthetic INDENT, A_SECOND.
    tokens = [
        complex_token('Z_FIRST'),
        SyntheticTokenRuleAggregate(name='INDENT', grammar_id='order'),
        complex_token('A_SECOND'),
    ]

    # Assert installation and tokenization.
    module = build_module(tokens)
    assert module.tokens == ['Z_FIRST', 'INDENT', 'A_SECOND']
    assert not hasattr(module, 't_INDENT')
    assert types_of(tokenize(tokens, 'x')) == ['Z_FIRST']

# ** test: parse_from_text_inherits_declared_order
def test_parse_from_text_inherits_declared_order() -> None:
    '''
    Test that text parse uses declared order and a lexeme stream is not
    re-lexed.
    '''

    # Z_FIRST then A_SECOND, both x.
    tokens = [complex_token('Z_FIRST'), complex_token('A_SECOND')]

    # expr : Z_FIRST accepts x.
    assert PlyParser().parse(
        'order',
        [grammar()],
        tokens,
        [ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='order',
            spec='expr : Z_FIRST',
            action='p[0] = p[1]',
        )],
        text='x',
    ) == 'x'

    # expr : A_SECOND rejects x as a Z_FIRST token.
    a_second = [ComplexProductionRuleAggregate(
        name='expr',
        grammar_id='order',
        spec='expr : A_SECOND',
        action='p[0] = p[1]',
    )]
    with pytest.raises(ServiceError) as raised:
        PlyParser().parse('order', [grammar()], tokens, a_second, text='x')
    assert raised.value.error_code == PARSE_ERROR_ID
    assert raised.value.kwargs['type'] == 'Z_FIRST'

    # A supplied A_SECOND lexeme stream parses without rebuilding a lexer.
    lexemes = [LexemeAggregate(type='A_SECOND', value='x', lineno=1, lexpos=0)]
    original = PlyReader.build_lexer_module

    def fail_build(*args, **kwargs):
        raise AssertionError('build_lexer_module must not be called')

    PlyReader.build_lexer_module = fail_build
    try:
        result = PlyParser().parse(
            'order',
            [grammar()],
            tokens,
            a_second,
            lexemes=lexemes,
        )
    finally:
        PlyReader.build_lexer_module = original
    assert result == 'x'

# ** test: dropping_action_falls_through_to_next_lexeme
def test_dropping_action_falls_through_to_next_lexeme() -> None:
    '''
    Test that a whitespace/comment action returning None leaves the next
    number to be recognized.
    '''

    # WS drops whitespace and comments; NUMBER converts.
    tokens = [
        complex_token('WS', pattern=r'(\s+|#.*)', action='return None'),
        complex_token('NUMBER', pattern=r'\d+', action='t.value = int(t.value)\nreturn t'),
    ]

    # Assert two numbers survive.
    result = tokenize(tokens, '1 # c\n2')
    assert types_of(result) == ['NUMBER', 'NUMBER']
    assert [lexeme.value for lexeme in result] == [1, 2]

# ** test: dispatcher_keeps_reflags_spans_and_ignore
def test_dispatcher_keeps_reflags_spans_and_ignore() -> None:
    '''
    Test reflags=0 (no VERBOSE), lineno and lexpos mutation, and t_ignore.
    '''

    # Pattern a b is literal, not verbose.
    result = tokenize([complex_token('AB', pattern='a b')], 'a b')
    assert [lexeme.value for lexeme in result] == ['a b']
    with pytest.raises(ServiceError) as raised:
        tokenize([complex_token('AB', pattern='a b')], 'ab')
    assert raised.value.error_code == LEX_ERROR_ID

    # NL bumps lineno for the next lexeme.
    result = tokenize(
        [
            complex_token('NL', pattern=r'\n', action='t.lexer.lineno += 1\nreturn t'),
            complex_token('X', pattern='x'),
        ],
        'x\nx',
    )
    assert [(lexeme.type, lexeme.lineno, lexeme.lexpos) for lexeme in result] == [
        ('X', 1, 0),
        ('NL', 1, 1),
        ('X', 2, 2),
    ]

    # A declared ignore still skips before the dispatcher.
    target = grammar()
    target.ignore = ' '
    result = tokenize([complex_token('X', pattern='x')], ' x', target=target)
    assert [(lexeme.type, lexeme.lexpos) for lexeme in result] == [('X', 1)]

# ** test: inherited_complex_rules_follow_catalogue_order
def test_inherited_complex_rules_follow_catalogue_order() -> None:
    '''
    Test that parent and child complex rules follow catalogue order and a
    dropped same-name rule is not a candidate.
    '''

    # Parent and child grammars.
    parent = grammar(id='parent')
    child = grammar(id='child', parent_ids=['parent'])
    grammars = [parent, child]
    z_mark = complex_token('Z_MARK', grammar_id='parent')
    a_mark = complex_token('A_MARK', grammar_id='child')

    # Parent-then-child yields Z_MARK; reversed yields A_MARK.
    assert types_of(tokenize([z_mark, a_mark], 'x', target=child, grammars=grammars)) == ['Z_MARK']
    assert types_of(tokenize([a_mark, z_mark], 'x', target=child, grammars=grammars)) == ['A_MARK']

    # A parent MARK on x is dropped for the child's MARK on y.
    tokens = [
        complex_token('MARK', pattern='x', grammar_id='parent'),
        complex_token('MARK', pattern='y', grammar_id='child'),
    ]
    assert types_of(tokenize(tokens, 'y', target=child, grammars=grammars)) == ['MARK']
    with pytest.raises(ServiceError) as raised:
        tokenize(tokens, 'x', target=child, grammars=grammars)
    assert raised.value.error_code == LEX_ERROR_ID

# ** test: public_surface_is_unchanged
def test_public_surface_is_unchanged() -> None:
    '''
    Test that service signatures and translate_token_rule are unchanged.
    '''

    # Service signatures keep their parameters.
    assert list(inspect.signature(LexerService.tokenize).parameters) == [
        'self', 'grammar_id', 'grammars', 'tokens', 'text', 'rewrites',
    ]
    assert list(inspect.signature(ParserService.parse).parameters) == [
        'self', 'grammar_id', 'grammars', 'tokens', 'productions', 'text',
        'lexemes', 'rewrites',
    ]

    # translate_token_rule still returns one compiled t_<name> function.
    name, func = RuleTranslator.translate_token_rule(complex_token('Z_FIRST'))
    assert name == 't_Z_FIRST'
    assert callable(func)
    assert func.__doc__ == 'x'
    assert func.__code__.co_filename == '<tiferet_ly:t_Z_FIRST>'
    assert RuleTranslator.translate_token_rule(
        SyntheticTokenRuleAggregate(name='INDENT', grammar_id='order'),
    ) is None

# ** test: duplicate_inner_group_names_fail_at_build
def test_duplicate_inner_group_names_fail_at_build() -> None:
    '''
    Test the pinned known limitation: inner named groups must be unique
    across the declared complex token rules, or the build fails.
    '''

    # Two complex rules reuse the inner group name g.
    tokens = [complex_token('A', pattern='(?P<g>a)'), complex_token('B', pattern='(?P<g>b)')]

    # Assert the joined dispatcher pattern fails to build.
    with pytest.raises(ServiceError) as raised:
        tokenize(tokens, 'a')
    assert raised.value.error_code == READER_BUILD_FAILED_ID
