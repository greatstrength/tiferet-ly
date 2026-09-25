"""Tiferet Ly Token Mapper Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** infra
import pytest
from pydantic import ValidationError

# ** app
from tiferet import (
    Aggregate,
    TransferObject,
    use_tester,
)
from tiferet_ly.domain import (
    ComplexTokenRule,
    SimpleTokenRule,
    TokenRule,
)
from tiferet_ly.mappers import core as mapper_core
from tiferet_ly.mappers import token as token_mappers
from tiferet_ly.mappers.core import (
    expand_keyed_entries,
    wrap_keyed_entries,
)
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    TokenRuleAggregate,
    TokenRuleConfigObject,
)

# *** functions

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

# ** test: package_marker_and_helper_home
def test_package_marker_and_helper_home():
    '''
    Keep the reshape helpers in mapper core, not the package marker.
    '''

    # The marker defines neither helper nor a mapper class.
    marker = Path(mapper_core.__file__).parent / '__init__.py'
    marker_tree = ast.parse(marker.read_text())
    marker_defs = [
        node.name
        for node in marker_tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    ]
    assert marker_defs == []
    assert _imported_modules(marker_tree) == []

    # Both helpers live under the functions section of mapper core.
    core_text = Path(mapper_core.__file__).read_text()
    functions_at = core_text.index('# *** functions')
    assert functions_at < core_text.index('def expand_keyed_entries')
    assert functions_at < core_text.index('def wrap_keyed_entries')
    assert expand_keyed_entries.__module__ == 'tiferet_ly.mappers.core'
    assert wrap_keyed_entries.__module__ == 'tiferet_ly.mappers.core'

    # Core does not import the domain, PLY, or a later runtime package.
    core_tree = ast.parse(core_text)
    for module in _imported_modules(core_tree):
        assert module != 'ply' and not module.startswith('ply.')
        assert not module.startswith('tiferet_ly.')

    # Token mappers do not redefine the helpers.
    token_tree = ast.parse(Path(token_mappers.__file__).read_text())
    token_defs = [
        node.name
        for node in ast.walk(token_tree)
        if isinstance(node, ast.FunctionDef)
    ]
    assert 'expand_keyed_entries' not in token_defs
    assert 'wrap_keyed_entries' not in token_defs

# ** test: test_module_imports
def test_test_module_imports():
    '''
    Call the helpers from mapper core and import no later runtime package.
    '''

    # This module imports the helpers from their owning module.
    tree = ast.parse(Path(__file__).read_text())
    imported = _imported_modules(tree)
    assert 'tiferet_ly.mappers.core' in imported

    # No PLY or later runtime package is imported.
    for module in imported:
        assert module != 'ply' and not module.startswith('ply.')
        parts = module.split('.')
        if parts[:1] == ['tiferet_ly'] and len(parts) > 1:
            assert parts[1] not in ('repos', 'interfaces', 'events', 'utils')

# ** test: empty_keyed_entries
def test_empty_keyed_entries():
    '''
    Return a new empty list from either helper.
    '''

    # Neither helper reuses or mutates the empty input.
    empty = []
    assert expand_keyed_entries(empty) == []
    assert expand_keyed_entries(empty) is not empty
    assert wrap_keyed_entries(empty) == []
    assert wrap_keyed_entries(empty) is not empty
    assert empty == []

# ** test: wrap_declared_catalogue
def test_wrap_declared_catalogue():
    '''
    Wrap a mixed catalogue without sorting, merging, or inserting action.
    '''

    # The literal flat catalogue wraps in declared order.
    assert wrap_keyed_entries([
        {
            'name': 'NUMBER',
            'grammar_id': 'arithmetic',
            'pattern': 'digits',
            'action': 't.value = int(t.value)',
        },
        {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'plus',
        },
        {
            'name': 'PLUS',
            'grammar_id': 'logic',
            'pattern': 'plus',
        },
    ]) == [
        {
            'NUMBER': {
                'grammar_id': 'arithmetic',
                'pattern': 'digits',
                'action': 't.value = int(t.value)',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'arithmetic',
                'pattern': 'plus',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'logic',
                'pattern': 'plus',
            },
        },
    ]

# ** test: expand_declared_catalogue
def test_expand_declared_catalogue():
    '''
    Expand a mixed catalogue without sorting or merging.
    '''

    # The literal keyed catalogue expands in declared order.
    assert expand_keyed_entries([
        {
            'NUMBER': {
                'grammar_id': 'arithmetic',
                'pattern': 'digits',
                'action': 't.value = int(t.value)',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'arithmetic',
                'pattern': 'plus',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'logic',
                'pattern': 'plus',
            },
        },
    ]) == [
        {
            'name': 'NUMBER',
            'grammar_id': 'arithmetic',
            'pattern': 'digits',
            'action': 't.value = int(t.value)',
        },
        {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'plus',
        },
        {
            'name': 'PLUS',
            'grammar_id': 'logic',
            'pattern': 'plus',
        },
    ]

# ** test: duplicate_names_stay_separate
def test_duplicate_names_stay_separate():
    '''
    Keep two same-named flat entries as two keyed entries.
    '''

    # Same name and grammar are not merged.
    assert wrap_keyed_entries([
        {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'plus',
        },
        {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'PLUS',
        },
    ]) == [
        {
            'PLUS': {
                'grammar_id': 'arithmetic',
                'pattern': 'plus',
            },
        },
        {
            'PLUS': {
                'grammar_id': 'arithmetic',
                'pattern': 'PLUS',
            },
        },
    ]

# ** test: mapping_key_wins_over_body_name
def test_mapping_key_wins_over_body_name():
    '''
    Let the mapping key replace a name already stored in the body.
    '''

    # The key wins; the body's name is not kept.
    assert expand_keyed_entries([
        {
            'PLUS': {
                'name': 'IGNORED',
                'grammar_id': 'arithmetic',
                'pattern': 'plus',
            },
        },
    ]) == [
        {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'plus',
        },
    ]

# ** test: helpers_do_not_mutate_input
def test_helpers_do_not_mutate_input():
    '''
    Leave keyed and flat inputs unchanged.
    '''

    # Expand copies the body and does not write name back into it.
    inner = {'grammar_id': 'arithmetic', 'pattern': 'plus'}
    wrapped = [{'PLUS': inner}]
    expand_keyed_entries(wrapped)
    assert wrapped == [{'PLUS': {'grammar_id': 'arithmetic', 'pattern': 'plus'}}]
    assert wrapped[0]['PLUS'] is inner
    assert 'name' not in inner

    # Wrap copies the flat dict and does not pop name from it.
    flat_entry = {'name': 'PLUS', 'grammar_id': 'arithmetic', 'pattern': 'plus'}
    flat = [flat_entry]
    wrap_keyed_entries(flat)
    assert flat == [{'name': 'PLUS', 'grammar_id': 'arithmetic', 'pattern': 'plus'}]
    assert flat[0] is flat_entry

# *** testers

# ** tester: test_token_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=TokenRuleAggregate,
    sample_data={
        'name': 'PLUS',
        'grammar_id': 'arithmetic',
    },
    equality_fields=['name', 'grammar_id'],
)
class TestTokenRuleAggregate:
    '''
    Tests for the token-rule aggregate base.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Keep only name and grammar membership on the token aggregate base.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases and model fields match the published boundary.
        assert TokenRuleAggregate.__bases__ == (TokenRule, Aggregate)
        assert set(TokenRuleAggregate.model_fields) == {'name', 'grammar_id'}
        test_ctx.assert_new()

# ** tester: test_simple_token_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=SimpleTokenRuleAggregate,
    sample_data={
        'name': 'PLUS',
        'grammar_id': 'arithmetic',
        'pattern': 'plus',
    },
    equality_fields=['name', 'grammar_id', 'pattern'],
)
class TestSimpleTokenRuleAggregate:
    '''
    Tests for a mutable simple token rule.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Store name, grammar membership, and pattern, and no action.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The simple variant extends the named-rule aggregate, not Aggregate directly.
        assert SimpleTokenRuleAggregate.__bases__ == (
            SimpleTokenRule,
            mapper_core.NamedRuleAggregate,
        )
        assert set(SimpleTokenRuleAggregate.model_fields) == {
            'name',
            'grammar_id',
            'pattern',
        }
        assert not hasattr(SimpleTokenRuleAggregate, 'set_action')
        test_ctx.assert_new()

    # * test: rename_reassign_and_set_pattern
    def test_rename_reassign_and_set_pattern(self, test_ctx, session):
        '''
        Assign name, grammar id, and pattern without resolving a grammar.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An unknown grammar id is stored, not resolved.
        rule = SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='arithmetic',
            pattern='plus',
        )
        assert rule.rename('SUM') is None
        assert rule.name == 'SUM'
        assert rule.reassign_grammar('logic') is None
        assert rule.grammar_id == 'logic'
        assert rule.set_pattern('PLUS') is None
        assert rule.pattern == 'PLUS'

# ** tester: test_complex_token_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=ComplexTokenRuleAggregate,
    sample_data={
        'name': 'NUMBER',
        'grammar_id': 'arithmetic',
        'pattern': 'digits',
        'action': 't.value = int(t.value)',
    },
    equality_fields=['name', 'grammar_id', 'pattern', 'action'],
)
class TestComplexTokenRuleAggregate:
    '''
    Tests for a mutable complex token rule.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Store name, grammar membership, pattern, and action source.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The complex variant extends the named-rule aggregate.
        assert ComplexTokenRuleAggregate.__bases__ == (
            ComplexTokenRule,
            mapper_core.NamedRuleAggregate,
        )
        assert set(ComplexTokenRuleAggregate.model_fields) == {
            'name',
            'grammar_id',
            'pattern',
            'action',
        }
        test_ctx.assert_new()

    # * test: rename_reassign_pattern_and_action
    def test_rename_reassign_pattern_and_action(self, test_ctx, session):
        '''
        Assign identity, pattern, and action without compiling the action.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of the assignments resolves grammar membership.
        rule = ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern='digits',
            action='t.value = int(t.value)',
        )
        assert rule.rename('SUM') is None
        assert rule.name == 'SUM'
        assert rule.reassign_grammar('logic') is None
        assert rule.grammar_id == 'logic'
        assert rule.set_pattern('PLUS') is None
        assert rule.pattern == 'PLUS'
        assert rule.set_action('return t') is None
        assert rule.action == 'return t'

# ** tester: test_token_rule_config_object
@use_tester(
    type='transfer_object',
    target_cls=TokenRuleConfigObject,
    aggregate_cls=SimpleTokenRuleAggregate,
    sample_data={
        'name': 'PLUS',
        'grammar_id': 'arithmetic',
        'pattern': 'plus',
    },
    aggregate_sample_data={
        'name': 'PLUS',
        'grammar_id': 'arithmetic',
        'pattern': 'plus',
    },
    equality_fields=['name', 'grammar_id', 'pattern'],
)
class TestTokenRuleConfigObject:
    '''
    Tests for token configuration mapping.
    '''

    # * test: roles_and_defaults
    def test_roles_and_defaults(self, test_ctx, session):
        '''
        Expose the published roles and nullable declared fields.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The config object is a direct transfer object, not a token rule.
        assert TokenRuleConfigObject.__bases__ == (TransferObject,)
        assert TokenRule not in TokenRuleConfigObject.__mro__
        assert TokenRuleConfigObject._ROLES == {
            'to_model': {},
            'to_data': {'by_alias': True},
        }
        bare = TokenRuleConfigObject()
        assert bare.name is None
        assert bare.grammar_id is None
        assert bare.pattern is None
        assert bare.action is None

    # * test: map_simple_when_action_missing
    def test_map_simple_when_action_missing(self, test_ctx, session):
        '''
        Map a missing or overridden-away action to a simple aggregate.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A missing action does not become an aggregate field.
        simple = TokenRuleConfigObject(
            name='PLUS',
            grammar_id='arithmetic',
            pattern='plus',
        ).map()
        assert isinstance(simple, SimpleTokenRuleAggregate)
        assert 'action' not in type(simple).model_fields

        # An explicit null override also selects the simple aggregate.
        overridden = TokenRuleConfigObject(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern='digits',
            action='t.value = int(t.value)',
        ).map(action=None)
        assert isinstance(overridden, SimpleTokenRuleAggregate)
        assert 'action' not in type(overridden).model_fields

    # * test: map_complex_when_action_present
    def test_map_complex_when_action_present(self, test_ctx, session):
        '''
        Map a present action to a complex aggregate.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The action source is stored, not compiled.
        mapped = TokenRuleConfigObject(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern='digits',
            action='t.value = int(t.value)',
        ).map()
        assert isinstance(mapped, ComplexTokenRuleAggregate)
        assert mapped.action == 't.value = int(t.value)'

    # * test: simple_round_trip
    def test_simple_round_trip(self, test_ctx, session):
        '''
        Round-trip a simple aggregate through to_data without an action key.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Serialization omits the null action, then map restores the aggregate.
        original = SimpleTokenRuleAggregate(
            name='PLUS',
            grammar_id='arithmetic',
            pattern='plus',
        )
        primitive = TokenRuleConfigObject.from_model(original).to_primitive('to_data')
        assert primitive == {
            'name': 'PLUS',
            'grammar_id': 'arithmetic',
            'pattern': 'plus',
        }
        restored = TokenRuleConfigObject.model_validate(primitive).map()
        assert restored.model_dump() == original.model_dump()

    # * test: complex_round_trip
    def test_complex_round_trip(self, test_ctx, session):
        '''
        Round-trip a complex aggregate through to_data with its action.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The action is serialized because the role does not exclude it.
        original = ComplexTokenRuleAggregate(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern='digits',
            action='t.value = int(t.value)',
        )
        primitive = TokenRuleConfigObject.from_model(original).to_primitive('to_data')
        assert primitive == {
            'name': 'NUMBER',
            'grammar_id': 'arithmetic',
            'pattern': 'digits',
            'action': 't.value = int(t.value)',
        }
        restored = TokenRuleConfigObject.model_validate(primitive).map()
        assert restored.model_dump() == original.model_dump()

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session):
        '''
        Round-trip the same token name under two grammars.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Neither construction consults the other grammar.
        for grammar_id in ('arithmetic', 'logic'):
            original = SimpleTokenRuleAggregate(
                name='PLUS',
                grammar_id=grammar_id,
                pattern='plus',
            )
            primitive = TokenRuleConfigObject.from_model(original).to_primitive('to_data')
            restored = TokenRuleConfigObject.model_validate(primitive).map()
            assert restored.model_dump() == original.model_dump()

    # * test: map_raises_when_grammar_id_missing
    def test_map_raises_when_grammar_id_missing(self, test_ctx, session):
        '''
        Accept partial configuration, then fail at aggregate construction.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Configuration validation does not require grammar membership.
        config = TokenRuleConfigObject.model_validate({
            'name': 'PLUS',
            'pattern': 'plus',
        })

        # Mapping raises the same type as constructing the aggregate directly.
        with pytest.raises(ValidationError) as mapped:
            config.map()
        with pytest.raises(ValidationError) as constructed:
            SimpleTokenRuleAggregate(name='PLUS', pattern='plus')
        assert type(mapped.value) is type(constructed.value)

    # * test: unknown_grammar_and_unused_field
    def test_unknown_grammar_and_unused_field(self, test_ctx, session):
        '''
        Keep an unresolved grammar id and drop an unknown configuration field.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Unused input is ignored. The grammar id is not resolved.
        config = TokenRuleConfigObject.model_validate({
            'name': 'PLUS',
            'grammar_id': 'missing',
            'pattern': 'plus',
            'unused': True,
        })
        mapped = config.map()
        assert mapped.grammar_id == 'missing'
        assert 'unused' not in config.to_primitive('to_data')
        assert 'unused' not in mapped.model_dump()

    # * test: from_model_domain_rules
    def test_from_model_domain_rules(self, test_ctx, session):
        '''
        Copy action only from a complex domain rule.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # A simple domain rule has no action to copy.
        simple = TokenRuleConfigObject.from_model(SimpleTokenRule(
            name='PLUS',
            grammar_id='arithmetic',
            pattern='plus',
        ))
        assert simple.action is None

        # A complex domain rule copies its action source.
        complex_rule = TokenRuleConfigObject.from_model(ComplexTokenRule(
            name='NUMBER',
            grammar_id='arithmetic',
            pattern='digits',
            action='t.value = int(t.value)',
        ))
        assert complex_rule.action == 't.value = int(t.value)'
