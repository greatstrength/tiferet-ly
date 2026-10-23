"""Tiferet Ly Lexeme Stream Utility"""

# *** imports

# ** core
from typing import Any, Iterator

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate

# *** classes

# ** class: lexeme_token
class LexemeToken:
    '''
    Carry type, value, lineno, and lexpos for one recognized lexeme.

    A parser reads those four fields off the object ``token`` returns.
    This carrier is not a PLY token, and constructing it does not import PLY.
    '''

    # * init
    def __init__(
            self,
            type: str,
            value: Any,
            lineno: int,
            lexpos: int,
        ) -> None:
        '''
        Initialize the carrier from one lexeme's span fields.

        :param type: Token type name copied from the lexeme.
        :type type: str
        :param value: Value copied from the lexeme, without coercion.
        :type value: Any
        :param lineno: Source line copied from the lexeme.
        :type lineno: int
        :param lexpos: Source character offset copied from the lexeme.
        :type lexpos: int
        :return: None.
        :rtype: None
        '''

        # Store the four span fields in order.
        self.type = type
        self.value = value
        self.lineno = lineno
        self.lexpos = lexpos

# *** utils

# ** util: lexeme_stream
class LexemeStream:
    '''
    Adapt an already-recognized lexeme list to the ``token`` calls a parser makes.

    Each call returns one carrier, in list order, and then ``None``.
    The adapter does not re-lex text, does not filter the list, and does not import PLY.
    '''

    # * attribute: _iter
    _iter: Iterator[LexemeAggregate]

    # * init
    def __init__(self, lexemes: list[LexemeAggregate]) -> None:
        '''
        Initialize the adapter over a recognized lexeme list.

        :param lexemes: The recognized lexeme list.
        :type lexemes: list[LexemeAggregate]
        :return: None.
        :rtype: None
        '''

        # Wrap the list in an iterator. This adapter has no input method.
        self._iter = iter(lexemes)

    # * method: token
    def token(self) -> LexemeToken | None:
        '''
        Return the carrier for the next lexeme, or None once the list is exhausted.

        :return: The next carrier, or None once the list is exhausted.
        :rtype: LexemeToken | None
        '''

        # Advance the iterator once. None means the list is exhausted.
        lexeme = next(self._iter, None)
        if lexeme is None:
            return None

        # Build the carrier from type, value, lineno, and lexpos, in that order.
        return LexemeToken(lexeme.type, lexeme.value, lexeme.lineno, lexeme.lexpos)
