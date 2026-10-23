"""Tiferet Ly Grammar Configuration Repository"""

# *** imports

# ** infra
from tiferet.repos.core import ConfigurationRepository

# ** app
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

    The body stores ordered parent identifiers, a start name, and an
    optional ignore pattern. Saving does not copy ignore from parent_ids,
    and it does not check that parents exist, that the graph is acyclic,
    or that the start name is a production. A declared layout profile is
    stored on that grammar alone. It is not copied from parent_ids.
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

        The body key order is parent identifiers, then start, then ignore
        when that value is a string. The identifier stays the mapping key.
        A missing or null ignore is omitted. A layout profile, when present,
        is the last key; a missing profile is omitted rather than written
        as null.

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
        body = {
            'parent_ids': list(primitive['parent_ids']),
            'start': primitive['start'],
        }

        # Write ignore after start, only when it is a string. An empty string is written.
        ignore = primitive.get('ignore')
        if isinstance(ignore, str):
            body['ignore'] = ignore

        # Omit a missing or null profile. Do not write null.
        layout = primitive.get('layout')
        if layout is None:
            return body

        # Write the profile last, in the declared key order, with copied lists.
        profile = {
            'block_tokens': list(layout.get('block_tokens', [])),
            'open_delimiters': list(layout.get('open_delimiters', [])),
            'close_delimiters': list(layout.get('close_delimiters', [])),
        }

        # Write the newline token only when it is declared.
        if layout.get('newline_token') is not None:
            profile['newline_token'] = layout['newline_token']

        # Keep False and 0 as given. Required names have no default.
        profile['suppress_newline_in_delimiters'] = layout.get('suppress_newline_in_delimiters', True)
        profile['indent_token'] = layout['indent_token']
        profile['dedent_token'] = layout['dedent_token']
        profile['tab_size'] = layout.get('tab_size', 4)
        body['layout'] = profile
        return body

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
