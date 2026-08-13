"""Tiferet-Ly Subgrammar Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: subgrammar
class Subgrammar(DomainObject):
    '''
    A named, declared dialect of one grammar declaration. Documentation
    only, no behavior; token and production rules refer to a subgrammar by
    id rather than nesting inside it.
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
