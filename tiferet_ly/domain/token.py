"""Tiferet Ly Token Domain Models"""

# *** imports

# ** infra
from pydantic import Field

# ** app
from tiferet.domain.core import DomainObject

# *** models

# ** model: token_rule
class TokenRule(DomainObject):
    '''
    A declared word in a language, owned by exactly one grammar.

    The rule stores its name and grammar membership only. Pattern and
    action source belong to the Simple and Complex variants.
    '''

    # * attribute: name
    name: str = Field(
        ...,
        description='The bare declared token name.',
    )

    # * attribute: grammar_id
    grammar_id: str = Field(
        ...,
        description='The identifier of the one grammar that owns the rule.',
    )

# ** model: simple_token_rule
class SimpleTokenRule(TokenRule):
    '''
    A token rule whose declaration is a pattern and nothing else.

    Simple rules carry no action source. Matching behavior is the
    pattern itself.
    '''

    # * attribute: pattern
    pattern: str = Field(
        ...,
        description='The declared match pattern for the token.',
    )

# ** model: complex_token_rule
class ComplexTokenRule(TokenRule):
    '''
    A token rule that declares both a pattern and action source.

    The action is stored as source text. Compiling or executing it is
    outside the domain model.
    '''

    # * attribute: pattern
    pattern: str = Field(
        ...,
        description='The declared match pattern for the token.',
    )

    # * attribute: action
    action: str = Field(
        ...,
        description='The declared action source for the token.',
    )
