"""Tiferet Ly Lexeme Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: lexeme
class Lexeme(DomainObject):
    '''
    A recognized word and the source span where it was read.

    The value is structural. Later AST work can reuse the same type,
    text, line, and position without depending on a reader token.
    '''

    # * attribute: type
    type: str = Field(
        ...,
        description='The token type name of the recognized word.',
    )

    # * attribute: value
    value: str = Field(
        ...,
        description='The matched text of the recognized word.',
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
