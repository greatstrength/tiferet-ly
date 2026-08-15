"""Tests for Tiferet-Ly PLY Translation Utility"""

# *** imports

# ** core
import inspect

# ** infra
import pytest

# ** app
from tiferet.interfaces.core import ServiceError
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    SimpleProductionRuleAggregate,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.mappers.ast import AstNodeAggregate
from tiferet_ly.utils.translation import (
    ACTION_COMPILATION_FAILED_ID,
    RULE_PATTERN_INVALID_ID,
    RuleTranslator,
    rewrite_action,
)

# *** functions

# ** function: simple_token
def simple_token(
        name: str = 'PLUS',
        grammar_id: str = 'arithmetic',
        pattern: str = r'\+') -> SimpleTokenRuleAggregate:
    '''
    Construct a simple token rule for translator tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :return: The constructed simple token rule.
    :rtype: SimpleTokenRuleAggregate
    '''

    # Construct a simple token under the given grammar.
    return SimpleTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
    )

# ** function: complex_token
def complex_token(
        name: str = 'NUMBER',
        grammar_id: str = 'arithmetic',
        pattern: str = r'\d+',
        action: str = 't.value = int(t.value)\nreturn t') -> ComplexTokenRuleAggregate:
    '''
    Construct a complex token rule for translator tests.

    :param name: The token name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param pattern: The token pattern.
    :type pattern: str
    :param action: The encoded action source.
    :type action: str
    :return: The constructed complex token rule.
    :rtype: ComplexTokenRuleAggregate
    '''

    # Construct a complex token under the given grammar.
    return ComplexTokenRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        pattern=pattern,
        action=action,
    )

# ** function: simple_production
def simple_production(
        name: str = 'expression',
        grammar_id: str = 'arithmetic',
        spec: str = 'expression : term') -> SimpleProductionRuleAggregate:
    '''
    Construct a simple production rule for translator tests.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :return: The constructed simple production rule.
    :rtype: SimpleProductionRuleAggregate
    '''

    # Construct a simple production under the given grammar.
    return SimpleProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
    )

# ** function: complex_production
def complex_production(
        name: str = 'expression',
        grammar_id: str = 'arithmetic',
        spec: str = 'expression : expression PLUS term',
        action: str = 'p[0] = p[1] + p[3]') -> ComplexProductionRuleAggregate:
    '''
    Construct a complex production rule for translator tests.

    :param name: The production name.
    :type name: str
    :param grammar_id: The owning grammar id.
    :type grammar_id: str
    :param spec: The production spec.
    :type spec: str
    :param action: The encoded action source.
    :type action: str
    :return: The constructed complex production rule.
    :rtype: ComplexProductionRuleAggregate
    '''

    # Construct a complex production under the given grammar.
    return ComplexProductionRuleAggregate(
        name=name,
        grammar_id=grammar_id,
        spec=spec,
        action=action,
    )

# *** tests

# ** test: translate_token_rule_simple_is_identity
def test_translate_token_rule_simple_is_identity() -> None:
    '''
    Test that a simple token rule returns the declared pattern unchanged.
    '''

    # Translate a simple PLUS token.
    pattern = r'\+'
    attr_name, value = RuleTranslator.translate_token_rule(
        simple_token(pattern=pattern),
    )

    # Assert the pair is the prefixed name and the identical pattern string.
    assert attr_name == 't_PLUS'
    assert value == pattern
    assert value is pattern

# ** test: translate_token_rule_complex_synthesizes_function
def test_translate_token_rule_complex_synthesizes_function() -> None:
    '''
    Test that a complex token rule becomes a one-arg function with the pattern as __doc__.
    '''

    # Translate a NUMBER token whose action mutates t.value.
    attr_name, func = RuleTranslator.translate_token_rule(complex_token())

    # Call the function with a stand-in whose value the action converts.
    token = type('Token', (), {'value': '12'})()
    result = func(token)

    # Assert the pair, signature, docstring, and mutation.
    assert attr_name == 't_NUMBER'
    assert callable(func)
    assert len(inspect.signature(func).parameters) == 1
    assert func.__doc__ == r'\d+'
    assert token.value == 12
    assert result is token

# ** test: translate_production_rule_complex_synthesizes_function
def test_translate_production_rule_complex_synthesizes_function() -> None:
    '''
    Test that a complex production becomes a one-arg function with the spec as __doc__.
    '''

    # Translate an adding production whose action writes p[0].
    spec = 'expression : expression PLUS term'
    attr_name, func = RuleTranslator.translate_production_rule(
        complex_production(spec=spec, action='p[0] = p[1] + p[3]'),
    )

    # Call the function with a stand-in list the action can index.
    parsed = [None, 2, '+', 3]
    func(parsed)

    # Assert the pair, signature, docstring, and mutation.
    assert attr_name == 'p_expression'
    assert callable(func)
    assert len(inspect.signature(func).parameters) == 1
    assert func.__doc__ == spec
    assert parsed[0] == 5

# ** test: translate_production_rule_simple_pass_through
def test_translate_production_rule_simple_pass_through() -> None:
    '''
    Test that a one-symbol simple production synthesizes p[0] = p[1].
    '''

    # Translate a single-symbol pass-through production.
    attr_name, func = RuleTranslator.translate_production_rule(simple_production())

    # Call the function with a stand-in whose first symbol should be copied.
    parsed = [None, 'term']
    func(parsed)

    # Assert the pair, docstring, and pass-through assignment.
    assert attr_name == 'p_expression'
    assert func.__doc__ == 'expression : term'
    assert parsed[0] == 'term'

# ** test: translate_production_rule_simple_rejects_zero_symbol_rhs
def test_translate_production_rule_simple_rejects_zero_symbol_rhs() -> None:
    '''
    Test that a simple production with an empty right-hand side is invalid.
    '''

    # Translate a spec whose right-hand side has no symbols.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_production_rule(
            simple_production(name='empty', spec='empty :'),
        )

    # Assert the structured pattern-invalid error names the rule.
    assert raised.value.error_code == RULE_PATTERN_INVALID_ID
    assert raised.value.kwargs['rule_name'] == 'empty'

# ** test: translate_production_rule_simple_rejects_multi_symbol_rhs
def test_translate_production_rule_simple_rejects_multi_symbol_rhs() -> None:
    '''
    Test that a simple production with more than one right-hand-side symbol is invalid.
    '''

    # Translate a spec whose right-hand side has two symbols.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_production_rule(
            simple_production(
                name='binary',
                spec='expression : expression PLUS',
            ),
        )

    # Assert the structured pattern-invalid error names the rule.
    assert raised.value.error_code == RULE_PATTERN_INVALID_ID
    assert raised.value.kwargs['rule_name'] == 'binary'

# ** test: translate_token_rule_syntax_error_is_attributable
def test_translate_token_rule_syntax_error_is_attributable() -> None:
    '''
    Test that a syntax error in a token action raises ACTION_COMPILATION_FAILED.
    '''

    # Translate a complex token whose action is not valid Python.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_token_rule(
            complex_token(action='t.value ='),
        )

    # Assert the structured compilation error names the rule and chains SyntaxError.
    assert raised.value.error_code == ACTION_COMPILATION_FAILED_ID
    assert raised.value.kwargs['rule_name'] == 'NUMBER'
    assert isinstance(raised.value.__cause__, SyntaxError)

# ** test: translate_production_rule_syntax_error_is_attributable
def test_translate_production_rule_syntax_error_is_attributable() -> None:
    '''
    Test that a syntax error in a production action raises ACTION_COMPILATION_FAILED.
    '''

    # Translate a complex production whose action is not valid Python.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_production_rule(
            complex_production(action='p[0] ='),
        )

    # Assert the structured compilation error names the rule and chains SyntaxError.
    assert raised.value.error_code == ACTION_COMPILATION_FAILED_ID
    assert raised.value.kwargs['rule_name'] == 'expression'
    assert isinstance(raised.value.__cause__, SyntaxError)

# ** test: translate_token_rule_invalid_pattern_before_synthesis
def test_translate_token_rule_invalid_pattern_before_synthesis() -> None:
    '''
    Test that an invalid regex pattern raises before any function is synthesized.
    '''

    # Translate a complex token whose pattern does not compile as a regex.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_token_rule(
            complex_token(pattern='[unterminated', action='return t'),
        )

    # Assert the structured pattern-invalid error names the rule.
    assert raised.value.error_code == RULE_PATTERN_INVALID_ID
    assert raised.value.kwargs['rule_name'] == 'NUMBER'

# ** test: derive_tokens_preserves_input_order
def test_derive_tokens_preserves_input_order() -> None:
    '''
    Test that derive_tokens returns bare names in the input list's order.
    '''

    # Derive tokens from a mixed-grammar list that is not alphabetical.
    names = RuleTranslator.derive_tokens([
        simple_token(name='ZETA', grammar_id='other', pattern='z'),
        simple_token(name='PLUS', grammar_id='arithmetic', pattern=r'\+'),
        simple_token(name='NUMBER', grammar_id='algebra', pattern=r'\d+'),
    ])

    # Assert the names match input order exactly.
    assert names == ['ZETA', 'PLUS', 'NUMBER']

# ** test: translation_calls_are_independent
def test_translation_calls_are_independent() -> None:
    '''
    Test that two translations of the same rule do not share function state.
    '''

    # Translate the same complex token twice.
    rule = complex_token()
    _, first = RuleTranslator.translate_token_rule(rule)
    _, second = RuleTranslator.translate_token_rule(rule)

    # Mutate only the first stand-in and assert the functions are distinct.
    first_token = type('Token', (), {'value': '1'})()
    second_token = type('Token', (), {'value': '2'})()
    first(first_token)
    second(second_token)

    # Assert independent objects with identical behavior and docstring.
    assert first is not second
    assert first.__doc__ == second.__doc__ == r'\d+'
    assert first_token.value == 1
    assert second_token.value == 2

# ** test: no_ply_import
def test_no_ply_import() -> None:
    '''
    Test that the translator module does not import ply.
    '''

    # Import the module under test and inspect its globals.
    import tiferet_ly.utils.translation as translation

    # Assert ply is not among the module's imported names.
    assert 'ply' not in translation.__dict__
    assert 'tiferet_ly.domain' not in translation.__dict__
    assert not any(
        name.startswith('tiferet_ly.domain')
        for name in getattr(translation, '__dict__', {})
    )


# ** test: default_rewrites_binds_ast_node_aggregate
def test_default_rewrites_binds_ast_node_aggregate() -> None:
    '''
    Test that the default rewrite table binds $ast to AstNodeAggregate.
    '''

    # Assert the published default table.
    assert RuleTranslator.DEFAULT_REWRITES == {
        '$ast': AstNodeAggregate,
    }


# ** test: translate_production_rule_rewrites_ast_new
def test_translate_production_rule_rewrites_ast_new() -> None:
    '''
    Test that $ast.new compiles to an AstNodeAggregate with those children.
    '''

    # Translate a production whose action constructs a generic add node.
    left = AstNodeAggregate.leaf('num', 1)
    right = AstNodeAggregate.leaf('num', 2)
    _, func = RuleTranslator.translate_production_rule(
        complex_production(action="p[0] = $ast.new('add', [p[1], p[3]])"),
    )
    parsed = [None, left, '+', right]
    func(parsed)

    # Assert the constructed node and that $ast is gone from the source.
    assert isinstance(parsed[0], AstNodeAggregate)
    assert parsed[0].kind == 'add'
    assert parsed[0].children == [left, right]
    assert '$ast' not in func.__code__.co_consts
    assert 'AstNodeAggregate' in func.__code__.co_names


# ** test: translate_production_rule_int_action_needs_no_ast
def test_translate_production_rule_int_action_needs_no_ast() -> None:
    '''
    Test that an int-returning action still compiles without $ast.
    '''

    # Translate a production that converts its first symbol to int.
    _, func = RuleTranslator.translate_production_rule(
        complex_production(action='p[0] = int(p[1])'),
    )
    parsed = [None, '12']
    func(parsed)

    # Assert the result is a plain int.
    assert parsed[0] == 12
    assert type(parsed[0]) is int


# ** test: translate_production_rule_simple_is_not_wrapped
def test_translate_production_rule_simple_is_not_wrapped() -> None:
    '''
    Test that a simple production is not wrapped in an AstNode.
    '''

    # Translate and invoke the literal pass-through.
    _, func = RuleTranslator.translate_production_rule(simple_production())
    parsed = [None, 7]
    func(parsed)

    # Assert the result is the first symbol, not a tree node.
    assert parsed[0] == 7
    assert not isinstance(parsed[0], AstNodeAggregate)


# ** test: translate_production_rule_merges_and_overwrites_rewrites
def test_translate_production_rule_merges_and_overwrites_rewrites() -> None:
    '''
    Test that caller rewrites merge with $ast and can overwrite $ast.
    '''

    # A test double whose new classmethod records construction.
    class SomeAggregate:
        def __init__(self, kind):
            self.kind = kind

        @classmethod
        def new(cls, kind):
            return cls(kind)

    class Subclass(AstNodeAggregate):
        pass

    # Merge: $decl constructs the double and $ast still constructs the default.
    _, decl_func = RuleTranslator.translate_production_rule(
        complex_production(action="p[0] = $decl.new('module')"),
        rewrites={'$decl': SomeAggregate},
    )
    parsed = [None]
    decl_func(parsed)
    assert isinstance(parsed[0], SomeAggregate)
    assert parsed[0].kind == 'module'

    _, ast_func = RuleTranslator.translate_production_rule(
        complex_production(action="p[0] = $ast.new('add')"),
        rewrites={'$decl': SomeAggregate},
    )
    parsed = [None]
    ast_func(parsed)
    assert type(parsed[0]) is AstNodeAggregate

    # Overwrite: $ast constructs the subclass.
    _, sub_func = RuleTranslator.translate_production_rule(
        complex_production(action="p[0] = $ast.new('add')"),
        rewrites={'$ast': Subclass},
    )
    parsed = [None]
    sub_func(parsed)
    assert type(parsed[0]) is Subclass


# ** test: rewrite_action_does_not_clip_longer_key
def test_rewrite_action_does_not_clip_longer_key() -> None:
    '''
    Test that $stmt does not rewrite the prefix of $stmt_list.
    '''

    # A two-row mapping whose shorter key is a prefix of the longer one.
    class Stmt:
        pass

    class StmtList:
        pass

    rewritten = rewrite_action(
        'p[0] = $stmt_list.new($stmt.new())',
        {
            '$stmt': Stmt,
            '$stmt_list': StmtList,
        },
    )

    # Assert each key rewrote independently.
    assert rewritten == 'p[0] = StmtList.new(Stmt.new())'


# ** test: shared_rewrite_class_name_fails_compilation
def test_shared_rewrite_class_name_fails_compilation() -> None:
    '''
    Test that two rewrite values sharing a __name__ fail compilation.
    '''

    # Two distinct classes that collide on the bound name.
    class Factory:
        @classmethod
        def new(cls):
            return cls()

    other = type('Factory', (), {'new': classmethod(lambda cls: cls())})

    # Compile an action that would need both binds.
    with pytest.raises(ServiceError) as raised:
        RuleTranslator.translate_production_rule(
            complex_production(action='p[0] = Factory.new()'),
            rewrites={
                '$one': Factory,
                '$two': other,
            },
        )

    # Assert the structured compilation error names the rule.
    assert raised.value.error_code == ACTION_COMPILATION_FAILED_ID
    assert raised.value.kwargs['rule_name'] == 'expression'


# ** test: translate_production_rule_invokes_subclass_compile_hook
def test_translate_production_rule_invokes_subclass_compile_hook() -> None:
    '''
    Test that a RuleTranslator subclass compile hook is the one invoked.
    '''

    # Record every compile call on a test subclass.
    calls = []

    class RecordingTranslator(RuleTranslator):
        @classmethod
        def _compile_action(cls, *args, **kwargs):
            calls.append((args, kwargs))
            return RuleTranslator._compile_action(*args, **kwargs)

    # Translate through the subclass.
    RecordingTranslator.translate_production_rule(
        complex_production(action='p[0] = int(p[1])'),
    )

    # Assert the subclass hook ran.
    assert len(calls) == 1
