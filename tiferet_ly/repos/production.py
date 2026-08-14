"""Tiferet-Ly Production Configuration Repository"""

# *** imports

# ** core
from typing import Any, Dict, List, Optional, Union

# ** app
from tiferet.repos.core import ConfigurationRepository
from ..interfaces.production import ProductionService
from ..mappers.core import (
    expand_keyed_entries,
    wrap_keyed_entries,
)
from ..mappers.production import ProductionRuleConfigObject
from ..domain.production import (
    ComplexProductionRule,
    ProductionRule,
    SimpleProductionRule,
)

# *** repos

# ** repo: production_config_repository
class ProductionConfigRepository(ProductionService, ConfigurationRepository):
    '''
    The production rule configuration repository.

    Operates against a ``production_rules:`` root node shaped as a sequence
    of single-key mappings. Lookup is a linear scan on the composite key
    ``(name, grammar_id)``.
    '''

    # * init
    def __init__(self, production_config: str, encoding: str = 'utf-8') -> None:
        '''
        Initialize the production configuration repository.

        :param production_config: Path to the configuration file.
        :type production_config: str
        :param encoding: File encoding.
        :type encoding: str
        '''

        # Initialize the configuration repository base.
        ConfigurationRepository.__init__(
            self,
            config_file=production_config,
            encoding=encoding,
        )

    # * method: _load_entries
    def _load_entries(self) -> List[Dict[str, Any]]:
        '''
        Load and expand the production_rules: sequence into flat dict entries.

        :return: The expanded production rule entries in declared order.
        :rtype: List[Dict[str, Any]]
        '''

        # Load the raw production_rules sequence and expand single-key mappings.
        return self._load(
            start_node=lambda data: data.get('production_rules', []) or [],
            data_factory=lambda entries: expand_keyed_entries(entries, key_field='name'),
        )

    # * method: _find_index
    def _find_index(self, entries: List[Dict[str, Any]], name: str, grammar_id: str) -> Optional[int]:
        '''
        Find the list index of a production entry matching name and grammar_id.

        :param entries: The expanded production entries.
        :type entries: List[Dict[str, Any]]
        :param name: The production rule name.
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
        Check whether a production rule with the given name and grammar_id exists.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: True if the production rule exists, otherwise False.
        :rtype: bool
        '''

        # Load expanded entries and scan for the composite key.
        entries = self._load_entries()
        return self._find_index(entries, name, grammar_id) is not None

    # * method: get
    def get(self, name: str, grammar_id: str) -> Optional[Union[SimpleProductionRule, ComplexProductionRule]]:
        '''
        Retrieve a production rule by name and grammar_id.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: The production rule, or None if not found.
        :rtype: Optional[Union[SimpleProductionRule, ComplexProductionRule]]
        '''

        # Load expanded entries and locate the composite key.
        entries = self._load_entries()
        index = self._find_index(entries, name, grammar_id)

        # Return None when absent.
        if index is None:
            return None

        # Map the matching entry to a domain production rule.
        return ProductionRuleConfigObject.model_validate(entries[index]).map()

    # * method: list
    def list(self) -> List[Union[SimpleProductionRule, ComplexProductionRule]]:
        '''
        List every production rule unfiltered, in declared order.

        :return: All stored production rules.
        :rtype: List[Union[SimpleProductionRule, ComplexProductionRule]]
        '''

        # Load expanded entries and map each to a domain production rule.
        entries = self._load_entries()
        return [
            ProductionRuleConfigObject.model_validate(entry).map()
            for entry in entries
        ]

    # * method: save
    def save(self, production: ProductionRule) -> None:
        '''
        Persist a production rule.

        Replaces an existing ``(name, grammar_id)`` entry in its original
        list position; otherwise appends at the end.

        :param production: The production rule to persist.
        :type production: ProductionRule
        :return: None
        :rtype: None
        '''

        # Convert the production rule to a flat config dict.
        production_data = ProductionRuleConfigObject.from_model(production).to_primitive(
            self.default_role,
            exclude=set(),
        )

        # Load the full configuration file and expand the production_rules sequence.
        full_data = self._load()
        entries = expand_keyed_entries(
            full_data.get('production_rules', []) or [],
            key_field='name',
        )

        # Replace in place when the composite key already exists.
        index = self._find_index(entries, production.name, production.grammar_id)
        if index is not None:
            entries[index] = production_data
        else:
            entries.append(production_data)

        # Re-wrap and persist the updated configuration.
        full_data['production_rules'] = wrap_keyed_entries(entries, key_field='name')
        self._save(full_data)

    # * method: delete
    def delete(self, name: str, grammar_id: str) -> None:
        '''
        Delete a production rule by name and grammar_id. Idempotent.

        :param name: The production rule name.
        :type name: str
        :param grammar_id: The grammar the rule is declared under.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Load the full configuration file and expand the production_rules sequence.
        full_data = self._load()
        entries = expand_keyed_entries(
            full_data.get('production_rules', []) or [],
            key_field='name',
        )

        # Remove the matching entry when present (idempotent).
        index = self._find_index(entries, name, grammar_id)
        if index is not None:
            del entries[index]

        # Re-wrap and persist the updated configuration.
        full_data['production_rules'] = wrap_keyed_entries(entries, key_field='name')
        self._save(full_data)
