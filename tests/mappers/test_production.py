"""Tiferet Ly Production Mapper Tests"""

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
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)
from tiferet_ly.mappers import core as mapper_core
from tiferet_ly.mappers import production as production_mappers
from tiferet_ly.mappers.core import wrap_keyed_entries
from tiferet_ly.mappers.production import (
    ComplexProductionRuleAggregate,
    ProductionRuleAggregate,
    ProductionRuleConfigObject,
    SimpleProductionRuleAggregate,
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

# ** function: defined_functions
def _defined_functions(tree: ast.AST) -> list[str]:
    '''
    Collect function names defined in a parsed module.

    :param tree: The parsed module.
    :type tree: ast.AST
    :return: Defined function names.
    :rtype: list[str]
    '''

    # Include nested definitions so a copied helper cannot hide.
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

# *** tests

# ** test: helpers_are_not_copied
def test_helpers_are_not_copied():
    '''
    Keep the keyed-entry helpers in mapper core, not the production mapper.
    '''

    # Neither this module nor the production mapper defines the helpers.
    production_tree = ast.parse(Path(production_mappers.__file__).read_text())
    test_tree = ast.parse(Path(__file__).read_text())
    for tree in (production_tree, test_tree):
        defined = _defined_functions(tree)
        assert 'expand_keyed_entries' not in defined
        assert 'wrap_keyed_entries' not in defined

    # This module calls the helper imported from mapper core.
    assert wrap_keyed_entries.__module__ == 'tiferet_ly.mappers.core'
    assert 'tiferet_ly.mappers.core' in _imported_modules(test_tree)

# ** test: test_module_imports
def test_test_module_imports():
    '''
    Import no PLY module and no later runtime package.
    '''

    # Forbidden packages stay out of this test module.
    for module in _imported_modules(ast.parse(Path(__file__).read_text())):
        assert module != 'ply' and not module.startswith('ply.')
        parts = module.split('.')
        if parts[:1] == ['tiferet_ly'] and len(parts) > 1:
            assert parts[1] not in ('repos', 'interfaces', 'events', 'utils')

# ** test: wrap_declared_catalogue
def test_wrap_declared_catalogue():
    '''
    Wrap repeated production names without collapsing alternatives.
    '''

    # The literal flat catalogue wraps in declared order.
    assert wrap_keyed_entries([
        {
            'name': 'expr',
            'grammar_id': 'boolean',
            'spec': 'expr OR term',
            'action': 'p[0] = p[1]',
        },
        {
            'name': 'expr',
            'grammar_id': 'arithmetic',
            'spec': 'expr PLUS term',
        },
        {
            'name': 'expr',
            'grammar_id': 'arithmetic',
            'spec': 'term',
        },
    ]) == [
        {
            'expr': {
                'grammar_id': 'boolean',
                'spec': 'expr OR term',
                'action': 'p[0] = p[1]',
            },
        },
        {
            'expr': {
                'grammar_id': 'arithmetic',
                'spec': 'expr PLUS term',
            },
        },
        {
            'expr': {
                'grammar_id': 'arithmetic',
                'spec': 'term',
            },
        },
    ]

# *** testers

# ** tester: test_production_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=ProductionRuleAggregate,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arithmetic',
    },
    equality_fields=['name', 'grammar_id'],
)
class TestProductionRuleAggregate:
    '''
    Tests for the production-rule aggregate base.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Keep only name and grammar membership on the production aggregate base.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases and model fields match the published boundary.
        assert ProductionRuleAggregate.__bases__ == (ProductionRule, Aggregate)
        assert set(ProductionRuleAggregate.model_fields) == {'name', 'grammar_id'}
        test_ctx.assert_new()

# ** tester: test_simple_production_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=SimpleProductionRuleAggregate,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arithmetic',
        'spec': 'term',
    },
    equality_fields=['name', 'grammar_id', 'spec'],
)
class TestSimpleProductionRuleAggregate:
    '''
    Tests for a mutable simple production rule.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Store name, grammar membership, and specification, and no action.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The simple variant extends the named-rule aggregate, not Aggregate directly.
        assert SimpleProductionRuleAggregate.__bases__ == (
            SimpleProductionRule,
            mapper_core.NamedRuleAggregate,
        )
        assert set(SimpleProductionRuleAggregate.model_fields) == {
            'name',
            'grammar_id',
            'spec',
        }
        assert not hasattr(SimpleProductionRuleAggregate, 'set_action')
        test_ctx.assert_new()

    # * test: rename_reassign_and_set_spec
    def test_rename_reassign_and_set_spec(self, test_ctx, session):
        '''
        Assign name, grammar id, and specification without resolving a grammar.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An unknown grammar id is stored, not resolved.
        rule = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='term',
        )
        assert rule.rename('term') is None
        assert rule.name == 'term'
        assert rule.reassign_grammar('boolean') is None
        assert rule.grammar_id == 'boolean'
        assert rule.set_spec('expr PLUS term') is None
        assert rule.spec == 'expr PLUS term'

# ** tester: test_complex_production_rule_aggregate
@use_tester(
    type='aggregate',
    target_cls=ComplexProductionRuleAggregate,
    sample_data={
        'name': 'expr',
        'grammar_id': 'boolean',
        'spec': 'expr OR term',
        'action': 'p[0] = p[1]',
    },
    equality_fields=['name', 'grammar_id', 'spec', 'action'],
)
class TestComplexProductionRuleAggregate:
    '''
    Tests for a mutable complex production rule.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Store name, grammar membership, specification, and action source.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The complex variant extends the named-rule aggregate.
        assert ComplexProductionRuleAggregate.__bases__ == (
            ComplexProductionRule,
            mapper_core.NamedRuleAggregate,
        )
        assert set(ComplexProductionRuleAggregate.model_fields) == {
            'name',
            'grammar_id',
            'spec',
            'action',
        }
        test_ctx.assert_new()

    # * test: rename_reassign_spec_and_action
    def test_rename_reassign_spec_and_action(self, test_ctx, session):
        '''
        Assign identity, specification, and action without compiling the action.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of the assignments resolves grammar membership.
        rule = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='boolean',
            spec='expr OR term',
            action='p[0] = p[1]',
        )
        assert rule.rename('term') is None
        assert rule.name == 'term'
        assert rule.reassign_grammar('arithmetic') is None
        assert rule.grammar_id == 'arithmetic'
        assert rule.set_spec('expr PLUS term') is None
        assert rule.spec == 'expr PLUS term'
        assert rule.set_action('p[0] = p[1] + p[3]') is None
        assert rule.action == 'p[0] = p[1] + p[3]'

# ** tester: test_production_rule_config_object
@use_tester(
    type='transfer_object',
    target_cls=ProductionRuleConfigObject,
    aggregate_cls=SimpleProductionRuleAggregate,
    sample_data={
        'name': 'expr',
        'grammar_id': 'arithmetic',
        'spec': 'term',
    },
    aggregate_sample_data={
        'name': 'expr',
        'grammar_id': 'arithmetic',
        'spec': 'term',
    },
    equality_fields=['name', 'grammar_id', 'spec'],
)
class TestProductionRuleConfigObject:
    '''
    Tests for production configuration mapping.
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

        # The config object is a direct transfer object, not a production rule.
        assert ProductionRuleConfigObject.__bases__ == (TransferObject,)
        assert ProductionRule not in ProductionRuleConfigObject.__mro__
        assert ProductionRuleConfigObject._ROLES == {
            'to_model': {},
            'to_data': {'by_alias': True},
        }
        bare = ProductionRuleConfigObject()
        assert bare.name is None
        assert bare.grammar_id is None
        assert bare.spec is None
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
        simple = ProductionRuleConfigObject(
            name='expr',
            grammar_id='arithmetic',
            spec='term',
        ).map()
        assert isinstance(simple, SimpleProductionRuleAggregate)
        assert 'action' not in type(simple).model_fields

        # An explicit null override also selects the simple aggregate.
        overridden = ProductionRuleConfigObject(
            name='expr',
            grammar_id='arithmetic',
            spec='expr PLUS term',
            action='p[0] = p[1]',
        ).map(action=None)
        assert isinstance(overridden, SimpleProductionRuleAggregate)
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
        mapped = ProductionRuleConfigObject(
            name='expr',
            grammar_id='boolean',
            spec='expr OR term',
            action='p[0] = p[1]',
        ).map()
        assert isinstance(mapped, ComplexProductionRuleAggregate)
        assert mapped.action == 'p[0] = p[1]'

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
        original = SimpleProductionRuleAggregate(
            name='expr',
            grammar_id='arithmetic',
            spec='term',
        )
        primitive = ProductionRuleConfigObject.from_model(original).to_primitive('to_data')
        assert primitive == {
            'name': 'expr',
            'grammar_id': 'arithmetic',
            'spec': 'term',
        }
        restored = ProductionRuleConfigObject.model_validate(primitive).map()
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
        original = ComplexProductionRuleAggregate(
            name='expr',
            grammar_id='boolean',
            spec='expr OR term',
            action='p[0] = p[1]',
        )
        primitive = ProductionRuleConfigObject.from_model(original).to_primitive('to_data')
        assert primitive == {
            'name': 'expr',
            'grammar_id': 'boolean',
            'spec': 'expr OR term',
            'action': 'p[0] = p[1]',
        }
        restored = ProductionRuleConfigObject.model_validate(primitive).map()
        assert restored.model_dump() == original.model_dump()

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session):
        '''
        Round-trip the same production name under two grammars.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Neither construction consults the other grammar.
        originals = [
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='arithmetic',
                spec='expr PLUS term',
            ),
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='boolean',
                spec='expr OR term',
            ),
        ]
        for original in originals:
            primitive = ProductionRuleConfigObject.from_model(original).to_primitive('to_data')
            restored = ProductionRuleConfigObject.model_validate(primitive).map()
            assert restored.model_dump() == original.model_dump()

    # * test: same_grammar_alternatives
    def test_same_grammar_alternatives(self, test_ctx, session):
        '''
        Keep two same-grammar productions as separate alternatives.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Repeated names in one grammar both complete the round trip.
        originals = [
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='arithmetic',
                spec='expr PLUS term',
            ),
            SimpleProductionRuleAggregate(
                name='expr',
                grammar_id='arithmetic',
                spec='term',
            ),
        ]
        primitives = []
        for original in originals:
            primitive = ProductionRuleConfigObject.from_model(original).to_primitive('to_data')
            restored = ProductionRuleConfigObject.model_validate(primitive).map()
            assert restored.model_dump() == original.model_dump()
            primitives.append(primitive)

        # Wrapping does not collapse the two alternatives.
        assert wrap_keyed_entries(primitives) == [
            {
                'expr': {
                    'grammar_id': 'arithmetic',
                    'spec': 'expr PLUS term',
                },
            },
            {
                'expr': {
                    'grammar_id': 'arithmetic',
                    'spec': 'term',
                },
            },
        ]

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
        config = ProductionRuleConfigObject.model_validate({
            'name': 'expr',
            'spec': 'term',
        })

        # Mapping raises the same type as constructing the aggregate directly.
        with pytest.raises(ValidationError) as mapped:
            config.map()
        with pytest.raises(ValidationError) as constructed:
            SimpleProductionRuleAggregate(name='expr', spec='term')
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
        config = ProductionRuleConfigObject.model_validate({
            'name': 'expr',
            'grammar_id': 'missing',
            'spec': 'term',
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
        simple = ProductionRuleConfigObject.from_model(SimpleProductionRule(
            name='expr',
            grammar_id='arithmetic',
            spec='term',
        ))
        assert simple.action is None

        # A complex domain rule copies its action source.
        complex_rule = ProductionRuleConfigObject.from_model(ComplexProductionRule(
            name='expr',
            grammar_id='boolean',
            spec='expr OR term',
            action='p[0] = p[1]',
        ))
        assert complex_rule.action == 'p[0] = p[1]'
