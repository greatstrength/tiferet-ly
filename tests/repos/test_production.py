"""Tiferet Ly Production Repository Tests"""

# *** imports

# ** core
import ast
import inspect
from pathlib import Path

# ** infra
import pytest
import yaml

# ** app
from tiferet import use_tester
from tiferet.interfaces import Service
from tiferet.repos.core import ConfigurationRepository
from tiferet_ly.interfaces import production as production_interface
from tiferet_ly.interfaces.production import ProductionService
from tiferet_ly.mappers.production import (
    ProductionRuleAggregate,
    ProductionRuleConfigObject,
)
from tiferet_ly.repos import production as production_repo
from tiferet_ly.repos.production import ProductionConfigRepository

# *** functions

# ** function: production_aggregate
def _production(
        name: str,
        grammar_id: str,
        spec: str,
        action: str | None = None,
    ):
    '''
    Build a production aggregate through the consumed config object.

    :param name: The declared production name.
    :type name: str
    :param grammar_id: The grammar that owns the production.
    :type grammar_id: str
    :param spec: The declared production specification.
    :type spec: str
    :param action: Optional action source.
    :type action: str | None
    :return: The mapped production aggregate.
    :rtype: SimpleProductionRuleAggregate | ComplexProductionRuleAggregate
    '''

    # Tests construct aggregates only through model_validate().map().
    data = {
        'name': name,
        'grammar_id': grammar_id,
        'spec': spec,
    }
    if action is not None:
        data['action'] = action
    return ProductionRuleConfigObject.model_validate(data).map()

# ** function: parsed_yaml
def _parsed(path: Path) -> dict:
    '''
    Parse a YAML file into a dictionary.

    :param path: The YAML file path.
    :type path: Path
    :return: The parsed document. An empty file is an empty dict.
    :rtype: dict
    '''

    # Empty YAML is an empty document.
    loaded = yaml.safe_load(path.read_text(encoding='utf-8'))
    if loaded is None:
        return {}
    return loaded

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

# ** function: seeded_alternatives
def _seeded_alternatives() -> dict:
    '''
    Return the three-alternative document used by the pair-lookup criteria.

    :return: A document whose production_rules hold two arithmetic alternatives.
    :rtype: dict
    '''

    # Keep the declared order: first arithmetic, second arithmetic, then other.
    return {
        'production_rules': [
            {
                'expression': {
                    'grammar_id': 'arithmetic',
                    'spec': 'expression : expression PLUS term',
                },
            },
            {
                'expression': {
                    'grammar_id': 'arithmetic',
                    'spec': 'expression : term',
                },
            },
            {
                'expression': {
                    'grammar_id': 'other',
                    'spec': 'expression : NAME',
                },
            },
        ],
    }

# *** fixtures

# ** fixture: write_yaml
@pytest.fixture
def write_yaml(tmp_path):
    '''
    Write a parsed document to a real temporary YAML file.

    :param tmp_path: The pytest temporary directory.
    :type tmp_path: Path
    :return: A writer that returns the file path.
    :rtype: Callable
    '''

    def write(document: dict, name: str = 'production_rules.yml') -> Path:
        '''
        Write one document and return its path.

        :param document: The document to serialize.
        :type document: dict
        :param name: The file name. Must be a YAML extension.
        :type name: str
        :return: The written file path.
        :rtype: Path
        '''

        # Persist a real .yml file. Do not sort keys.
        path = tmp_path / name
        path.write_text(
            yaml.safe_dump(document, sort_keys=False),
            encoding='utf-8',
        )
        return path

    return write

# *** testers

# ** tester: test_production_config_repository
@use_tester(
    type='repo',
    target_cls=ProductionConfigRepository,
    config_parameter='production_config',
    exists_cases=[],
    get_cases=[],
    list_ids=[],
    delete_ids=[],
)
class TestProductionConfigRepository:
    '''
    Temporary-file tests for the production configuration repository.
    '''

    # * test: contract
    def test_contract(self, test_ctx, session, write_yaml):
        '''
        Keep the production service and repository on the published contract.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # The service is abstract and exposes exactly seven operations.
        assert issubclass(ProductionService, Service)
        assert ProductionService.__abstractmethods__ == frozenset({
            'exists',
            'get',
            'list',
            'save',
            'delete',
            'replace',
            'delete_alternative',
        })

        # Pair operations take name and grammar id. list takes neither.
        for name in ('exists', 'get', 'delete'):
            parameters = inspect.signature(getattr(ProductionService, name)).parameters
            assert list(parameters) == ['self', 'name', 'grammar_id']
            assert parameters['name'].annotation is str
            assert parameters['grammar_id'].annotation is str
        assert list(inspect.signature(ProductionService.list).parameters) == ['self']
        assert list(inspect.signature(ProductionService.save).parameters) == [
            'self',
            'production',
        ]
        save_production = inspect.signature(ProductionService.save).parameters['production']
        assert save_production.annotation is ProductionRuleAggregate

        # Triple operations add spec, and replace also takes the new aggregate.
        replace_parameters = inspect.signature(ProductionService.replace).parameters
        assert list(replace_parameters) == [
            'self',
            'old_name',
            'old_grammar_id',
            'old_spec',
            'production',
        ]
        assert replace_parameters['old_name'].annotation is str
        assert replace_parameters['old_grammar_id'].annotation is str
        assert replace_parameters['old_spec'].annotation is str
        assert replace_parameters['production'].annotation is ProductionRuleAggregate
        alternative = inspect.signature(ProductionService.delete_alternative).parameters
        assert list(alternative) == ['self', 'name', 'grammar_id', 'spec']
        assert alternative['spec'].annotation is str

        # Return annotations match the published contract.
        assert inspect.signature(ProductionService.exists).return_annotation is bool
        assert inspect.signature(ProductionService.get).return_annotation == (
            ProductionRuleAggregate | None
        )
        assert inspect.signature(ProductionService.list).return_annotation == (
            list[ProductionRuleAggregate]
        )
        assert inspect.signature(ProductionService.save).return_annotation is None
        assert inspect.signature(ProductionService.delete).return_annotation is None
        assert inspect.signature(ProductionService.replace).return_annotation is None
        assert inspect.signature(
            ProductionService.delete_alternative,
        ).return_annotation is None

        # The repository subclasses both bases and does not override the role.
        assert issubclass(ProductionConfigRepository, ProductionService)
        assert issubclass(ProductionConfigRepository, ConfigurationRepository)
        assert 'default_role' not in ProductionConfigRepository.__dict__
        init = inspect.signature(ProductionConfigRepository.__init__)
        assert list(init.parameters) == ['self', 'production_config', 'encoding']
        assert init.parameters['production_config'].annotation is str
        assert init.parameters['encoding'].default == 'utf-8'
        assert init.parameters['encoding'].annotation is str

        # Both reshape methods exist. The single-id case lists stay empty.
        assert callable(ProductionConfigRepository._unwrap_named_entries)
        assert callable(ProductionConfigRepository._wrap_named_entries)
        assert test_ctx.domain.exists_cases == []
        assert test_ctx.domain.get_cases == []
        assert test_ctx.domain.list_ids == []
        assert test_ctx.domain.delete_ids == []

        # Package markers export nothing and do not import these classes.
        interfaces_marker = Path(production_interface.__file__).parent / '__init__.py'
        repos_marker = Path(production_repo.__file__).parent / '__init__.py'
        assert interfaces_marker.read_text(encoding='utf-8') == (
            '"""tiferet-ly interfaces package."""\n'
            '\n'
            '# *** exports\n'
            '\n'
            '__all__ = []\n'
        )
        assert repos_marker.read_text(encoding='utf-8') == (
            '"""tiferet-ly repositories package."""\n'
            '\n'
            '# *** exports\n'
            '\n'
            '__all__ = []\n'
        )
        assert 'ProductionService' not in interfaces_marker.read_text(encoding='utf-8')
        assert 'ProductionConfigRepository' not in repos_marker.read_text(encoding='utf-8')

        # The repository module imports none of the forbidden packages.
        repo_tree = ast.parse(Path(production_repo.__file__).read_text(encoding='utf-8'))
        imported = _imported_modules(repo_tree)
        forbidden = (
            'tiferet_ly.domain',
            'tiferet_ly.events',
            'tiferet_ly.utils',
            'tiferet_ly.repos.token',
            'tiferet_ly.repos.grammar',
            'ply',
        )
        for module in imported:
            assert module not in forbidden
            assert not module.startswith('ply.')
            assert not module.startswith('tiferet_ly.domain')
            assert not module.startswith('tiferet_ly.events')
            assert not module.startswith('tiferet_ly.utils')
            assert not module.startswith('tiferet_ly.repos.token')
            assert not module.startswith('tiferet_ly.repos.grammar')
        assigned = [
            target.id
            for node in repo_tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        ]
        assert assigned == []

        # A constructed repository keeps the inherited serialization role.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        assert isinstance(repo, ProductionConfigRepository)
        assert repo.default_role == 'to_data'

    # * test: missing_production_rules_node
    def test_missing_production_rules_node(self, test_ctx, session, write_yaml):
        '''
        Treat a missing production_rules node as empty, and do not write on reads.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed a document that has no production_rules node.
        path = write_yaml({'grammars': {'kept': {'start': 'expression'}}})
        before = path.read_bytes()
        repo = test_ctx.make_target(config_file=str(path))

        # Reads report absence and do not change the file.
        assert repo.exists('expression', 'arithmetic') is False
        assert repo.get('expression', 'arithmetic') is None
        assert repo.list() == []
        assert path.read_bytes() == before

        # Delete of an absent pair does not raise.
        repo.delete('expression', 'arithmetic')
        reloaded = test_ctx.make_target(config_file=str(path))
        assert reloaded.exists('expression', 'arithmetic') is False
        assert reloaded.get('expression', 'arithmetic') is None
        assert reloaded.list() == []

    # * test: unwrap_does_not_invent_grammar_id
    def test_unwrap_does_not_invent_grammar_id(self, test_ctx, session, write_yaml):
        '''
        Unwrap a named entry without adding a grammar id the body lacks.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Unwrap does not read the file. The path only satisfies construction.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        unwrapped = repo._unwrap_named_entries([
            {
                'expression': {
                    'grammar_id': 'arithmetic',
                    'spec': 'expression : term',
                },
            },
        ])

        # The mapping key becomes name. The body's grammar id is kept.
        assert unwrapped[0]['name'] == 'expression'
        assert unwrapped[0]['grammar_id'] == 'arithmetic'
        assert unwrapped[0]['spec'] == 'expression : term'

        # A body without grammar_id does not gain one.
        bare = repo._unwrap_named_entries([
            {'expression': {'spec': 'expression : term'}},
        ])
        assert bare == [{'name': 'expression', 'spec': 'expression : term'}]
        assert 'grammar_id' not in bare[0]

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session, write_yaml):
        '''
        Persist the same production name under two grammars, including one action.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save the simple pair, then reload before saving the complex pair.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.save(_production('expression', 'g1', 'expression : term')) is None
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.save(
            _production(
                'expression',
                'g2',
                'expression : NAME',
                action='p[0] = p[1]',
            ),
        ) is None

        # A new repository reads both pairs without collapsing the name.
        repo = test_ctx.make_target(config_file=str(path))
        simple = repo.get('expression', 'g1')
        complex_rule = repo.get('expression', 'g2')
        assert simple.spec == 'expression : term'
        assert not hasattr(simple, 'action')
        assert complex_rule.spec == 'expression : NAME'
        assert complex_rule.action == 'p[0] = p[1]'
        listed = repo.list()
        assert [(item.name, item.grammar_id) for item in listed] == [
            ('expression', 'g1'),
            ('expression', 'g2'),
        ]

    # * test: declared_order
    def test_declared_order(self, test_ctx, session, write_yaml):
        '''
        Keep declared order, including two entries that share a grammar id.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save three productions in an order that is not grouped by grammar id.
        path = write_yaml({})
        saves = (
            _production('term', 'zeta', 'term : NUMBER'),
            _production('expr', 'alpha', 'expr : NAME', action='p[0] = p[1]'),
            _production('factor', 'zeta', 'factor : NUMBER'),
        )
        for production in saves:
            repo = test_ctx.make_target(config_file=str(path))
            repo.save(production)

        # A new repository returns that order, and the file matches it.
        repo = test_ctx.make_target(config_file=str(path))
        listed = repo.list()
        assert [(item.name, item.grammar_id, item.spec) for item in listed] == [
            ('term', 'zeta', 'term : NUMBER'),
            ('expr', 'alpha', 'expr : NAME'),
            ('factor', 'zeta', 'factor : NUMBER'),
        ]
        assert listed[1].action == 'p[0] = p[1]'
        assert not hasattr(listed[0], 'action')
        assert not hasattr(listed[2], 'action')
        assert _parsed(path) == {
            'production_rules': [
                {'term': {'grammar_id': 'zeta', 'spec': 'term : NUMBER'}},
                {
                    'expr': {
                        'grammar_id': 'alpha',
                        'spec': 'expr : NAME',
                        'action': 'p[0] = p[1]',
                    },
                },
                {'factor': {'grammar_id': 'zeta', 'spec': 'factor : NUMBER'}},
            ],
        }

    # * test: different_spec_appends_then_pair_delete
    def test_different_spec_appends_then_pair_delete(self, test_ctx, session, write_yaml):
        '''
        Append a new specification, replace the original triple, then delete the pair.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save three distinct triples, reloading after each write.
        path = write_yaml({})
        for production in (
            _production('one', 'g1', 'one : A'),
            _production('two', 'g1', 'two : B'),
            _production('three', 'g1', 'three : C'),
        ):
            repo = test_ctx.make_target(config_file=str(path))
            repo.save(production)

        # A different spec for two appends and leaves the original row unchanged.
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_production('two', 'g1', 'two : B2'))
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.spec) for item in repo.list()] == [
            ('one', 'one : A'),
            ('two', 'two : B'),
            ('three', 'three : C'),
            ('two', 'two : B2'),
        ]

        # Saving the original spec again replaces that row and does not append.
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_production('two', 'g1', 'two : B', action='p[0] = p[1]'))
        repo = test_ctx.make_target(config_file=str(path))
        listed = repo.list()
        assert [(item.name, item.spec) for item in listed] == [
            ('one', 'one : A'),
            ('two', 'two : B'),
            ('three', 'three : C'),
            ('two', 'two : B2'),
        ]
        assert listed[1].action == 'p[0] = p[1]'
        assert len(_parsed(path)['production_rules']) == 4

        # Delete removes only the first two/g1 row. Later calls do not raise.
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.delete('two', 'g1') is None
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.spec) for item in repo.list()] == [
            ('one', 'one : A'),
            ('three', 'three : C'),
            ('two', 'two : B2'),
        ]
        assert repo.delete('absent', 'g1') is None
        assert repo.delete('two', 'g1') is None
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.spec) for item in repo.list()] == [
            ('one', 'one : A'),
            ('three', 'three : C'),
        ]

    # * test: first_pair_keeps_later_alternatives
    def test_first_pair_keeps_later_alternatives(self, test_ctx, session, write_yaml):
        '''
        Read, append, and pair-delete alternatives without collapsing the pair.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Reload the seeded alternatives in declared order.
        path = write_yaml(_seeded_alternatives())
        repo = test_ctx.make_target(config_file=str(path))
        listed = repo.list()
        assert [(item.name, item.grammar_id, item.spec) for item in listed] == [
            ('expression', 'arithmetic', 'expression : expression PLUS term'),
            ('expression', 'arithmetic', 'expression : term'),
            ('expression', 'other', 'expression : NAME'),
        ]
        assert repo.get('expression', 'arithmetic').spec == 'expression : expression PLUS term'
        assert len(listed) == 3

        # Saving a new spec appends and leaves the seeded rows in place.
        append_path = write_yaml(_seeded_alternatives(), name='append.yml')
        repo = test_ctx.make_target(config_file=str(append_path))
        repo.save(_production('expression', 'arithmetic', 'expression : factor'))
        repo = test_ctx.make_target(config_file=str(append_path))
        assert [(item.name, item.grammar_id, item.spec) for item in repo.list()] == [
            ('expression', 'arithmetic', 'expression : expression PLUS term'),
            ('expression', 'arithmetic', 'expression : term'),
            ('expression', 'other', 'expression : NAME'),
            ('expression', 'arithmetic', 'expression : factor'),
        ]

        # Pair delete removes only the first arithmetic alternative.
        delete_path = write_yaml(_seeded_alternatives(), name='delete.yml')
        repo = test_ctx.make_target(config_file=str(delete_path))
        repo.delete('expression', 'arithmetic')
        repo = test_ctx.make_target(config_file=str(delete_path))
        assert [(item.name, item.grammar_id, item.spec) for item in repo.list()] == [
            ('expression', 'arithmetic', 'expression : term'),
            ('expression', 'other', 'expression : NAME'),
        ]

    # * test: unknown_grammar_persists
    def test_unknown_grammar_persists(self, test_ctx, session, write_yaml):
        '''
        Save a production whose grammar id is not a key in grammars.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # The grammars node has no missing-grammar key.
        path = write_yaml({
            'grammars': {
                'arithmetic': {
                    'parent_ids': [],
                    'start': 'expression',
                },
            },
        })
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_production('orphan', 'missing-grammar', 'orphan : NAME'))

        # Reload keeps the unresolved grammar id.
        repo = test_ctx.make_target(config_file=str(path))
        orphan = repo.get('orphan', 'missing-grammar')
        assert orphan.grammar_id == 'missing-grammar'
        assert orphan.spec == 'orphan : NAME'

    # * test: save_leaves_other_roots
    def test_save_leaves_other_roots(self, test_ctx, session, write_yaml):
        '''
        Leave grammars and tokens unchanged when saving a production.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed the neighbouring catalogues and an empty production list.
        document = {
            'grammars': {
                'arithmetic': {
                    'parent_ids': [],
                    'start': 'expression',
                },
            },
            'tokens': [
                {
                    'PLUS': {
                        'grammar_id': 'arithmetic',
                        'pattern': 'plus',
                    },
                },
            ],
            'production_rules': [],
        }
        path = write_yaml(document)
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_production('expression', 'arithmetic', 'expression : term'))

        # Only production_rules changes.
        parsed = _parsed(path)
        assert parsed['grammars'] == document['grammars']
        assert parsed['tokens'] == document['tokens']
        assert parsed['production_rules'] == [
            {
                'expression': {
                    'grammar_id': 'arithmetic',
                    'spec': 'expression : term',
                },
            },
        ]

    # * test: reads_do_not_write
    def test_reads_do_not_write(self, test_ctx, session, write_yaml):
        '''
        Leave a populated file unchanged after exists, get, and list.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed one production, then snapshot the bytes the repository wrote.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_production('expression', 'g1', 'expression : term'))
        before = path.read_bytes()
        repo = test_ctx.make_target(config_file=str(path))

        # Reads do not call save.
        assert repo.exists('expression', 'g1') is True
        assert repo.get('expression', 'g1').spec == 'expression : term'
        assert len(repo.list()) == 1
        assert path.read_bytes() == before

    # * test: replace_and_delete_alternative
    def test_replace_and_delete_alternative(self, test_ctx, session, write_yaml):
        '''
        Replace one alternative in place, and delete only the named specification.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Replace the first arithmetic spec even though the update uses another spec.
        path = write_yaml(_seeded_alternatives())
        repo = test_ctx.make_target(config_file=str(path))
        updated = _production(
            'expression',
            'arithmetic',
            'expression : factor',
            action='p[0] = p[1]',
        )
        assert repo.replace(
            'expression',
            'arithmetic',
            'expression : expression PLUS term',
            updated,
        ) is None
        repo = test_ctx.make_target(config_file=str(path))
        listed = repo.list()
        assert [(item.name, item.grammar_id, item.spec) for item in listed] == [
            ('expression', 'arithmetic', 'expression : factor'),
            ('expression', 'arithmetic', 'expression : term'),
            ('expression', 'other', 'expression : NAME'),
        ]
        assert listed[0].action == 'p[0] = p[1]'

        # An absent old spec does not append and does not rewrite the file.
        absent_path = write_yaml(_seeded_alternatives(), name='absent.yml')
        absent_before = absent_path.read_bytes()
        repo = test_ctx.make_target(config_file=str(absent_path))
        repo.replace(
            'expression',
            'arithmetic',
            'expression : missing',
            updated,
        )
        assert absent_path.read_bytes() == absent_before
        repo = test_ctx.make_target(config_file=str(absent_path))
        assert len(repo.list()) == 3

        # Delete only the second arithmetic alternative. A repeat does not raise.
        delete_path = write_yaml(_seeded_alternatives(), name='alternative.yml')
        repo = test_ctx.make_target(config_file=str(delete_path))
        assert repo.delete_alternative(
            'expression',
            'arithmetic',
            'expression : term',
        ) is None
        repo = test_ctx.make_target(config_file=str(delete_path))
        assert [(item.name, item.grammar_id, item.spec) for item in repo.list()] == [
            ('expression', 'arithmetic', 'expression : expression PLUS term'),
            ('expression', 'other', 'expression : NAME'),
        ]
        assert repo.delete_alternative(
            'expression',
            'arithmetic',
            'expression : term',
        ) is None
        repo = test_ctx.make_target(config_file=str(delete_path))
        assert [(item.name, item.grammar_id, item.spec) for item in repo.list()] == [
            ('expression', 'arithmetic', 'expression : expression PLUS term'),
            ('expression', 'other', 'expression : NAME'),
        ]
