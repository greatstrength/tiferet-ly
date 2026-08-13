"""Tiferet-Ly Grammar Configuration Repository"""

# *** imports

# ** core
from typing import List, Optional

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
    The grammar configuration repository.

    Operates against a ``grammars:`` root node shaped as a flat, id-keyed
    mapping, mirroring ErrorConfigRepository.
    '''

    # * init
    def __init__(self, grammar_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the grammar configuration repository.

        :param grammar_config: Path to the configuration file.
        :type grammar_config: str
        :param encoding: File encoding.
        :type encoding: str
        '''

        # Initialize the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=grammar_config,
            encoding=encoding,
        )

    # * method: exists
    def exists(self, id: str) -> bool:
        '''
        Check whether a grammar with the given ID exists.

        :param id: The grammar identifier.
        :type id: str
        :return: True if the grammar exists, otherwise False.
        :rtype: bool
        '''

        # Load the grammars mapping from the configuration file.
        grammars_data = self._load(
            start_node=lambda data: data.get('grammars', {})
        )

        # Return whether the grammar id exists in the mapping.
        return id in grammars_data

    # * method: get
    def get(self, id: str) -> Optional[GrammarAggregate]:
        '''
        Retrieve a Grammar by its ID.

        :param id: The grammar identifier.
        :type id: str
        :return: The GrammarAggregate, or None if not found.
        :rtype: Optional[GrammarAggregate]
        '''

        # Load the specific grammar entry from the configuration file.
        grammar_data = self._load(
            start_node=lambda data: data.get('grammars', {}).get(id)
        )

        # Return None when absent.
        if not grammar_data:
            return None

        # Map the data to a GrammarAggregate and return it.
        return GrammarConfigObject.model_validate({
            **grammar_data,
            'id': id,
        }).map()

    # * method: list
    def list(self) -> List[GrammarAggregate]:
        '''
        List all Grammar aggregates.

        :return: All stored grammars.
        :rtype: List[GrammarAggregate]
        '''

        # Load all grammars data from the configuration file.
        grammars_data = self._load(
            start_node=lambda data: data.get('grammars', {})
        )

        # Map each grammar entry to a GrammarAggregate.
        return [
            GrammarConfigObject.model_validate({
                **grammar_data,
                'id': grammar_id,
            }).map()
            for grammar_id, grammar_data in grammars_data.items()
        ]

    # * method: save
    def save(self, grammar: GrammarAggregate) -> None:
        '''
        Persist a Grammar aggregate.

        :param grammar: The grammar aggregate to persist.
        :type grammar: GrammarAggregate
        :return: None
        :rtype: None
        '''

        # Convert the grammar model to configuration data.
        grammar_data = GrammarConfigObject.from_model(grammar)

        # Load the full configuration file.
        full_data = self._load()

        # Update or insert the grammar entry.
        full_data.setdefault('grammars', {})[grammar.id] = grammar_data.to_primitive(
            self.default_role
        )

        # Persist the updated configuration file.
        self._save(full_data)

    # * method: delete
    def delete(self, id: str) -> None:
        '''
        Delete a Grammar by ID. Idempotent.

        :param id: The grammar identifier.
        :type id: str
        :return: None
        :rtype: None
        '''

        # Load the full configuration file.
        full_data = self._load()

        # Remove the grammar entry if it exists (idempotent).
        full_data.get('grammars', {}).pop(id, None)

        # Persist the updated configuration file.
        self._save(full_data)
