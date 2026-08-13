"""Tiferet-Ly Production Rule Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: production_rule
class ProductionRule(DomainObject):
    '''
    A declared grammar production: how a sequence of tokens and/or other
    productions forms a larger structure. The base carries only what every
    production has in common.
    '''

    # * attribute: name
    name: str = Field(
        ...,
        description='The bare rule name PLY expects after its p_ prefix.',
    )

    # * attribute: subgrammar
    subgrammar: str | None = Field(
        default=None,
        description='The declared Subgrammar.id this rule belongs to; None means common to every subgrammar.',
    )

# ** model: simple_production_rule
class SimpleProductionRule(ProductionRule):
    '''
    A production whose declaration is nothing but its grammar-pattern
    string; the parser step it represents does nothing beyond a
    pass-through action.
    '''

    # * attribute: spec
    spec: str = Field(
        ...,
        description="The grammar-pattern string in PLY's own docstring grammar notation.",
    )

# ** model: complex_production_rule
class ComplexProductionRule(ProductionRule):
    '''
    A production whose declaration pairs a grammar-pattern string with the
    code that runs when the production matches.
    '''

    # * attribute: spec
    spec: str = Field(
        ...,
        description="The grammar-pattern string in PLY's own docstring grammar notation.",
    )

    # * attribute: action
    action: str = Field(
        ...,
        description='An encoded source fragment that runs when the production matches.',
    )
