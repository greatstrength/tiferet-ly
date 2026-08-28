"""Tiferet-Ly Lexeme Stream Utility"""

# *** imports

# ** core
from typing import Any, Iterator, List, Optional

# ** app
from ..mappers.lexeme import LexemeAggregate

# *** classes

# ** class: lexeme_token
class _LexemeToken:
    '''
    Small duck-typed token carrier exposing exactly the four fields
    yacc's own internals and p_error read off whatever lexer.token()
    returns, mirroring a real PLY LexToken with no PLY dependency.
    '''

    # * init
    def __init__(self, type: str, value: Any, lineno: int, lexpos: int) -> None:
        '''
        Initialize the token carrier from one lexeme's four span fields.

        :param type: The token type name.
        :type type: str
        :param value: The token's value.
        :type value: Any
        :param lineno: The source line the token is attributed to.
        :type lineno: int
        :param lexpos: The source position the token is attributed to.
        :type lexpos: int
        '''

        # Copy the four fields yacc and p_error read.
        self.type = type
        self.value = value
        self.lineno = lineno
        self.lexpos = lexpos

# *** utils

# ** util: lexeme_stream
class LexemeStream:
    '''
    Ply-lexer-shaped adapter over an already-recognized lexeme stream, so
    a parser can be driven without paying to re-lex source text it was
    never given. Generalizes tiferet-takwin's TokenStream against
    LexemeAggregate instead of a compiler-specific token type.
    '''

    # * attribute: _iter
    _iter: Iterator[LexemeAggregate]

    # * init
    def __init__(self, lexemes: List[LexemeAggregate]) -> None:
        '''
        Initialize the stream from an already-recognized lexeme list.

        :param lexemes: The recognized lexeme stream to drive a parser from.
        :type lexemes: List[LexemeAggregate]
        '''

        # Wrap the stream in an iterator; no .input() method is needed.
        self._iter = iter(lexemes)

    # * method: token
    def token(self) -> Optional[_LexemeToken]:
        '''
        Return the next lexeme as a duck-typed token, or None at exhaustion.

        :return: The next token, or None once the stream is exhausted.
        :rtype: Optional[_LexemeToken]
        '''

        # Advance the stream once; None signals exhaustion to yacc.
        lexeme = next(self._iter, None)
        if lexeme is None:
            return None

        # Carry the four span fields yacc and p_error read.
        return _LexemeToken(lexeme.type, lexeme.value, lexeme.lineno, lexeme.lexpos)
