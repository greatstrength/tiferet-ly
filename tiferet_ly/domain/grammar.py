"""Tiferet Ly Grammar Domain Models"""

# *** imports

# ** core
from typing import List

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: grammar
class Grammar(DomainObject):
    '''
    The identity and composition of one declared grammar.

    A grammar names itself, the grammars it composes, and the production
    it starts from. It does not own a rule catalogue or check those facts
    against any other aggregate.
    '''

    # * attribute: id
    id: str = Field(
        ...,
        description='The grammar identifier.',
    )

    # * attribute: parent_ids
    parent_ids: List[str] = Field(
        default_factory=list,
        description='The ordered identifiers of the grammars this grammar composes.',
    )

    # * attribute: start
    start: str = Field(
        ...,
        description='The declared start-production name.',
    )
