"""Tiferet-Ly Lexeme Domain Model"""

# *** imports

# ** core
from typing import Any

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: lexeme
class Lexeme(DomainObject):
    '''
    A recognized word from source text. It is not a TokenRule: it is the
    span a reader actually produced, so a later tree can reuse this
    location rather than invent a second one.
    '''

    # * attribute: type
    type: str = Field(
        ...,
        description='The token type name that recognized this span.',
    )

    # * attribute: value
    value: Any = Field(
        ...,
        description='The matched text, or the value a token action assigned.',
    )

    # * attribute: lineno
    lineno: int = Field(
        ...,
        description='The source line of this span.',
    )

    # * attribute: lexpos
    lexpos: int = Field(
        ...,
        description='The source position of this span.',
    )
