"""Tiferet-Ly Lexeme Mappers"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet import Aggregate
from ..domain.lexeme import Lexeme

# *** mappers

# ** mapper: lexeme_aggregate
class LexemeAggregate(Lexeme, Aggregate):
    '''
    Mapper form of a recognized word. The lexer constructs this, not a
    bare Lexeme, so utils stay on the mapper side of the layer line.
    '''

    # * method: from_ply_token (static)
    @staticmethod
    def from_ply_token(tok: Any) -> 'LexemeAggregate':
        '''
        Copy type, value, lineno, and lexpos off a PLY token.

        :param tok: A PLY LexToken or any object with the same four fields.
        :type tok: Any
        :return: The constructed lexeme aggregate.
        :rtype: LexemeAggregate
        '''

        # Copy the four span fields in one place so tokenize never inlines them.
        return LexemeAggregate(
            type=tok.type,
            value=tok.value,
            lineno=tok.lineno,
            lexpos=tok.lexpos,
        )
