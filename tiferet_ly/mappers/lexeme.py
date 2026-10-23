"""Tiferet Ly Lexeme Mappers"""

# *** imports

# ** core
from typing import Any

# ** infra
from tiferet import Aggregate

# ** app
from tiferet_ly.domain.lexeme import Lexeme

# *** mappers

# ** mapper: lexeme_aggregate
class LexemeAggregate(Lexeme, Aggregate):
    '''
    The lexeme a reader builds from a recognized word's span, or from a
    span the reader supplies itself.

    ``new`` builds from a recognized word. ``synthesize`` builds a span
    that was not copied from a recognized token. Both return this
    aggregate, not a PLY token.
    '''

    # * method: new (static)
    @staticmethod
    def new(
            type: str,
            value: str,
            lineno: int,
            lexpos: int,
        ) -> 'LexemeAggregate':
        '''
        Build a lexeme aggregate from a recognized word's span.

        :param type: The token type name.
        :type type: str
        :param value: The matched text.
        :type value: str
        :param lineno: The source line of the match.
        :type lineno: int
        :param lexpos: The source character offset of the match.
        :type lexpos: int
        :return: The lexeme aggregate.
        :rtype: LexemeAggregate
        '''

        # Build the aggregate from the four span fields.
        return LexemeAggregate(
            type=type,
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )

    # * method: synthesize (static)
    @staticmethod
    def synthesize(
            type: str,
            lineno: int,
            lexpos: int,
            value: Any | None = None,
        ) -> 'LexemeAggregate':
        '''
        Construct a lexeme that was not copied from a recognized token.

        :param type: The synthetic token type name.
        :type type: str
        :param lineno: The source line the synthetic lexeme is attributed to.
        :type lineno: int
        :param lexpos: The source character offset the synthetic lexeme is attributed to.
        :type lexpos: int
        :param value: The payload carried by the synthetic lexeme. Defaults to None.
        :type value: Any | None
        :return: The lexeme aggregate.
        :rtype: LexemeAggregate
        '''

        # Build the aggregate from the supplied span. Do not require a token.
        return LexemeAggregate(
            type=type,
            value=value,
            lineno=lineno,
            lexpos=lexpos,
        )
