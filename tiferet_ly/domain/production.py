"""Tiferet Ly Production Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: production_rule
class ProductionRule(DomainObject):
    '''
    A declared sentence rule, owned by exactly one grammar.

    A repeated name is a legal alternative, not a duplicate declaration.
    Specification and action source belong to the Simple and Complex variants.
    '''

    # * attribute: name
    name: str = Field(
        ...,
        description='The declared production name.',
    )

    # * attribute: grammar_id
    grammar_id: str = Field(
        ...,
        description='The identifier of the one grammar that owns the production.',
    )

# ** model: simple_production_rule
class SimpleProductionRule(ProductionRule):
    '''
    A production whose declaration is a grammar specification only.

    Simple productions store no action source and do not themselves
    implement a translation-time pass-through.
    '''

    # * attribute: spec
    spec: str = Field(
        ...,
        description='The declared grammar specification for the production.',
    )

# ** model: complex_production_rule
class ComplexProductionRule(ProductionRule):
    '''
    A production that declares both a specification and action source.

    The action is stored as source text. Compiling or executing it is
    outside the domain model.
    '''

    # * attribute: spec
    spec: str = Field(
        ...,
        description='The declared grammar specification for the production.',
    )

    # * attribute: action
    action: str = Field(
        ...,
        description='The declared action source for the production.',
    )
