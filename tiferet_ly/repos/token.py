"""Tiferet-Ly Token Configuration Repository"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional, Union

# ** app
from tiferet.repos.core import ConfigurationRepository
from ..interfaces.token import TokenService
from ..mappers.core import (
    expand_keyed_entries,
    wrap_keyed_entries,
)
from ..mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
    TokenRuleConfigObject,
)

# *** repos

# ** repo: token_config_repository
class TokenConfigRepository(TokenService, ConfigurationRepository):
    '''
    The token rule configuration repository.

    Operates against a ``tokens:`` root node shaped as a sequence of
    single-key mappings. Lookup is a linear scan on the composite key
    ``(name, grammar_id)``.
    '''

    # * init
    def __init__(self, token_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the token configuration repository.

        :param token_config: Path to the configuration file.
        :type token_config: str
        :param encoding: File encoding.
        :type encoding: str
        '''

        # Initialize the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=token_config,
            encoding=encoding,
        )

    # * method: _load_entries
    def _load_entries(self) -> List[Dict[str, Any]]:
        '''
        Load and expand the tokens: sequence into flat dict entries.

        :return: The expanded token rule entries in declared order.
        :rtype: List[Dict[str, Any]]
        '''

        # Load the raw tokens sequence and expand single-key mappings.
        return self._load(
            start_node=lambda data: data.get('tokens', []) or [],
            data_factory=lambda entries: expand_keyed_entries(entries, key_field='name'),
        )

    # * method: _find_index
    def _find_index(self, entries: List[Dict[str, Any]], name: str, grammar_id: str) -> Optional[int]:
        '''
        Find the list index of a token entry matching name and grammar_id.

        :param entries: The expanded token entries.
        :type entries: List[Dict[str, Any]]
        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The matching index, or None if not found.
        :rtype: Optional[int]
        '''

        # Scan for the first matching composite key.
        for index, entry in enumerate(entries):
            if entry.get('name') == name and entry.get('grammar_id') == grammar_id:
                return index

        # No match.
        return None

    # * method: exists
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Check whether a token rule with the given name and grammar_id exists.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: True if the token rule exists, otherwise False.
        :rtype: bool
        '''

        # Load expanded entries and scan for the composite key.
        entries = self._load_entries()
        return self._find_index(entries, name, grammar_id) is not None

    # * method: get
    def get(self, name: str, grammar_id: str) -> Optional[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]:
        '''
        Retrieve a token rule aggregate by name and grammar_id.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The token rule aggregate, or None if not found.
        :rtype: Optional[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]
        '''

        # Load expanded entries and locate the composite key.
        entries = self._load_entries()
        index = self._find_index(entries, name, grammar_id)

        # Return None when absent.
        if index is None:
            return None

        # Map the matching entry to a token rule aggregate.
        return TokenRuleConfigObject.model_validate(entries[index]).map()

    # * method: list
    def list(self) -> List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]:
        '''
        List every token rule aggregate unfiltered, in declared order.

        :return: All stored token rule aggregates.
        :rtype: List[Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]]
        '''

        # Load expanded entries and map each to a token rule aggregate.
        entries = self._load_entries()
        return [
            TokenRuleConfigObject.model_validate(entry).map()
            for entry in entries
        ]

    # * method: save
    def save(self, token: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]) -> None:
        '''
        Persist a token rule aggregate.

        Replaces an existing ``(name, grammar_id)`` entry in its original
        list position; otherwise appends at the end.

        :param token: The token rule aggregate to persist.
        :type token: Union[SimpleTokenRuleAggregate, ComplexTokenRuleAggregate]
        :return: None
        :rtype: None
        '''

        # Convert the aggregate to a flat config dict.
        token_data = TokenRuleConfigObject.from_model(token).to_primitive(
            self.default_role,
            exclude=set(),
        )

        # Load the full configuration file and expand the tokens sequence.
        full_data = self._load()
        entries = expand_keyed_entries(
            full_data.get('tokens', []) or [],
            key_field='name',
        )

        # Replace in place when the composite key already exists.
        index = self._find_index(entries, token.name, token.grammar_id)
        if index is not None:
            entries[index] = token_data
        else:
            entries.append(token_data)

        # Re-wrap and persist the updated configuration.
        full_data['tokens'] = wrap_keyed_entries(entries, key_field='name')
        self._save(full_data)

    # * method: delete
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Delete a token rule by name and grammar_id. Idempotent.

        :param name: The token rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Load the full configuration file and expand the tokens sequence.
        full_data = self._load()
        entries = expand_keyed_entries(
            full_data.get('tokens', []) or [],
            key_field='name',
        )

        # Remove the matching entry when present (idempotent).
        index = self._find_index(entries, name, grammar_id)
        if index is not None:
            del entries[index]

        # Re-wrap and persist the updated configuration.
        full_data['tokens'] = wrap_keyed_entries(entries, key_field='name')
        self._save(full_data)
