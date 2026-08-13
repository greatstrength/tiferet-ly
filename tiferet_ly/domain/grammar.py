"""Tiferet-Ly Grammar Declaration Domain Models"""

# *** imports

# ** core
from typing import List

# ** infra
from pydantic import Field, model_validator

# ** app
from tiferet.domain.core import DomainObject
from .production import ProductionRule
from .token import TokenRule

# *** models

# ** model: subgrammar
class Subgrammar(DomainObject):
    '''
    A named, declared dialect of one grammar declaration. Documentation
    only, no behavior; token and production rules refer to a subgrammar by
    id rather than nesting inside it. Kept in this module rather than its
    own, since TokenRule/ProductionRule only ever reference it by id,
    never by importing the type itself.
    '''

    # * attribute: id
    id: str = Field(
        ...,
        description='The unique identifier of the subgrammar within its declaring grammar.',
    )

    # * attribute: description
    description: str | None = Field(
        default=None,
        description='A human-readable description of the subgrammar.',
    )

# ** model: grammar_declaration
class GrammarDeclaration(DomainObject):
    '''
    The complete, declared description of one small language: its
    catalogues of token rules and productions, the subgrammars it
    supports, and its start symbol.

    Deliberately format-agnostic: this model accepts already-constructed
    TokenRule/ProductionRule/Subgrammar instances (or canonical field-name
    dicts pydantic can build them from directly). Reading the RFP's YAML
    sequence-of-single-key-mappings shape and dispatching simple vs.
    complex rule construction is a mapper/TransferObject concern, not a
    domain object concern.
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

    # * method: _validate_references (validator)
    @model_validator(mode='after')
    def _validate_references(self) -> 'GrammarDeclaration':
        '''
        Validate token rule name uniqueness, the start symbol reference,
        and every rule's subgrammar reference, once all catalogues have
        been constructed. Operates only on already-built domain objects;
        has no opinion on how those objects were produced.

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
