"""Tiferet-Ly Grammar Domain Model"""

# *** imports

# ** core
from typing import List, Optional

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject
from .layout import LayoutProfile

# *** models

# ** model: grammar
class Grammar(DomainObject):
    '''
    A declared grammar's own composition structure: the other grammars it
    extends (parent_ids) and its start symbol. Deliberately lean — a
    Grammar does not hold the token/production rules declared under it
    (each rule names its one owning grammar directly via grammar_id, not
    the other way around), and performs no validation beyond whatever
    Pydantic's own field typing enforces.

    Resolving a grammar's effective, ancestor-composed rule set — including
    cycle detection on parent_ids and validating that start names an
    existing production in that resolved set — is a cross-aggregate
    concern requiring the full grammar/production sets, which no single
    Grammar instance has access to. That concern belongs to whatever
    writes a Grammar (e.g. AddGrammar/UpdateGrammar), not to this domain
    object's own construction.
    '''

    # * attribute: id
    id: str = Field(
        ...,
        description='The identifier a ConfigurationRepository uses to find this grammar.',
    )

    # * attribute: parent_ids
    parent_ids: List[str] = Field(
        default_factory=list,
        description=(
            'The ordered ids of the other grammars this grammar directly '
            'extends. Declared order is precedence when resolving '
            'same-named rules across ancestors; empty is valid for a root '
            'grammar with no ancestors. Not validated for existence or '
            'cycles at this layer.'
        ),
    )

    # * attribute: start
    start: str = Field(
        ...,
        description=(
            "The start symbol, naming a production in this grammar's "
            'resolved, ancestor-composed production set. Not validated '
            'against any production catalogue at this layer.'
        ),
    )

    # * attribute: ignore
    ignore: Optional[str] = Field(
        default=None,
        description=(
            "A bare regular-expression character class PLY skips before "
            'attempting any token rule, installed as the literal t_ignore '
            'module attribute PLY\'s own convention expects. Grammar-own, '
            'like start: not composed across parent_ids.'
        ),
    )

    # * attribute: layout
    layout: Optional[LayoutProfile] = Field(
        default=None,
        description=(
            'The declared indentation/delimiter layout policy a '
            'LayoutFilter applies to this grammar\'s lexeme stream. '
            'Grammar-own, like start and ignore: not composed across '
            'parent_ids.'
        ),
    )
