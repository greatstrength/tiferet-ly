"""Tiferet Ly Production Configuration Repository"""

# *** imports

# ** app
from tiferet.repos.core import ConfigurationRepository
from ..interfaces.production import ProductionService
from ..mappers.production import (
    ProductionRuleAggregate,
    ProductionRuleConfigObject,
)

# *** repos

# ** repo: production_config_repository
class ProductionConfigRepository(ProductionService, ConfigurationRepository):
    '''
    Persist declared production rules as one ordered production_rules sequence.

    The same name and grammar may appear more than once when the specifications
    differ. Saving does not check that the grammar id names a stored grammar,
    and does not sort the list.
    '''

    # * init
    def __init__(self, production_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the production configuration repository.

        :param production_config: The configuration file path.
        :type production_config: str
        :param encoding: The file encoding.
        :type encoding: str
        '''

        # Forward the production file to the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=production_config,
            encoding=encoding,
        )

    # * method: _unwrap_named_entries
    def _unwrap_named_entries(self, entries: list) -> list[dict]:
        '''
        Flatten one-key production mappings into named dicts, in input order.

        The mapping key becomes ``name`` and wins over a name already in the
        body. No other field is injected, and a missing ``grammar_id`` is not
        defaulted.

        :param entries: The raw production_rules sequence.
        :type entries: list
        :return: Flat production dicts in the same order.
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
        Fold flat production dicts back into one-key mappings, in input order.

        Body key order is ``grammar_id``, ``spec``, then ``action`` only
        when that value is not None. The body does not contain ``name``.

        :param entries: The flat production dicts.
        :type entries: list[dict]
        :return: One-key production mappings in the same order.
        :rtype: list[dict]
        '''

        # Wrap each flat dict in order, omitting name from the body.
        wrapped = []
        for entry in entries:
            name = entry['name']
            body = {}
            if 'grammar_id' in entry:
                body['grammar_id'] = entry['grammar_id']
            if 'spec' in entry:
                body['spec'] = entry['spec']
            if entry.get('action') is not None:
                body['action'] = entry['action']
            wrapped.append({name: body})

        # Return a new list and leave the input untouched.
        return wrapped

    # * method: _load_production_entries
    def _load_production_entries(self) -> list:
        '''
        Load the production_rules sequence without writing the file.

        A missing or empty node is an empty list.

        :return: The raw production_rules sequence.
        :rtype: list
        '''

        # Read only the production_rules node. A missing node is an empty list.
        loaded = self._load(
            start_node=lambda data: data.get('production_rules', []),
        )
        if not loaded:
            return []

        # Copy the sequence so callers can scan without mutating the load.
        return list(loaded)

    # * method: _flat_from_production
    def _flat_from_production(self, production: ProductionRuleAggregate) -> dict:
        '''
        Build the flat write dict for a production aggregate.

        The written name is always the aggregate name. ``grammar_id`` is not
        invented when the primitive omits it. ``action`` is included only when
        the primitive or the aggregate attribute has a non-None action.

        :param production: The production aggregate to persist.
        :type production: ProductionRuleAggregate
        :return: The flat production dict.
        :rtype: dict
        '''

        # Serialize through the consumed mapper role.
        flat = dict(
            ProductionRuleConfigObject.from_model(production).to_primitive(
                self.default_role,
            )
        )

        # The written and matched name is always the aggregate name.
        flat['name'] = production.name

        # Include action only when the primitive or the aggregate has one.
        if flat.get('action') is None and getattr(production, 'action', None) is not None:
            flat['action'] = production.action

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

        :param entries: The unwrapped production dicts.
        :type entries: list[dict]
        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
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

    # * method: _first_triple_index
    def _first_triple_index(
            self,
            entries: list[dict],
            name: str,
            grammar_id: str,
            spec: str,
        ) -> int | None:
        '''
        Return the lowest index whose name, grammar id, and spec match exactly.

        :param entries: The unwrapped production dicts.
        :type entries: list[dict]
        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The declared production specification.
        :type spec: str
        :return: The first matching index, or None.
        :rtype: int | None
        '''

        # Scan from index 0. A different spec is not this alternative.
        for index, entry in enumerate(entries):
            if (
                entry.get('name') == name
                and entry.get('grammar_id') == grammar_id
                and entry.get('spec') == spec
            ):
                return index

        # Absence is not an error.
        return None

    # * method: exists
    def exists(self, name: str, grammar_id: str) -> bool:
        '''
        Report whether any stored production has the exact name and grammar pair.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: True when a stored production has that pair, otherwise False.
        :rtype: bool
        '''

        # Scan unwrapped entries. Do not write the file.
        entries = self._unwrap_named_entries(self._load_production_entries())

        # An exact pair match is enough.
        return self._first_pair_index(entries, name, grammar_id) is not None

    # * method: get
    def get(self, name: str, grammar_id: str) -> ProductionRuleAggregate | None:
        '''
        Return the first stored production with the exact name and grammar pair.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: The first matching production aggregate, or None.
        :rtype: ProductionRuleAggregate | None
        '''

        # Scan unwrapped entries. Do not write the file.
        entries = self._unwrap_named_entries(self._load_production_entries())
        index = self._first_pair_index(entries, name, grammar_id)

        # Absence returns None. Do not catch mapper failures.
        if index is None:
            return None

        # Map the first flat match through the consumed config object.
        return ProductionRuleConfigObject.model_validate(entries[index]).map()

    # * method: list
    def list(self) -> list[ProductionRuleAggregate]:
        '''
        Return every stored production, unfiltered, in declared order.

        :return: The stored production aggregates.
        :rtype: list[ProductionRuleAggregate]
        '''

        # Map every unwrapped entry. Do not filter or collapse alternatives.
        entries = self._unwrap_named_entries(self._load_production_entries())
        return [
            ProductionRuleConfigObject.model_validate(entry).map()
            for entry in entries
        ]

    # * method: save
    def save(self, production: ProductionRuleAggregate) -> None:
        '''
        Replace the first matching triple in place, or append when it is absent.

        :param production: The production aggregate to persist.
        :type production: ProductionRuleAggregate
        :return: None
        :rtype: None
        '''

        # Build the flat dict from the aggregate. Do not invent grammar_id.
        flat = self._flat_from_production(production)

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_rules = full_data.get('production_rules') or []
        entries = self._unwrap_named_entries(raw_rules)

        # Replace the first exact triple, or append when that spec is absent.
        index = self._first_triple_index(
            entries,
            production.name,
            production.grammar_id,
            production.spec,
        )
        if index is None:
            entries.append(flat)
        else:
            entries[index] = flat

        # Assign only the production_rules value, then persist the document.
        full_data['production_rules'] = self._wrap_named_entries(entries)
        self._save(full_data)

    # * method: delete
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Remove the first matching pair. Absence does not raise.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_rules = full_data.get('production_rules') or []
        entries = self._unwrap_named_entries(raw_rules)

        # Remove only the first exact pair. A missing pair leaves the list unchanged.
        index = self._first_pair_index(entries, name, grammar_id)
        if index is not None:
            del entries[index]

        # Assign the wrapped list back, including an empty list.
        full_data['production_rules'] = self._wrap_named_entries(entries)
        self._save(full_data)

    # * method: replace
    def replace(
            self,
            old_name: str,
            old_grammar_id: str,
            old_spec: str,
            production: ProductionRuleAggregate,
        ) -> None:
        '''
        Replace the old triple in its original index. An absent triple does not append.

        :param old_name: The stored production name to replace.
        :type old_name: str
        :param old_grammar_id: The stored grammar id to replace.
        :type old_grammar_id: str
        :param old_spec: The stored specification to replace.
        :type old_spec: str
        :param production: The production aggregate to write at that index.
        :type production: ProductionRuleAggregate
        :return: None
        :rtype: None
        '''

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_rules = full_data.get('production_rules') or []
        entries = self._unwrap_named_entries(raw_rules)

        # An absent old triple does not append and does not write.
        index = self._first_triple_index(
            entries,
            old_name,
            old_grammar_id,
            old_spec,
        )
        if index is None:
            return

        # Write the new aggregate at the original index, even if its spec differs.
        entries[index] = self._flat_from_production(production)
        full_data['production_rules'] = self._wrap_named_entries(entries)
        self._save(full_data)

    # * method: delete_alternative
    def delete_alternative(
            self,
            name: str,
            grammar_id: str,
            spec: str,
        ) -> None:
        '''
        Remove only the first matching triple. Absence does not raise.

        :param name: The declared production name.
        :type name: str
        :param grammar_id: The grammar that owns the production.
        :type grammar_id: str
        :param spec: The specification of the alternative to remove.
        :type spec: str
        :return: None
        :rtype: None
        '''

        # Load the full document so other roots stay unchanged.
        full_data = self._load()
        raw_rules = full_data.get('production_rules') or []
        entries = self._unwrap_named_entries(raw_rules)

        # Remove only the matching spec. A sibling pair stays stored.
        index = self._first_triple_index(entries, name, grammar_id, spec)
        if index is None:
            return

        # Assign the wrapped list back without that alternative.
        del entries[index]
        full_data['production_rules'] = self._wrap_named_entries(entries)
        self._save(full_data)
