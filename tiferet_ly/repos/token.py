"""Tiferet Ly Token Configuration Repository"""

# *** imports

# ** app
from tiferet.repos.core import ConfigurationRepository
from ..interfaces.token import TokenService
from ..mappers.token import (
    TokenRuleAggregate,
    TokenRuleConfigObject,
)

# *** repos

# ** repo: token_config_repository
class TokenConfigRepository(TokenService, ConfigurationRepository):
    '''
    Persist declared token rules as one ordered tokens sequence.

    Each entry is addressed by name and grammar id. Saving does not check
    that the grammar id names a stored grammar, and does not sort the list.
    '''

    # * init
    def __init__(self, token_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the token configuration repository.

        :param token_config: The configuration file path.
        :type token_config: str
        :param encoding: The file encoding.
        :type encoding: str
        '''

        # Forward the token file to the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=token_config,
            encoding=encoding,
        )

    # * method: _unwrap_named_entries
    def _unwrap_named_entries(self, entries: list) -> list[dict]:
        '''
        Flatten one-key token mappings into named dicts, in input order.

        The mapping key becomes ``name`` and wins over a name already in the
        body. No other field is injected, and a missing ``grammar_id`` is not
        defaulted.

        :param entries: The raw tokens sequence.
        :type entries: list
        :return: Flat token dicts in the same order.
        :rtype: list[dict]
        '''

        # Copy each single-key body in order, letting the key win as name.
        unwrapped = []
        for entry in entries:
            (key, body), = entry.items()
            unwrapped.append({**body, 'name': key})

        # Return a new list and leave the input untouched.
        return unwrapped

    # * method: _wrap_named_entries
    def _wrap_named_entries(self, entries: list[dict]) -> list[dict]:
        '''
        Fold flat token dicts back into one-key mappings, in input order.

        Body key order is ``grammar_id``, ``pattern``, then ``action`` only
        when that value is not None. The body does not contain ``name``.

        :param entries: The flat token dicts.
        :type entries: list[dict]
        :return: One-key token mappings in the same order.
        :rtype: list[dict]
        '''

        # Wrap each flat dict in order, omitting name from the body.
        wrapped = []
        for entry in entries:
            name = entry['name']
            body = {}
            if 'grammar_id' in entry:
                body['grammar_id'] = entry['grammar_id']
            if 'pattern' in entry:
                body['pattern'] = entry['pattern']
            if entry.get('action') is not None:
                body['action'] = entry['action']
            wrapped.append({name: body})

        # Return a new list and leave the input untouched.
        return wrapped

    # * method: _load_token_entries
    def _load_token_entries(self) -> list:
        '''
        Load the tokens sequence without writing the file.

        A missing or empty node is an empty list.

        :return: The raw tokens sequence.
        :rtype: list
        '''

        # Read only the tokens node. A missing node is an empty list.
        loaded = self._load(
            start_node=lambda data: data.get('tokens', []),
        )
        if not loaded:
            return []

        # Copy the sequence so callers can scan without mutating the load.
        return list(loaded)

    # * method: _flat_from_token
    def _flat_from_token(self, token: TokenRuleAggregate) -> dict:
        '''
        Build the flat write dict for a token aggregate.

        The written name is always the aggregate name. ``grammar_id`` is not
        invented when the primitive omits it. ``action`` is included only when
        the primitive or the aggregate attribute has a non-None action.

        :param token: The token aggregate to persist.
        :type token: TokenRuleAggregate
        :return: The flat token dict.
        :rtype: dict
        '''

        # Serialize through the consumed mapper role.
        flat = dict(
            TokenRuleConfigObject.from_model(token).to_primitive(self.default_role)
        )

        # The written and matched name is always the aggregate name.
        flat['name'] = token.name

        # Include action only when the primitive or the aggregate has one.
        if flat.get('action') is None and getattr(token, 'action', None) is not None:
            flat['action'] = token.action

        # Return the flat dict. Do not invent a grammar id.
        return flat

    # * method: _first_pair_index
    def _first_pair_index(
            self,
            entries: list[dict],
            name: str,
            grammar_id: str,
        ) -> int | None:
        '''
        Return the lowest index whose name and grammar id match exactly.

        :param entries: The unwrapped token dicts.
        :type entries: list[dict]
        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: The first matching index, or None.
        :rtype: int | None
        '''

        # Scan from index 0. The first exact pair is the match.
        for index, entry in enumerate(entries):
            if entry.get('name') == name and entry.get('grammar_id') == grammar_id:
                return index

        # Absence is not an error.
        return None

    # * method: exists
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Report whether any stored token has the exact name and grammar pair.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: True when a stored token has that pair, otherwise False.
        :rtype: bool
        '''

        # Scan unwrapped entries. Do not write the file.
        entries = self._unwrap_named_entries(self._load_token_entries())

        # An exact pair match is enough.
        return self._first_pair_index(entries, name, grammar_id) is not None

    # * method: get
    def get(self, name: str, grammar_id: str) -> TokenRuleAggregate | None:
        '''
        Return the first stored token with the exact name and grammar pair.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: The first matching token aggregate, or None.
        :rtype: TokenRuleAggregate | None
        '''

        # Scan unwrapped entries. Do not write the file.
        entries = self._unwrap_named_entries(self._load_token_entries())
        index = self._first_pair_index(entries, name, grammar_id)

        # Absence returns None. Do not catch mapper failures.
        if index is None:
            return None

        # Map the first flat match through the consumed config object.
        return TokenRuleConfigObject.model_validate(entries[index]).map()

    # * method: list
    def list(self) -> list[TokenRuleAggregate]:
        '''
        Return every stored token, unfiltered, in declared order.

        :return: The stored token aggregates.
        :rtype: list[TokenRuleAggregate]
        '''

        # Map every unwrapped entry. Do not filter or collapse names.
        entries = self._unwrap_named_entries(self._load_token_entries())
        return [
            TokenRuleConfigObject.model_validate(entry).map()
            for entry in entries
        ]

    # * method: save
    def save(self, token: TokenRuleAggregate) -> None:
        '''
        Replace the first matching pair in place, or append when the pair is absent.

        :param token: The token aggregate to persist.
        :type token: TokenRuleAggregate
        :return: None
        :rtype: None
        '''

        # Build the flat dict from the aggregate. Do not invent grammar_id.
        flat = self._flat_from_token(token)

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_tokens = full_data.get('tokens') or []
        entries = self._unwrap_named_entries(raw_tokens)

        # Replace the first exact pair, or append when the pair is absent.
        index = self._first_pair_index(entries, token.name, token.grammar_id)
        if index is None:
            entries.append(flat)
        else:
            entries[index] = flat

        # Assign only the tokens value, then persist the document.
        full_data['tokens'] = self._wrap_named_entries(entries)
        self._save(full_data)

    # * method: delete
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Remove the first matching pair. Absence does not raise.

        :param name: The declared token name.
        :type name: str
        :param grammar_id: The grammar that owns the token.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_tokens = full_data.get('tokens') or []
        entries = self._unwrap_named_entries(raw_tokens)

        # Remove only the first exact pair. A missing pair leaves the list unchanged.
        index = self._first_pair_index(entries, name, grammar_id)
        if index is not None:
            del entries[index]

        # Assign the wrapped list back, including an empty list.
        full_data['tokens'] = self._wrap_named_entries(entries)
        self._save(full_data)
