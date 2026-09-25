"""Tiferet Ly Grammar Configuration Repository"""

# *** imports

# ** app
from tiferet.repos.core import ConfigurationRepository
from ..interfaces.grammar import GrammarService
from ..mappers.grammar import (
    GrammarAggregate,
    GrammarConfigObject,
)

# *** repos

# ** repo: grammar_config_repository
class GrammarConfigRepository(GrammarService, ConfigurationRepository):
    '''
    Persist a lean grammar as one id-keyed grammars mapping.

    The body stores ordered parent identifiers and a start name. Saving does
    not check that parents exist, that the graph is acyclic, or that the
    start name is a production.
    '''

    # * init
    def __init__(self, grammar_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the grammar configuration repository.

        :param grammar_config: The configuration file path.
        :type grammar_config: str
        :param encoding: The file encoding.
        :type encoding: str
        '''

        # Forward the grammar file to the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=grammar_config,
            encoding=encoding,
        )

    # * method: _load_grammars
    def _load_grammars(self) -> dict:
        '''
        Load the grammars mapping without writing the file.

        A missing or empty node is an empty mapping.

        :return: The grammars mapping.
        :rtype: dict
        '''

        # Read only the grammars node. A missing node is an empty mapping.
        loaded = self._load(
            start_node=lambda data: data.get('grammars') or {},
        )
        if not loaded:
            return {}

        # Copy the mapping so callers can scan without mutating the load.
        return dict(loaded)

    # * method: _grammar_body
    def _grammar_body(self, grammar: GrammarAggregate) -> dict:
        '''
        Build the write body for a grammar aggregate.

        The body key order is parent identifiers, then start. The identifier
        stays the mapping key and is not written into the body.

        :param grammar: The grammar aggregate to persist.
        :type grammar: GrammarAggregate
        :return: The grammar body.
        :rtype: dict
        '''

        # Serialize through the consumed mapper role. Do not catch failures.
        primitive = GrammarConfigObject.from_model(grammar).to_primitive(
            self.default_role,
        )

        # Keep only the lean body, in the required key order.
        return {
            'parent_ids': list(primitive['parent_ids']),
            'start': primitive['start'],
        }

    # * method: exists
    def exists(self, id: str) -> bool:
        '''
        Report whether that grammar identifier is a key in grammars.

        :param id: The grammar identifier.
        :type id: str
        :return: True when that key is stored, otherwise False.
        :rtype: bool
        '''

        # A missing grammars node is an empty mapping. Do not write the file.
        return id in self._load_grammars()

    # * method: get
    def get(self, id: str) -> GrammarAggregate | None:
        '''
        Return the grammar for that key, or None.

        :param id: The grammar identifier.
        :type id: str
        :return: The stored grammar aggregate, or None.
        :rtype: GrammarAggregate | None
        '''

        # Absence returns None. Do not write the file or catch mapper failures.
        grammars = self._load_grammars()
        if id not in grammars:
            return None

        # Inject the mapping key, then map the lean body.
        return GrammarConfigObject.model_validate({
            **grammars[id],
            'id': id,
        }).map()

    # * method: list
    def list(self) -> list[GrammarAggregate]:
        '''
        Return every stored grammar once.

        File-position order is not a requirement.

        :return: The stored grammar aggregates.
        :rtype: list[GrammarAggregate]
        '''

        # Map every key once. A mapping cannot store the same id twice.
        return [
            GrammarConfigObject.model_validate({**body, 'id': grammar_id}).map()
            for grammar_id, body in self._load_grammars().items()
        ]

    # * method: save
    def save(self, grammar: GrammarAggregate) -> None:
        '''
        Insert or replace the entry whose key is the grammar identifier.

        :param grammar: The grammar aggregate to persist.
        :type grammar: GrammarAggregate
        :return: None
        :rtype: None
        '''

        # Build the lean body. Do not read tokens or production rules.
        body = self._grammar_body(grammar)

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        grammars = dict(full_data.get('grammars') or {})

        # Replace that one key. A mapping cannot append a second copy.
        grammars[grammar.id] = body
        full_data['grammars'] = grammars

        # Persist only the updated grammars value.
        self._save(full_data)

    # * method: delete
    def delete(self, id: str) -> None:
        '''
        Remove that grammar key. Absence does not raise.

        :param id: The grammar identifier.
        :type id: str
        :return: None
        :rtype: None
        '''

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        grammars = dict(full_data.get('grammars') or {})

        # Remove the key when present. A missing key is not an error.
        grammars.pop(id, None)
        full_data['grammars'] = grammars

        # Persist the grammars mapping, including an empty mapping.
        self._save(full_data)
