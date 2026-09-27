"""Tiferet Ly AST Domain Models"""

# *** imports

# ** core
from typing import Any

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: ast_node
class AstNode(DomainObject):
    '''
    An optional generic node for a parse that chooses to keep structure.

    The node stores a kind, children, a value, and a source span. It is
    not a required parse result.
    '''

    # * attribute: kind
    kind: str = Field(
        ...,
        description='The kind of generic node.',
    )

    # * attribute: children
    children: list = Field(
        default_factory=list,
        description='The child nodes stored under this node.',
    )

    # * attribute: value
    value: Any | None = Field(
        default=None,
        description='The optional value carried by this node.',
    )

    # * attribute: lineno
    lineno: int | None = Field(
        default=None,
        description='The optional source line of this node.',
    )

    # * attribute: lexpos
    lexpos: int | None = Field(
        default=None,
        description='The optional source character offset of this node.',
    )
