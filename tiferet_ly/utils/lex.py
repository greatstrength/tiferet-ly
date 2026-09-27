"""Tiferet Ly Ply Lexer"""

# *** imports

# ** core
import types

# ** app
from tiferet_ly.interfaces.lexer import LexerService
from tiferet_ly.mappers.lexeme import LexemeAggregate
from tiferet_ly.utils import core as reader_core
from tiferet_ly.utils.core import PlyReader

# *** utils

# ** util: ply_lexer
class PlyLexer(PlyReader, LexerService):
    '''
    Read declared text as lexeme aggregates, not as reader tokens.

    Each call builds a fresh lexer from the selected token set. Optional
    rewrites are accepted and ignored until a later child supplies a use.
    '''

    # * method: tokenize
    def tokenize(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
        ) -> list[LexemeAggregate]:
        '''
        Turn declared text into lexeme aggregates for one grammar.

        The shared reader resolves the grammar, installs the selected
        tokens, and builds with ``optimize=0``. Each PLY token is mapped
        through ``LexemeAggregate.new``. An unmatched character raises
        ``LEX_ERROR_ID``. A build failure raises ``READER_BUILD_FAILED_ID``.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read.
        :type text: str
        :param tokens: The declared token rules.
        :type tokens: list
        :param productions: The declared production rules. Unused.
        :type productions: list
        :param grammars: The declared grammars.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None. Ignored.
        :type rewrites: dict | None
        :return: The lexeme aggregates.
        :rtype: list[LexemeAggregate]
        '''

        # Productions and rewrites are accepted. Neither selects tokens.
        _ = (productions, rewrites)

        # Build a fresh lexer. Span errors and build failures stay in the reader.
        lexer = PlyLexer._build_lexer(grammar_id, grammars, tokens)

        # Feed this call's text. Do not reuse a previous input.
        lexer.input(text)

        # Map each recognized word. An unmatched character raises here.
        lexemes = []
        token = lexer.token()
        while token is not None:
            lexemes.append(LexemeAggregate.new(
                token.type,
                token.value,
                token.lineno,
                token.lexpos,
            ))
            token = lexer.token()

        # Return aggregates, not PLY tokens.
        return lexemes

    # * method: _build_lexer (static)
    @staticmethod
    def _build_lexer(
            grammar_id: str,
            grammars: list,
            tokens: list,
        ):
        '''
        Build one lexer through the shared reader.

        Compiled actions have no module. PLY's ``optimize=0`` validation
        then fails before any token is read. Bind those actions for this
        call only, then use ``PlyReader.build_lexer``.

        :param grammar_id: The grammar identifier to resolve.
        :type grammar_id: str
        :param grammars: The declared grammar catalogue.
        :type grammars: list
        :param tokens: The declared token catalogue, in input order.
        :type tokens: list
        :return: A new PLY lexer.
        :rtype: ply.lex.Lexer
        '''

        # Keep the real builder. Restore it even when the build fails.
        real_lex = reader_core.lex.lex

        def bound_lex(*args, **kwargs):
            # Bind compiled actions before PLY validates the module.
            reader = kwargs.get('object')
            if reader is not None:
                PlyLexer._bind_compiled_actions(reader)
            return real_lex(*args, **kwargs)

        # Swap only for this build. The shared reader still calls lex.lex.
        reader_core.lex.lex = bound_lex
        try:
            return PlyReader.build_lexer(grammar_id, grammars, tokens)
        finally:
            reader_core.lex.lex = real_lex

    # * method: _bind_compiled_actions (static)
    @staticmethod
    def _bind_compiled_actions(module) -> None:
        '''
        Give module-less compiled actions a module name.

        String tokens and the reader's error function already have a
        module. Only compiled actions need a name so validation can run.

        :param module: The token module about to be built.
        :type module: object
        :return: None
        :rtype: None
        '''

        # Leave strings, wrappers, and t_error alone.
        for name in dir(module):
            value = getattr(module, name)
            if isinstance(value, types.FunctionType) and value.__module__ is None:
                value.__module__ = __name__
