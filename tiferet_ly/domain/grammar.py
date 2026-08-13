"""Tiferet-Ly Grammar Declaration Domain Models"""

# *** imports

# ** core
from typing import Any, List

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject
from .production import ComplexProductionRule, ProductionRule, SimpleProductionRule
from .subgrammar import Subgrammar
from .token import ComplexTokenRule, SimpleTokenRule, TokenRule

# *** functions

# ** function: expand_keyed_entries
def expand_keyed_entries(entries: Any, key_field: str) -> Any:
    '''
    Expand a YAML-style sequence of single-key mappings (e.g. ``- PLUS:
    {pattern: '+'}``) into a sequence of flat dicts carrying ``key_field``.
    Entries already in canonical flat-dict form pass through unchanged, so
    both declaration shapes are accepted.

    :param entries: The raw catalogue entries, or any other shape (passed through unchanged).
    :type entries: Any
    :param key_field: The field name the single mapping key is injected under.
    :type key_field: str
    :return: The expanded entries, or the original value when not a list.
    :rtype: Any
    '''

    # Only lists are eligible for expansion; anything else passes through.
    if not isinstance(entries, list):
        return entries

    # Expand each entry that looks like a single-key YAML mapping.
    expanded = []
    for entry in entries:
        if isinstance(entry, dict) and key_field not in entry and len(entry) == 1:
            ((key, body),) = entry.items()
            expanded.append({key_field: key, **(body or {})})
        else:
            expanded.append(entry)

    # Return the expanded entries.
    return expanded

# ** function: build_token_rule
def build_token_rule(entry: Any) -> Any:
    '''
    Construct the correct TokenRule variant from a flat dict, branching on
    the presence of ``action``. Anything that is not a plain dict (e.g. an
    already-constructed TokenRule instance) passes through unchanged.

    :param entry: The flat rule dict, or an already-constructed instance.
    :type entry: Any
    :return: The constructed TokenRule instance, or the original value.
    :rtype: Any
    '''

    # Pass through anything that is not a plain dict.
    if not isinstance(entry, dict):
        return entry

    # Construct the complex variant when an action is present, else the simple variant.
    return ComplexTokenRule(**entry) if 'action' in entry else SimpleTokenRule(**entry)

# ** function: build_production_rule
def build_production_rule(entry: Any) -> Any:
    '''
    Construct the correct ProductionRule variant from a flat dict,
    branching on the presence of ``action``. Anything that is not a plain
    dict (e.g. an already-constructed ProductionRule instance) passes
    through unchanged.

    :param entry: The flat rule dict, or an already-constructed instance.
    :type entry: Any
    :return: The constructed ProductionRule instance, or the original value.
    :rtype: Any
    '''

    # Pass through anything that is not a plain dict.
    if not isinstance(entry, dict):
        return entry

    # Construct the complex variant when an action is present, else the simple variant.
    return ComplexProductionRule(**entry) if 'action' in entry else SimpleProductionRule(**entry)

# *** models

# ** model: grammar_declaration
class GrammarDeclaration(DomainObject):
    '''
    The complete, declared description of one small language: its
    catalogues of token rules and productions, the subgrammars it
    supports, and its start symbol.
    '''

    # * attribute: id
    id: str = Field(
        ...,
        description='The identifier a ConfigurationRepository uses to find this declaration.',
    )

    # * attribute: subgrammars
    subgrammars: List[Subgrammar] = Field(
        ...,
        min_length=1,
        description='The declared dialects this grammar supports; required to be non-empty.',
    )

    # * attribute: token_rules
    token_rules: List[TokenRule] = Field(
        default_factory=list,
        description='The ordered token catalogue, in declared order.',
    )

    # * attribute: production_rules
    production_rules: List[ProductionRule] = Field(
        default_factory=list,
        description='The ordered production catalogue, in declared order.',
    )

    # * attribute: start
    start: str = Field(
        ...,
        description='The start symbol, naming a production in production_rules.',
    )

    # * method: _expand_catalogues (validator)
    @model_validator(mode='before')
    @classmethod
    def _expand_catalogues(cls, data: Any) -> Any:
        '''
        Expand the YAML sequence-of-single-key-mappings shape for
        subgrammars, token_rules, and production_rules, dispatching token
        and production rules to their simple or complex variant by the
        presence of an action.

        :param data: The raw input data passed to the model.
        :type data: Any
        :return: The (possibly augmented) input data.
        :rtype: Any
        '''

        # Only mutate dict-shaped inputs; pass other shapes through unchanged.
        if not isinstance(data, dict):
            return data

        # Copy so the caller's original dict is never mutated in place.
        data = dict(data)

        # Expand the subgrammar registry entries.
        if 'subgrammars' in data:
            data['subgrammars'] = expand_keyed_entries(data['subgrammars'], key_field='id')

        # Expand and construct the token rule catalogue.
        if 'token_rules' in data:
            data['token_rules'] = [
                build_token_rule(entry)
                for entry in expand_keyed_entries(data['token_rules'], key_field='name')
            ]

        # Expand and construct the production rule catalogue.
        if 'production_rules' in data:
            data['production_rules'] = [
                build_production_rule(entry)
                for entry in expand_keyed_entries(data['production_rules'], key_field='name')
            ]

        # Return the augmented input data.
        return data

    # * method: _validate_references (validator)
    @model_validator(mode='after')
    def _validate_references(self) -> 'GrammarDeclaration':
        '''
        Validate token rule name uniqueness, the start symbol reference,
        and every rule's subgrammar reference, once all catalogues have
        been constructed.

        :return: The validated GrammarDeclaration.
        :rtype: GrammarDeclaration
        '''

        # Validate token rule name uniqueness within the token catalogue.
        token_names = [rule.name for rule in self.token_rules]
        duplicate_token_names = {name for name in token_names if token_names.count(name) > 1}
        if duplicate_token_names:
            raise ValueError(
                f'Duplicate token rule name(s) declared: {sorted(duplicate_token_names)}.'
            )

        # Validate the start symbol names an existing production.
        production_names = {rule.name for rule in self.production_rules}
        if self.start not in production_names:
            raise ValueError(
                f"start '{self.start}' does not name a declared production."
            )

        # Validate every rule's subgrammar tag (if set) names a declared subgrammar.
        subgrammar_ids = {subgrammar.id for subgrammar in self.subgrammars}
        for rule in [*self.token_rules, *self.production_rules]:
            if rule.subgrammar is not None and rule.subgrammar not in subgrammar_ids:
                raise ValueError(
                    f"Rule '{rule.name}' references undeclared subgrammar '{rule.subgrammar}'."
                )

        # Return self, per the model_validator(mode='after') contract.
        return self
