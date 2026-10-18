"""Tiferet Ly Grammar Mapper Tests"""

# *** imports

# ** core
import ast
from pathlib import Path

# ** infra
import pytest
from pydantic import ValidationError
from tiferet import (
    Aggregate,
    TransferObject,
    use_tester,
)

# ** app
from tiferet_ly.domain import Grammar
from tiferet_ly.mappers import grammar as grammar_mappers
from tiferet_ly.mappers.grammar import (
    GrammarAggregate,
    GrammarConfigObject,
)

# *** constants

# ** constant: retired_names
_RETIRED_NAMES = (
    'token_rules',
    'production_rules',
    'subgrammars',
    'precedence',
    'associativity',
    'subgrammar',
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

# ** function: class_method_artifacts
def _class_method_artifacts(tree: ast.AST, class_name: str) -> list[str]:
    '''
    Collect method artifact comments declared on one class.

    :param tree: The parsed module.
    :type tree: ast.AST
    :param class_name: The class whose body comments to read.
    :type class_name: str
    :return: Method artifact comment lines, in source order.
    :rtype: list[str]
    '''

    # Read only the named class body, not nested scopes.
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                line.strip()
                for line in ast.get_source_segment(Path(grammar_mappers.__file__).read_text(), node).splitlines()
                if line.strip().startswith('# * method:')
            ]
    return []

# *** tests

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

# ** test: method_artifacts
def test_method_artifacts():
    '''
    Declare only the published mutation and mapping methods.
    '''

    # The aggregate declares the two mutation methods and no others.
    tree = ast.parse(Path(grammar_mappers.__file__).read_text())
    assert _class_method_artifacts(tree, 'GrammarAggregate') == [
        '# * method: set_start',
        '# * method: set_parent_ids',
    ]
    assert set(GrammarAggregate.__dict__) >= {'set_start', 'set_parent_ids'}

    # The config object declares map and from_model only.
    assert _class_method_artifacts(tree, 'GrammarConfigObject') == [
        '# * method: map',
        '# * method: from_model',
    ]

# *** testers

# ** tester: test_grammar_aggregate
@use_tester(
    type='aggregate',
    target_cls=GrammarAggregate,
    sample_data={
        'id': 'expr',
        'parent_ids': ['term', 'factor'],
        'start': 'expr',
    },
    equality_fields=['id', 'parent_ids', 'start'],
)
class TestGrammarAggregate:
    '''
    Tests for the lean grammar aggregate.
    '''

    # * test: bases_and_fields
    def test_bases_and_fields(self, test_ctx, session):
        '''
        Keep only identity, ordered parents, and the start name.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases and model fields match the published boundary.
        assert GrammarAggregate.__bases__ == (Grammar, Aggregate)
        assert set(GrammarAggregate.model_fields) == {'id', 'parent_ids', 'start', 'ignore'}
        test_ctx.assert_new()

    # * test: retired_shape_absent
    def test_retired_shape_absent(self, test_ctx, session):
        '''
        Omit the retired container shape and its catalogue fields.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Catalogue and precedence names are not exposed.
        for name in _RETIRED_NAMES:
            assert name not in GrammarAggregate.model_fields
            assert not hasattr(GrammarAggregate, name)

    # * test: set_start_and_parent_ids
    def test_set_start_and_parent_ids(self, test_ctx, session):
        '''
        Assign start and a copied parent list without resolving either.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The assigned parent list is a new list, not the caller's object.
        grammar = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='expr',
        )
        parents = ['a', 'b']
        assert grammar.set_start('term') is None
        assert grammar.start == 'term'
        assert grammar.set_parent_ids(parents) is None
        assert grammar.parent_ids == ['a', 'b']
        assert grammar.parent_ids is not parents

        # Later mutation of the caller's list does not change stored parents.
        parents.append('c')
        assert grammar.parent_ids == ['a', 'b']

    # * test: unresolved_values_do_not_raise
    def test_unresolved_values_do_not_raise(self, test_ctx, session):
        '''
        Accept an unresolvable parent, a self-parent, and an unresolved start.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of these assignments walks parents or resolves a production.
        grammar = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='expr',
        )
        grammar.set_parent_ids(['missing'])
        assert grammar.parent_ids == ['missing']
        grammar.set_parent_ids(['expr'])
        assert grammar.parent_ids == ['expr']
        grammar.set_start('missing')
        assert grammar.start == 'missing'

    # * test: ignore_defaults_to_none
    def test_ignore_defaults_to_none(self, test_ctx, session):
        '''
        Leave ignore None when the grammar omits it.

        :param test_ctx: The bound aggregate tester context.
        :type test_ctx: AggregateTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Construction without ignore does not raise and stores None.
        grammar = GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='expr',
        )
        assert grammar.ignore is None
        assert 'layout' not in GrammarAggregate.model_fields

# ** tester: test_grammar_config_object
@use_tester(
    type='transfer_object',
    target_cls=GrammarConfigObject,
    aggregate_cls=GrammarAggregate,
    sample_data={
        'id': 'expr',
        'parent_ids': ['term', 'factor'],
        'start': 'expr',
    },
    aggregate_sample_data={
        'id': 'expr',
        'parent_ids': ['term', 'factor'],
        'start': 'expr',
    },
    equality_fields=['id', 'parent_ids', 'start'],
)
class TestGrammarConfigObject:
    '''
    Tests for lean grammar configuration mapping.
    '''

    # * test: bases_roles_and_fields
    def test_bases_roles_and_fields(self, test_ctx, session):
        '''
        Extend the grammar model with the published roles and no new field.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Bases, roles, and model fields match the published boundary.
        assert GrammarConfigObject.__bases__ == (Grammar, TransferObject)
        assert set(GrammarConfigObject.model_fields) == {'id', 'parent_ids', 'start', 'ignore'}
        assert GrammarConfigObject._ROLES == {
            'to_model': {},
            'to_data': {'by_alias': True, 'exclude': {'id'}},
        }
        for name in _RETIRED_NAMES:
            assert name not in GrammarConfigObject.model_fields
            assert not hasattr(GrammarConfigObject, name)

    # * test: to_data_preserves_parent_order
    def test_to_data_preserves_parent_order(self, test_ctx, session):
        '''
        Serialize ordered parents and omit only the grammar id.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Declared parent order is the serialized order. No ignore key is written.
        primitive = GrammarConfigObject.from_model(GrammarAggregate(
            id='expr',
            parent_ids=['term', 'factor'],
            start='expr',
        )).to_primitive('to_data')
        assert primitive == {
            'parent_ids': ['term', 'factor'],
            'start': 'expr',
        }
        assert 'id' not in primitive
        assert 'layout' not in primitive

        # A declared ignore string is written after start, unchanged.
        declared = GrammarConfigObject.from_model(GrammarAggregate(
            id='expr',
            parent_ids=['term', 'factor'],
            start='expr',
            ignore=' \t',
        )).to_primitive('to_data')
        assert declared == {
            'parent_ids': ['term', 'factor'],
            'start': 'expr',
            'ignore': ' \t',
        }
        assert 'id' not in declared
        assert 'layout' not in declared

    # * test: to_data_keeps_empty_parents
    def test_to_data_keeps_empty_parents(self, test_ctx, session):
        '''
        Serialize an empty parent list rather than omitting it.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # An empty list is not None, so the role keeps it. No ignore key is written.
        primitive = GrammarConfigObject.from_model(GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='expr',
        )).to_primitive('to_data')
        assert primitive == {
            'parent_ids': [],
            'start': 'expr',
        }
        assert 'id' not in primitive
        assert 'layout' not in primitive

        # A declared ignore string is written alongside the empty parent list.
        declared = GrammarConfigObject.from_model(GrammarAggregate(
            id='expr',
            parent_ids=[],
            start='expr',
            ignore=' \t',
        )).to_primitive('to_data')
        assert declared == {
            'parent_ids': [],
            'start': 'expr',
            'ignore': ' \t',
        }
        assert 'id' not in declared
        assert 'layout' not in declared

    # * test: map_round_trip
    def test_map_round_trip(self, test_ctx, session):
        '''
        Map validated configuration back to the same aggregate dump.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Mapping does not reshape parents or drop declared order.
        original = GrammarAggregate(
            id='expr',
            parent_ids=['term', 'factor'],
            start='expr',
        )
        mapped = GrammarConfigObject.model_validate({
            'id': 'expr',
            'parent_ids': ['term', 'factor'],
            'start': 'expr',
        }).map()
        assert isinstance(mapped, GrammarAggregate)
        assert mapped.model_dump() == original.model_dump()

    # * test: map_does_not_validate_composition
    def test_map_does_not_validate_composition(self, test_ctx, session):
        '''
        Map empty, missing, self, and unresolved-start grammars without raising.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # None of these constructions consults a token or production rule.
        cases = [
            GrammarConfigObject(id='root', parent_ids=[], start='expr'),
            GrammarConfigObject(id='child', parent_ids=['missing'], start='expr'),
            GrammarConfigObject(id='loop', parent_ids=['loop'], start='expr'),
            GrammarConfigObject(id='expr', parent_ids=[], start='missing'),
        ]
        for config in cases:
            mapped = config.map()
            assert isinstance(mapped, GrammarAggregate)

    # * test: map_raises_when_id_missing
    def test_map_raises_when_id_missing(self, test_ctx, session):
        '''
        Accept a null id assignment, then fail at aggregate construction.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Transfer-object assignment does not validate the null id.
        config = GrammarConfigObject(
            id='expr',
            parent_ids=[],
            start='expr',
        )
        config.id = None
        assert config.id is None

        # Mapping raises the same type as constructing the aggregate directly.
        with pytest.raises(ValidationError) as mapped:
            config.map()
        with pytest.raises(ValidationError) as constructed:
            GrammarAggregate(id=None, parent_ids=[], start='expr')
        assert type(mapped.value) is type(constructed.value)

    # * test: unused_field_is_dropped
    def test_unused_field_is_dropped(self, test_ctx, session):
        '''
        Drop an unknown configuration field from both serialization and mapping.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Unused input is ignored. The empty parent list is kept.
        config = GrammarConfigObject.model_validate({
            'id': 'expr',
            'parent_ids': [],
            'start': 'expr',
            'unused': True,
        })
        primitive = config.to_primitive('to_data')
        assert primitive == {
            'parent_ids': [],
            'start': 'expr',
        }
        assert 'ignore' not in primitive
        assert 'layout' not in primitive

        # The mapped dump keeps a null ignore; to_data omits it.
        mapped = config.map()
        assert 'unused' not in mapped.model_dump()
        assert mapped.ignore is None
        assert mapped.model_dump()['ignore'] is None

    # * test: to_data_preserves_ignore
    def test_to_data_preserves_ignore(self, test_ctx, session):
        '''
        Serialize a declared ignore string exactly and keep the id out.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The space-then-tab string is not stripped, escaped, or compiled.
        primitive = GrammarConfigObject.from_model(GrammarAggregate(
            id='expr',
            parent_ids=['term', 'factor'],
            start='expr',
            ignore=' \t',
        )).to_primitive('to_data')
        assert primitive == {
            'parent_ids': ['term', 'factor'],
            'start': 'expr',
            'ignore': ' \t',
        }
        assert 'id' not in primitive
        assert 'layout' not in primitive

    # * test: map_preserves_ignore
    def test_map_preserves_ignore(self, test_ctx, session):
        '''
        Map a declared ignore string to the aggregate unchanged.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Validation then mapping keeps the same two-character string.
        mapped = GrammarConfigObject.model_validate({
            'id': 'expr',
            'parent_ids': ['term'],
            'start': 'expr',
            'ignore': ' \t',
        }).map()
        assert isinstance(mapped, GrammarAggregate)
        assert mapped.id == 'expr'
        assert mapped.parent_ids == ['term']
        assert mapped.start == 'expr'
        assert mapped.ignore == ' \t'
        assert 'layout' not in mapped.model_dump()

    # * test: map_without_ignore_stays_valid
    def test_map_without_ignore_stays_valid(self, test_ctx, session):
        '''
        Map a grammar with no ignore key, and take no ignore from parents.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # The published grammar body plus its injected id maps without ignore.
        mapped = GrammarConfigObject.model_validate({
            'id': 'arith',
            'parent_ids': [],
            'start': 'expr',
        }).map()
        assert isinstance(mapped, GrammarAggregate)
        assert mapped.ignore is None
        assert mapped.parent_ids == []
        assert mapped.start == 'expr'

        # A child grammar does not receive ignore through parent_ids.
        child = GrammarConfigObject(
            id='child',
            parent_ids=['arith'],
            start='expr',
        ).map()
        assert child.ignore is None
        assert child.parent_ids == ['arith']

    # * test: layout_key_is_dropped
    def test_layout_key_is_dropped(self, test_ctx, session):
        '''
        Drop a layout configuration key as unused input.

        :param test_ctx: The bound transfer-object tester context.
        :type test_ctx: TransferObjectTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        '''

        # Layout is not a field, so it is neither serialized nor mapped.
        config = GrammarConfigObject.model_validate({
            'id': 'expr',
            'parent_ids': [],
            'start': 'expr',
            'layout': {'indent_token': 'INDENT', 'dedent_token': 'DEDENT'},
        })
        assert 'layout' not in GrammarConfigObject.model_fields
        assert not hasattr(config, 'layout')
        assert 'layout' not in config.to_primitive('to_data')
        mapped = config.map()
        assert 'layout' not in mapped.model_dump()
        assert mapped.ignore is None
