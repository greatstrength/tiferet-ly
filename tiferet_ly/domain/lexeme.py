"""Tiferet Ly Lexeme Domain Models"""

# *** imports

# ** core
from typing import Any

# ** infra
from pydantic import Field
from tiferet.domain.core import DomainObject

# *** models

# ** model: lexeme
class Lexeme(DomainObject):
    '''
    A recognized word and the source span where it was read.

    The span is structural. Later work can reuse the same type, payload,
    line, and position without depending on a reader token. A recognized
    text token still carries its matched text. An absent payload is valid.
    '''

    # * attribute: type
    type: str = Field(
        ...,
        description='The token type name of the recognized word.',
    )

    # * attribute: value
    value: Any | None = Field(
        default=None,
        description='The matched text, a payload a token action assigned, or none when the span carries no payload.',
    )

    # * attribute: lineno
    lineno: int = Field(
        ...,
        description='The source line of the match.',
    )

    # * attribute: lexpos
    lexpos: int = Field(
        ...,
        description='The source character offset of the match.',
    )
