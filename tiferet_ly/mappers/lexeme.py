"""Tiferet Ly Lexeme Mappers"""

# *** imports

# ** app
from tiferet import Aggregate
from tiferet_ly.domain.lexeme import Lexeme

# *** mappers

# ** mapper: lexeme_aggregate
class LexemeAggregate(Lexeme, Aggregate):
    '''
    The lexeme a reader builds from a recognized word's span.

    ``new`` is the only constructor the reader may use. It returns this
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
