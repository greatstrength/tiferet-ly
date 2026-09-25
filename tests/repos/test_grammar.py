"""Tiferet Ly Grammar Repository Tests"""

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
from tiferet_ly.interfaces import grammar as grammar_interface
from tiferet_ly.interfaces.grammar import GrammarService
from tiferet_ly.mappers.grammar import (
    GrammarAggregate,
    GrammarConfigObject,
)
from tiferet_ly.repos import grammar as grammar_repo
from tiferet_ly.repos.grammar import GrammarConfigRepository

# *** constants

# ** constant: forbidden_body_keys
_FORBIDDEN_BODY_KEYS = (
    'token_rules',
    'production_rules',
    'subgrammars',
    'subgrammar',
    'precedence',
    'associativity',
)

# *** functions

# ** function: grammar_aggregate
def _grammar(id: str, parent_ids: list[str], start: str) -> GrammarAggregate:
    '''
    Build a grammar aggregate through the consumed config object.

    :param id: The grammar identifier.
    :type id: str
    :param parent_ids: The ordered parent identifiers.
    :type parent_ids: list[str]
    :param start: The declared start-production name.
    :type start: str
    :return: The mapped grammar aggregate.
    :rtype: GrammarAggregate
    '''

    # Tests construct aggregates only through model_validate().map().
    return GrammarConfigObject.model_validate({
        'id': id,
        'parent_ids': parent_ids,
        'start': start,
    }).map()

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

# ** function: seeded_grammars
def _seeded_grammars() -> dict:
    '''
    Return the two-grammar document used by the id-keyed helpers.

    :return: A document whose grammars mapping holds both seeded identifiers.
    :rtype: dict
    '''

    # Identity is the mapping key. The body is parents, then start.
    return {
        'grammars': {
            'arithmetic': {
                'parent_ids': [],
                'start': 'expression',
            },
            'arithmetic_with_names': {
                'parent_ids': ['arithmetic', 'names'],
                'start': 'expression',
            },
        },
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

    def write(document: dict, name: str = 'grammars.yml') -> Path:
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

# *** tests

# ** test: test_module_imports
def test_test_module_imports():
    '''
    Import no PLY module from the grammar repository tests.
    '''

    # This module proves the repository without importing PLY.
    for module in _imported_modules(ast.parse(Path(__file__).read_text())):
        assert module != 'ply' and not module.startswith('ply.')

# *** testers

# ** tester: test_grammar_config_repository
@use_tester(
    type='repo',
    target_cls=GrammarConfigRepository,
    config_parameter='grammar_config',
    aggregate_cls=GrammarAggregate,
    equality_fields=['id', 'parent_ids', 'start'],
    exists_cases=[
        ('arithmetic', True),
        ('missing', False),
    ],
    get_cases=[
        ('arithmetic', {
            'id': 'arithmetic',
            'parent_ids': [],
            'start': 'expression',
        }),
        ('missing', None),
    ],
    list_ids=[
        'arithmetic',
        'arithmetic_with_names',
    ],
    delete_ids=[
        'arithmetic_with_names',
    ],
)
class TestGrammarConfigRepository:
    '''
    Temporary-file tests for the grammar configuration repository.
    '''

    # * test: contract
    def test_contract(self, test_ctx, session, write_yaml):
        '''
        Keep the grammar service and repository on the published contract.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # The service is abstract and exposes exactly five operations.
        assert issubclass(GrammarService, Service)
        assert GrammarService.__abstractmethods__ == frozenset({
            'exists',
            'get',
            'list',
            'save',
            'delete',
        })

        # Single-id operations take one identifier. list takes neither.
        for name in ('exists', 'get', 'delete'):
            parameters = inspect.signature(getattr(GrammarService, name)).parameters
            assert list(parameters) == ['self', 'id']
            assert parameters['id'].annotation is str
        assert list(inspect.signature(GrammarService.list).parameters) == ['self']
        assert list(inspect.signature(GrammarService.save).parameters) == ['self', 'grammar']
        assert inspect.signature(GrammarService.save).parameters['grammar'].annotation is GrammarAggregate

        # Return annotations match the published id-keyed contract.
        assert inspect.signature(GrammarService.exists).return_annotation is bool
        assert inspect.signature(GrammarService.get).return_annotation == GrammarAggregate | None
        assert inspect.signature(GrammarService.list).return_annotation == list[GrammarAggregate]
        assert inspect.signature(GrammarService.save).return_annotation is None
        assert inspect.signature(GrammarService.delete).return_annotation is None

        # The repository subclasses both bases and does not override the role.
        assert issubclass(GrammarConfigRepository, GrammarService)
        assert issubclass(GrammarConfigRepository, ConfigurationRepository)
        assert 'default_role' not in GrammarConfigRepository.__dict__
        assert not hasattr(GrammarConfigRepository, '_unwrap_named_entries')
        assert not hasattr(GrammarConfigRepository, '_wrap_named_entries')
        init = inspect.signature(GrammarConfigRepository.__init__)
        assert list(init.parameters) == ['self', 'grammar_config', 'encoding']
        assert init.parameters['grammar_config'].annotation is str
        assert init.parameters['encoding'].default == 'utf-8'
        assert init.parameters['encoding'].annotation is str

        # The single-id helpers are bound to the seeded grammar cases.
        assert test_ctx.domain.exists_cases == [
            ('arithmetic', True),
            ('missing', False),
        ]
        assert test_ctx.domain.list_ids == [
            'arithmetic',
            'arithmetic_with_names',
        ]
        assert test_ctx.domain.delete_ids == ['arithmetic_with_names']
        assert test_ctx.domain.equality_fields == ['id', 'parent_ids', 'start']

        # Package markers export nothing and do not import these classes.
        interfaces_marker = Path(grammar_interface.__file__).parent / '__init__.py'
        repos_marker = Path(grammar_repo.__file__).parent / '__init__.py'
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
        assert 'GrammarService' not in interfaces_marker.read_text(encoding='utf-8')
        assert 'GrammarConfigRepository' not in repos_marker.read_text(encoding='utf-8')

        # The repository module imports none of the forbidden packages.
        repo_tree = ast.parse(Path(grammar_repo.__file__).read_text(encoding='utf-8'))
        imported = _imported_modules(repo_tree)
        forbidden = (
            'tiferet_ly.domain',
            'tiferet_ly.events',
            'tiferet_ly.utils',
            'tiferet_ly.repos.token',
            'tiferet_ly.repos.production',
            'ply',
        )
        for module in imported:
            assert module not in forbidden
            assert not module.startswith('ply.')
            assert not module.startswith('tiferet_ly.domain')
            assert not module.startswith('tiferet_ly.events')
            assert not module.startswith('tiferet_ly.utils')
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
        assert isinstance(repo, GrammarConfigRepository)
        assert repo.default_role == 'to_data'

    # * test: id_keyed_helpers
    def test_id_keyed_helpers(self, test_ctx, session, write_yaml):
        '''
        Exercise the single-id helpers against the seeded grammars mapping.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed both identifiers in a real YAML file.
        path = write_yaml(_seeded_grammars())
        repo = test_ctx.make_target(config_file=str(path))

        # Exists, get, and list use the published id-keyed cases.
        test_ctx.assert_exists(repo)
        test_ctx.assert_get(repo)
        test_ctx.assert_list(repo)

        # Delete removes arithmetic_with_names and a second delete does not raise.
        test_ctx.assert_delete(repo)
        assert repo.get('arithmetic_with_names') is None
        assert repo.get('arithmetic').start == 'expression'

    # * test: missing_grammars_node
    def test_missing_grammars_node(self, test_ctx, session, write_yaml):
        '''
        Treat a missing grammars node as empty, and do not raise on delete.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed a document that has no grammars node.
        path = write_yaml({'kept': {'start': 'expression'}})
        before = path.read_bytes()
        repo = test_ctx.make_target(config_file=str(path))

        # Reads report absence and do not change the file.
        assert repo.exists('arithmetic') is False
        assert repo.get('arithmetic') is None
        assert repo.list() == []
        assert path.read_bytes() == before

        # Delete of an absent key does not raise and leaves the other root.
        assert repo.delete('arithmetic') is None
        parsed = _parsed(path)
        assert parsed['kept'] == {'start': 'expression'}
        reloaded = test_ctx.make_target(config_file=str(path))
        assert reloaded.exists('arithmetic') is False
        assert reloaded.get('arithmetic') is None
        assert reloaded.list() == []

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

        # Seed one grammar, then snapshot the bytes the repository wrote.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_grammar('arithmetic', [], 'expression'))
        before = path.read_bytes()
        parsed_before = _parsed(path)
        repo = test_ctx.make_target(config_file=str(path))

        # Reads do not call save.
        assert repo.exists('arithmetic') is True
        assert repo.get('arithmetic').start == 'expression'
        assert len(repo.list()) == 1
        assert path.read_bytes() == before
        assert _parsed(path) == parsed_before

    # * test: save_body_shape
    def test_save_body_shape(self, test_ctx, session, write_yaml):
        '''
        Persist lean bodies whose keys are parent identifiers, then start.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save the root grammar, then the grammar that composes it.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.save(_grammar('arithmetic', [], 'expression')) is None
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.save(_grammar(
            'arithmetic_with_names',
            ['arithmetic', 'names'],
            'expression',
        )) is None

        # Neither body contains the identifier or a retired catalogue field.
        bodies = _parsed(path)['grammars']
        assert bodies['arithmetic'] == {
            'parent_ids': [],
            'start': 'expression',
        }
        assert bodies['arithmetic_with_names'] == {
            'parent_ids': ['arithmetic', 'names'],
            'start': 'expression',
        }
        assert list(bodies['arithmetic']) == ['parent_ids', 'start']
        assert list(bodies['arithmetic_with_names']) == ['parent_ids', 'start']
        for body in bodies.values():
            assert 'id' not in body
            for key in _FORBIDDEN_BODY_KEYS:
                assert key not in body

        # Reloaded parents keep the saved sequence.
        repo = test_ctx.make_target(config_file=str(path))
        reloaded = repo.get('arithmetic_with_names')
        assert reloaded.parent_ids == ['arithmetic', 'names']
        assert reloaded.parent_ids == bodies['arithmetic_with_names']['parent_ids']

    # * test: missing_delete_and_replace
    def test_missing_delete_and_replace(self, test_ctx, session, write_yaml):
        '''
        Return None for a missing key, delete idempotently, and replace in place.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save both seeded grammars, reloading after each write.
        path = write_yaml({})
        for grammar in (
            _grammar('arithmetic', [], 'expression'),
            _grammar('arithmetic_with_names', ['arithmetic', 'names'], 'expression'),
        ):
            repo = test_ctx.make_target(config_file=str(path))
            repo.save(grammar)

        # A missing key is absent, and deleting it does not raise.
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.get('missing') is None
        assert repo.delete('missing') is None

        # The first delete removes the key. The second delete does not raise.
        assert repo.delete('arithmetic_with_names') is None
        assert repo.delete('arithmetic_with_names') is None
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.get('arithmetic_with_names') is None
        assert repo.exists('arithmetic') is True

        # Saving an existing id replaces that entry and does not append.
        repo.save(_grammar('arithmetic', ['names'], 'term'))
        repo = test_ctx.make_target(config_file=str(path))
        replaced = repo.get('arithmetic')
        assert replaced.parent_ids == ['names']
        assert replaced.start == 'term'
        parsed = _parsed(path)
        assert list(parsed['grammars']) == ['arithmetic']
        assert parsed['grammars']['arithmetic'] == {
            'parent_ids': ['names'],
            'start': 'term',
        }
        listed_ids = [item.id for item in repo.list()]
        assert listed_ids == ['arithmetic']
        assert set(listed_ids) == set(parsed['grammars'])

    # * test: list_ids_match_keys
    def test_list_ids_match_keys(self, test_ctx, session, write_yaml):
        '''
        Return each stored identifier once, matching the grammars keys.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed both identifiers, then list through a new repository.
        path = write_yaml(_seeded_grammars())
        repo = test_ctx.make_target(config_file=str(path))
        listed_ids = [item.id for item in repo.list()]

        # The set of identifiers equals the mapping keys. Order is not required.
        assert len(listed_ids) == len(set(listed_ids))
        assert set(listed_ids) == set(_parsed(path)['grammars'])
        assert set(listed_ids) == {'arithmetic', 'arithmetic_with_names'}

    # * test: unresolved_values_persist
    def test_unresolved_values_persist(self, test_ctx, session, write_yaml):
        '''
        Persist an empty parent list, a missing parent, a self-parent, and a bad start.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # None of these values is checked against another aggregate.
        path = write_yaml({'grammars': {}})
        saves = (
            _grammar('root', [], 'expression'),
            _grammar('orphan-parent', ['missing-parent'], 'expression'),
            _grammar('self-parent', ['self-parent'], 'expression'),
            _grammar('bad-start', [], 'no-such-production'),
        )
        for grammar in saves:
            repo = test_ctx.make_target(config_file=str(path))
            assert repo.save(grammar) is None

        # Each reloaded grammar returns the same field values.
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.get('root').parent_ids == []
        assert repo.get('root').start == 'expression'
        assert repo.get('orphan-parent').parent_ids == ['missing-parent']
        assert repo.get('self-parent').parent_ids == ['self-parent']
        assert repo.get('bad-start').start == 'no-such-production'
        assert repo.get('bad-start').parent_ids == []

    # * test: save_leaves_other_roots
    def test_save_leaves_other_roots(self, test_ctx, session, write_yaml):
        '''
        Leave tokens and production rules unchanged when saving a grammar.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed the neighbouring catalogues and an empty grammars mapping.
        document = {
            'tokens': [
                {
                    'PLUS': {
                        'grammar_id': 'arithmetic',
                        'pattern': 'plus',
                    },
                },
            ],
            'production_rules': [
                {
                    'expression': {
                        'grammar_id': 'arithmetic',
                        'spec': 'expression : term',
                    },
                },
            ],
            'grammars': {},
        }
        path = write_yaml(document)
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_grammar('arithmetic', [], 'expression'))

        # Only grammars changes.
        parsed = _parsed(path)
        assert parsed['tokens'] == document['tokens']
        assert parsed['production_rules'] == document['production_rules']
        assert parsed['grammars'] == {
            'arithmetic': {
                'parent_ids': [],
                'start': 'expression',
            },
        }
        for key in _FORBIDDEN_BODY_KEYS:
            assert key not in parsed['grammars']['arithmetic']
