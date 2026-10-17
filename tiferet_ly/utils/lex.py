"""Tiferet Ly Ply Lexer"""

# *** imports

# ** core
import types

# ** app
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.reader import ACTION_EXECUTION_FAILED_ID
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
    rewrites are passed into token translation.
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
        A non-``ServiceError`` exception from ``lexer.token()`` raises
        ``ACTION_EXECUTION_FAILED_ID``. ``ServiceError`` values, including
        ``LEX_ERROR_ID``, pass through unchanged.

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
        :param rewrites: Optional rewrites passed into token translation. Defaults to None.
        :type rewrites: dict | None
        :return: The lexeme aggregates.
        :rtype: list[LexemeAggregate]
        '''

        # Productions are accepted and unused. They do not select tokens.
        _ = productions

        # Build a fresh lexer. Pass caller rewrites into token translation.
        lexer = PlyLexer._build_lexer(
            grammar_id,
            grammars,
            tokens,
            rewrites=rewrites,
        )

        # Feed this call's text. Do not reuse a previous input.
        lexer.input(text)

        # Map each recognized word. Wrap only the token loop.
        lexemes = []
        try:
            token = lexer.token()
            while token is not None:
                lexemes.append(LexemeAggregate.new(
                    token.type,
                    token.value,
                    token.lineno,
                    token.lexpos,
                ))
                token = lexer.token()
        except ServiceError:
            # Existing reader errors, including lexical failures, pass through.
            raise
        except Exception as error:
            # Prefer the innermost compiled rule named in the traceback.
            frames = []
            tb = error.__traceback__
            while tb is not None:
                frames.append(tb)
                tb = tb.tb_next
            rule_name = None
            for frame in reversed(frames):
                filename = frame.tb_frame.f_code.co_filename
                if filename.startswith('<rule:') and filename.endswith('>'):
                    rule_name = filename[len('<rule:'):-1]
                    break

            # Raise the action failure. Omit rule_name when no frame matches.
            attribution = {}
            if rule_name is not None:
                attribution['rule_name'] = rule_name
            ServiceError.raise_for(
                self,
                ACTION_EXECUTION_FAILED_ID,
                message=str(error),
                cause=error,
                grammar_id=grammar_id,
                **attribution,
            )

        # Return aggregates, not PLY tokens.
        return lexemes

    # * method: _build_lexer (static)
    @staticmethod
    def _build_lexer(
            grammar_id: str,
            grammars: list,
            tokens: list,
            rewrites: dict | None = None,
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
        :param rewrites: Optional rewrites forwarded to lexer construction. Defaults to None.
        :type rewrites: dict | None
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
            return PlyReader.build_lexer(
                grammar_id,
                grammars,
                tokens,
                rewrites=rewrites,
            )
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
