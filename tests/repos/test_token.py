"""Tiferet Ly Token Repository Tests"""

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
from tiferet_ly.interfaces import token as token_interface
from tiferet_ly.interfaces.token import TokenService
from tiferet_ly.mappers.token import (
    TokenRuleAggregate,
    TokenRuleConfigObject,
)
from tiferet_ly.repos import token as token_repo
from tiferet_ly.repos.token import TokenConfigRepository

# *** functions

# ** function: token_aggregate
def _token(
        name: str,
        grammar_id: str,
        pattern: str,
        action: str | None = None,
    ):
    '''
    Build a token aggregate through the consumed config object.

    :param name: The declared token name.
    :type name: str
    :param grammar_id: The grammar that owns the token.
    :type grammar_id: str
    :param pattern: The declared token pattern.
    :type pattern: str
    :param action: Optional action source.
    :type action: str | None
    :return: The mapped token aggregate.
    :rtype: SimpleTokenRuleAggregate | ComplexTokenRuleAggregate
    '''

    # Tests construct aggregates only through model_validate().map().
    data = {
        'name': name,
        'grammar_id': grammar_id,
        'pattern': pattern,
    }
    if action is not None:
        data['action'] = action
    return TokenRuleConfigObject.model_validate(data).map()

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

    def write(document: dict, name: str = 'tokens.yml') -> Path:
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

# ** tester: test_token_config_repository
@use_tester(
    type='repo',
    target_cls=TokenConfigRepository,
    config_parameter='token_config',
    exists_cases=[],
    get_cases=[],
    list_ids=[],
    delete_ids=[],
)
class TestTokenConfigRepository:
    '''
    Temporary-file tests for the token configuration repository.
    '''

    # * test: contract
    def test_contract(self, test_ctx, session, write_yaml):
        '''
        Keep the token service and repository on the published contract.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # The service is abstract and exposes exactly five operations.
        assert issubclass(TokenService, Service)
        assert TokenService.__abstractmethods__ == frozenset({
            'exists',
            'get',
            'list',
            'save',
            'delete',
        })

        # Pair operations take name and grammar id. list takes neither.
        for name in ('exists', 'get', 'delete'):
            parameters = inspect.signature(getattr(TokenService, name)).parameters
            assert list(parameters) == ['self', 'name', 'grammar_id']
            assert parameters['name'].annotation is str
            assert parameters['grammar_id'].annotation is str
        assert list(inspect.signature(TokenService.list).parameters) == ['self']
        assert list(inspect.signature(TokenService.save).parameters) == ['self', 'token']
        assert inspect.signature(TokenService.save).parameters['token'].annotation is TokenRuleAggregate

        # Return annotations match the published pair contract.
        assert inspect.signature(TokenService.exists).return_annotation is bool
        assert inspect.signature(TokenService.get).return_annotation == TokenRuleAggregate | None
        assert inspect.signature(TokenService.list).return_annotation == list[TokenRuleAggregate]
        assert inspect.signature(TokenService.save).return_annotation is None
        assert inspect.signature(TokenService.delete).return_annotation is None

        # The repository subclasses both bases and does not override the role.
        assert issubclass(TokenConfigRepository, TokenService)
        assert issubclass(TokenConfigRepository, ConfigurationRepository)
        assert 'default_role' not in TokenConfigRepository.__dict__
        init = inspect.signature(TokenConfigRepository.__init__)
        assert list(init.parameters) == ['self', 'token_config', 'encoding']
        assert init.parameters['token_config'].annotation is str
        assert init.parameters['encoding'].default == 'utf-8'
        assert init.parameters['encoding'].annotation is str

        # Both reshape methods exist. The single-id case lists stay empty.
        assert callable(TokenConfigRepository._unwrap_named_entries)
        assert callable(TokenConfigRepository._wrap_named_entries)
        assert test_ctx.domain.exists_cases == []
        assert test_ctx.domain.get_cases == []
        assert test_ctx.domain.list_ids == []
        assert test_ctx.domain.delete_ids == []

        # Package markers export nothing and do not import these classes.
        interfaces_marker = Path(token_interface.__file__).parent / '__init__.py'
        repos_marker = Path(token_repo.__file__).parent / '__init__.py'
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
        assert 'TokenService' not in interfaces_marker.read_text(encoding='utf-8')
        assert 'TokenConfigRepository' not in repos_marker.read_text(encoding='utf-8')

        # The repository module imports none of the forbidden packages.
        repo_tree = ast.parse(Path(token_repo.__file__).read_text(encoding='utf-8'))
        imported = _imported_modules(repo_tree)
        forbidden = (
            'tiferet_ly.domain',
            'tiferet_ly.events',
            'tiferet_ly.utils',
            'tiferet_ly.repos.production',
            'tiferet_ly.repos.grammar',
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
        assert isinstance(repo, TokenConfigRepository)
        assert repo.default_role == 'to_data'

    # * test: missing_tokens_node
    def test_missing_tokens_node(self, test_ctx, session, write_yaml):
        '''
        Treat a missing tokens node as empty, and do not write on reads.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed a document that has no tokens node.
        path = write_yaml({'grammars': {'kept': {'start': 'expression'}}})
        before = path.read_bytes()
        repo = test_ctx.make_target(config_file=str(path))

        # Reads report absence and do not change the file.
        assert repo.exists('PLUS', 'g1') is False
        assert repo.get('PLUS', 'g1') is None
        assert repo.list() == []
        assert path.read_bytes() == before

        # Delete of an absent pair does not raise.
        repo.delete('PLUS', 'g1')
        reloaded = test_ctx.make_target(config_file=str(path))
        assert reloaded.exists('PLUS', 'g1') is False
        assert reloaded.get('PLUS', 'g1') is None
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
            {'PLUS': {'grammar_id': 'g1', 'pattern': 'plus'}},
        ])

        # The mapping key becomes name. The body's grammar id is kept.
        assert unwrapped[0]['name'] == 'PLUS'
        assert unwrapped[0]['grammar_id'] == 'g1'
        assert unwrapped[0]['pattern'] == 'plus'

        # A body without grammar_id does not gain one.
        bare = repo._unwrap_named_entries([
            {'PLUS': {'pattern': 'plus'}},
        ])
        assert bare == [{'name': 'PLUS', 'pattern': 'plus'}]
        assert 'grammar_id' not in bare[0]

    # * test: same_name_different_grammar
    def test_same_name_different_grammar(self, test_ctx, session, write_yaml):
        '''
        Persist the same token name under two grammars, including one action.

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
        assert repo.save(_token('PLUS', 'g1', 'plus')) is None
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.save(_token('PLUS', 'g2', 'other', action='return t')) is None

        # A new repository reads both pairs without collapsing the name.
        repo = test_ctx.make_target(config_file=str(path))
        simple = repo.get('PLUS', 'g1')
        complex_rule = repo.get('PLUS', 'g2')
        assert simple.pattern == 'plus'
        assert not hasattr(simple, 'action')
        assert complex_rule.pattern == 'other'
        assert complex_rule.action == 'return t'
        listed = repo.list()
        assert [(item.name, item.grammar_id) for item in listed] == [
            ('PLUS', 'g1'),
            ('PLUS', 'g2'),
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

        # Save three tokens in an order that is not grouped by grammar id.
        path = write_yaml({})
        saves = (
            _token('ZED', 'zeta', 'z'),
            _token('ALPHA', 'alpha', 'a', action='return t'),
            _token('MID', 'zeta', 'm'),
        )
        for token in saves:
            repo = test_ctx.make_target(config_file=str(path))
            repo.save(token)

        # A new repository returns that order, and the file matches it.
        repo = test_ctx.make_target(config_file=str(path))
        listed = repo.list()
        assert [(item.name, item.grammar_id, item.pattern) for item in listed] == [
            ('ZED', 'zeta', 'z'),
            ('ALPHA', 'alpha', 'a'),
            ('MID', 'zeta', 'm'),
        ]
        assert listed[1].action == 'return t'
        assert not hasattr(listed[0], 'action')
        assert _parsed(path) == {
            'tokens': [
                {'ZED': {'grammar_id': 'zeta', 'pattern': 'z'}},
                {
                    'ALPHA': {
                        'grammar_id': 'alpha',
                        'pattern': 'a',
                        'action': 'return t',
                    },
                },
                {'MID': {'grammar_id': 'zeta', 'pattern': 'm'}},
            ],
        }

    # * test: replace_in_place_and_delete
    def test_replace_in_place_and_delete(self, test_ctx, session, write_yaml):
        '''
        Replace one pair in place, then delete only that pair.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Save three distinct pairs, reloading after each write.
        path = write_yaml({})
        for token in (
            _token('ONE', 'g1', 'one'),
            _token('TWO', 'g1', 'two'),
            _token('THREE', 'g1', 'three'),
        ):
            repo = test_ctx.make_target(config_file=str(path))
            repo.save(token)

        # Updating TWO replaces the middle entry and does not append.
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_token('TWO', 'g1', 'two-updated'))
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.pattern) for item in repo.list()] == [
            ('ONE', 'one'),
            ('TWO', 'two-updated'),
            ('THREE', 'three'),
        ]
        assert len(_parsed(path)['tokens']) == 3

        # Delete removes only TWO. Absent and repeated deletes do not raise.
        repo = test_ctx.make_target(config_file=str(path))
        assert repo.delete('TWO', 'g1') is None
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.pattern) for item in repo.list()] == [
            ('ONE', 'one'),
            ('THREE', 'three'),
        ]
        assert repo.delete('ABSENT', 'g1') is None
        assert repo.delete('TWO', 'g1') is None
        repo = test_ctx.make_target(config_file=str(path))
        assert [(item.name, item.pattern) for item in repo.list()] == [
            ('ONE', 'one'),
            ('THREE', 'three'),
        ]

    # * test: unknown_grammar_persists
    def test_unknown_grammar_persists(self, test_ctx, session, write_yaml):
        '''
        Save a token whose grammar id is not a key in grammars.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # The grammars node has no missing-grammar key.
        path = write_yaml({'grammars': {'arithmetic': {'parent_ids': [], 'start': 'expression'}}})
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_token('ORPHAN', 'missing-grammar', 'x'))

        # Reload keeps the unresolved grammar id.
        repo = test_ctx.make_target(config_file=str(path))
        orphan = repo.get('ORPHAN', 'missing-grammar')
        assert orphan.grammar_id == 'missing-grammar'
        assert orphan.pattern == 'x'

    # * test: save_leaves_other_roots
    def test_save_leaves_other_roots(self, test_ctx, session, write_yaml):
        '''
        Leave grammars and production rules unchanged when saving a token.

        :param test_ctx: The bound repository tester context.
        :type test_ctx: RepoTesterContext
        :param session: A fresh test session.
        :type session: TestSessionContext
        :param write_yaml: Writer for a temporary YAML file.
        :type write_yaml: Callable
        '''

        # Seed the neighbouring catalogues and an empty tokens list.
        document = {
            'grammars': {
                'arithmetic': {
                    'parent_ids': [],
                    'start': 'expression',
                },
            },
            'production_rules': [
                {
                    'expression': {
                        'grammar_id': 'arithmetic',
                        'spec': 'expression : term',
                    },
                },
            ],
            'tokens': [],
        }
        path = write_yaml(document)
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_token('PLUS', 'arithmetic', 'plus'))

        # Only tokens changes.
        parsed = _parsed(path)
        assert parsed['grammars'] == document['grammars']
        assert parsed['production_rules'] == document['production_rules']
        assert parsed['tokens'] == [
            {'PLUS': {'grammar_id': 'arithmetic', 'pattern': 'plus'}},
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

        # Seed one token, then snapshot the bytes the repository wrote.
        path = write_yaml({})
        repo = test_ctx.make_target(config_file=str(path))
        repo.save(_token('PLUS', 'g1', 'plus'))
        before = path.read_bytes()
        repo = test_ctx.make_target(config_file=str(path))

        # Reads do not call save.
        assert repo.exists('PLUS', 'g1') is True
        assert repo.get('PLUS', 'g1').pattern == 'plus'
        assert len(repo.list()) == 1
        assert path.read_bytes() == before
