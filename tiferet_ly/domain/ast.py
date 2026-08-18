"""Tiferet-Ly AST Domain Model"""

# *** imports

# ** core
from typing import Any, List, Optional

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: ast_node
class AstNode(DomainObject):
    '''
    An optional, generic tree node a declared language may put in a
    production result. It is a convenience factory target, not a required
    parse shape and not one type per production name.
    '''

    # * attribute: kind
    kind: str = Field(
        ...,
        description='A language-chosen node kind, not a production name.',
    )

    # * attribute: children
    children: List['AstNode'] = Field(
        default_factory=list,
        description='Child nodes; empty on a leaf.',
    )

    # * attribute: value
    value: Optional[Any] = Field(
        default=None,
        description='Optional leaf payload; unused on an internal node unless set.',
    )

    # * attribute: lineno
    lineno: Optional[int] = Field(
        default=None,
        description='Source line of the first meaningful symbol.',
    )

    # * attribute: lexpos
    lexpos: Optional[int] = Field(
        default=None,
        description='Source position of the first meaningful symbol.',
    )
