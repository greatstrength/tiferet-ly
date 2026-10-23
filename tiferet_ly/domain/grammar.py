"""Tiferet Ly Grammar Domain Models"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from pydantic import Field
from tiferet.domain.core import DomainObject

# ** app
from .layout import LayoutProfile

# *** models

# ** model: grammar
class Grammar(DomainObject):
    '''
    The identity and composition of one declared grammar.

    A grammar names itself, the grammars it composes, the production it
    starts from, and an optional ignore pattern of its own. It does not
    own a rule catalogue or check those facts against any other aggregate.
    The ignore pattern is not composed across parent_ids. A declared
    layout profile is grammar-own, like start and ignore: construction
    does not read parent_ids to fill it.
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

    # * attribute: ignore
    ignore: Optional[str] = Field(
        default=None,
        description=(
            'A bare regular-expression character class PLY skips before attempting any '
            'token rule, installed as the literal t_ignore module attribute PLY\'s own '
            'convention expects. Grammar-own, like start: not composed across parent_ids.'
        ),
    )

    # * attribute: layout
    layout: LayoutProfile | None = Field(
        default=None,
        description=(
            'The declared indentation/delimiter layout policy a LayoutFilter applies to '
            'this grammar\'s lexeme stream. Grammar-own, like start and ignore: not '
            'composed across parent_ids.'
        ),
    )
