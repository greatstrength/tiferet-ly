"""Tiferet-Ly Token Rule Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: token_rule
class TokenRule(DomainObject):
    '''
    A declared token rule: how one kind of token is recognized. The base
    carries only what every token rule has in common; a bare pattern has no
    place here because the simple and complex variants disagree on what a
    pattern even is.
    '''

    # * attribute: name
    name: str = Field(
        ...,
        description='The bare token name PLY expects after its t_ prefix.',
    )

    # * attribute: subgrammar
    subgrammar: str | None = Field(
        default=None,
        description='The declared Subgrammar.id this rule belongs to; None means common to every subgrammar.',
    )

# ** model: simple_token_rule
class SimpleTokenRule(TokenRule):
    '''
    A token rule whose declaration is nothing but a bare regular
    expression pattern; translation treats this close to an identity
    operation.
    '''

    # * attribute: pattern
    pattern: str = Field(
        ...,
        description='The bare regular expression pattern PLY matches this token against.',
    )

# ** model: complex_token_rule
class ComplexTokenRule(TokenRule):
    '''
    A token rule whose declaration pairs a pattern with a small block of
    executable logic that runs whenever the rule matches.
    '''

    # * attribute: pattern
    pattern: str = Field(
        ...,
        description='The regular expression pattern PLY matches this token against.',
    )

    # * attribute: action
    action: str = Field(
        ...,
        description='An encoded source fragment that runs whenever the rule matches.',
    )
