"""Tiferet-Ly Layout Profile Domain Model"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: layout_profile
class LayoutProfile(DomainObject):
    '''
    A declared per-grammar lexical layout policy: which already-recognized
    tokens introduce a block or pair up as nesting delimiters, what to
    name the synthetic indent/dedent tokens a LayoutFilter injects, and
    whether a newline token is suppressed while delimiter depth is
    nonzero. Productizes tiferet-takwin's hand-written BlockTracker state
    machine as declared data instead of a Python subclass.
    '''

    # * attribute: block_tokens
    block_tokens: List[str] = Field(
        default_factory=list,
        description='Names of already-recognized tokens that introduce a block.',
    )

    # * attribute: open_delimiters
    open_delimiters: List[str] = Field(
        default_factory=list,
        description='Names of already-recognized tokens that open a nesting delimiter.',
    )

    # * attribute: close_delimiters
    close_delimiters: List[str] = Field(
        default_factory=list,
        description='Names of already-recognized tokens that close a nesting delimiter.',
    )

    # * attribute: newline_token
    newline_token: Optional[str] = Field(
        default=None,
        description=(
            'The name of the already-recognized token representing a line '
            'break; required for delimiter-depth newline suppression to '
            'do anything.'
        ),
    )

    # * attribute: suppress_newline_in_delimiters
    suppress_newline_in_delimiters: bool = Field(
        default=True,
        description=(
            'Whether an occurrence of newline_token is dropped from the '
            'output stream while delimiter depth is greater than zero.'
        ),
    )

    # * attribute: indent_token
    indent_token: str = Field(
        ...,
        description='The declared name of the synthetic token a LayoutFilter injects on indent.',
    )

    # * attribute: dedent_token
    dedent_token: str = Field(
        ...,
        description='The declared name of the synthetic token a LayoutFilter injects on dedent.',
    )

    # * attribute: tab_size
    tab_size: int = Field(
        default=4,
        description='The column-width one indentation level represents.',
    )
