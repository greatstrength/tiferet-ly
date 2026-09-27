"""Tiferet Ly Ply Parser"""

# *** imports

# ** core
import types
from typing import Any

# ** infra
import ply.yacc as yacc

# ** app
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.reader import (
    PARSE_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.interfaces.parser import ParserService
from tiferet_ly.utils import core as reader_core
from tiferet_ly.utils.core import PlyReader
from tiferet_ly.utils.grammar import GrammarRuleSelector
from tiferet_ly.utils.translation import RuleTranslator

# *** classes

# ** class: parser_module
class _ParserModule:
    '''
    A fresh attribute bag for one parser build.

    PLY reads productions from the instance. A new instance is created
    on every parse so an earlier build cannot leak rules or a table.
    '''

# *** utils

# ** util: ply_parser
class PlyParser(PlyReader, ParserService):
    '''
    Read declared text with every selected production installed as an alternative.

    Same-named productions stay in the grammar. Each is stored under a
    unique attribute, the parse starts at the grammar start symbol, and
    no parse table is written.
    '''

    # * method: install_productions (static)
    @staticmethod
    def install_productions(productions: list) -> _ParserModule:
        '''
        Install translated productions under unique attributes.

        The first production of a name keeps the translated ``p_{name}``
        attribute. Later alternatives use ``p_{name}_2``, ``p_{name}_3``,
        and so on. A suffix already taken by another production is skipped.
        The production name and specification are not rewritten.

        :param productions: Selected productions, in selected order.
        :type productions: list
        :return: A fresh module whose production attributes are unique.
        :rtype: _ParserModule
        '''

        # A new bag on every call so an earlier parse cannot leak rules.
        module = _ParserModule()
        module.__module__ = __name__

        # Assign each translation. Do not change the production name.
        used = set()
        counts = {}
        for rule in productions:
            base, function = RuleTranslator.translate_production_rule(rule)
            counts[rule.name] = counts.get(rule.name, 0) + 1
            attribute = base if counts[rule.name] == 1 else f'{base}_{counts[rule.name]}'
            while attribute in used:
                counts[rule.name] += 1
                attribute = f'{base}_{counts[rule.name]}'
            used.add(attribute)

            # Compiled actions have no module. PLY validates by source file.
            if not function.__module__:
                function.__module__ = RuleTranslator.__module__

            setattr(module, attribute, function)

        # Return the bag. Tokens and the error handler are added by parse.
        return module

    # * method: raise_parse_error (static)
    @staticmethod
    def raise_parse_error(
            grammar_id: str,
            token: Any | None,
        ) -> None:
        '''
        Raise a syntax failure carrying the grammar and, when present, the token span.

        :param grammar_id: The grammar that owned the read.
        :type grammar_id: str
        :param token: The token in hand, or None at end of input.
        :type token: Any | None
        :return: None
        :rtype: None
        '''

        # Always name the grammar. Add the span only when a token is in hand.
        details = {
            'grammar_id': grammar_id,
        }
        if token is not None:
            details.update(
                type=token.type,
                value=token.value,
                lineno=token.lineno,
                lexpos=token.lexpos,
            )

        # Carry those keys. Do not recover inside PLY.
        ServiceError.raise_for(
            PlyParser,
            PARSE_ERROR_ID,
            message=f'Parse error in grammar {grammar_id}.',
            **details,
        )

    # * method: parse
    def parse(
            self,
            grammar_id: str,
            text: str,
            tokens: list,
            productions: list,
            grammars: list,
            rewrites: dict | None = None,
        ) -> Any:
        '''
        Read declared text for one grammar into the start action's result.

        Productions are selected, translated, and installed under unique
        attributes. The parser is built with ``write_tables=False`` and
        starts at the grammar start symbol. The return value is the start
        action's ``p[0]``.

        :param grammar_id: The grammar that owns the read.
        :type grammar_id: str
        :param text: The source text to read.
        :type text: str
        :param tokens: The declared token rules.
        :type tokens: list
        :param productions: The declared production rules.
        :type productions: list
        :param grammars: The declared grammars.
        :type grammars: list
        :param rewrites: Optional rewrites. Defaults to None. Ignored.
        :type rewrites: dict | None
        :return: The start action's ``p[0]``.
        :rtype: Any
        '''

        # Rewrites are accepted. They do not select productions.
        _ = rewrites

        # Resolve before PLY so a missing grammar never builds a parser.
        grammar = PlyReader.resolve_grammar(grammar_id, grammars)

        # Build a new lexer for this call. Do not reuse a lexer table.
        lexer = PlyParser._build_lexer(grammar_id, grammars, tokens)

        # Select in ancestry order. Repeated names stay as alternatives.
        selected = GrammarRuleSelector.select_productions(
            grammar,
            grammars,
            productions,
        )

        # Install translations under unique attributes. Do not rename them.
        module = PlyParser.install_productions(selected)

        # The parser token list is the selected token order.
        installed_tokens = PlyReader.install_tokens(grammar, grammars, tokens)
        module.tokens = list(installed_tokens.tokens)

        # Point syntax errors at the span-bearing helper.
        def p_error(token):
            PlyParser.raise_parse_error(grammar_id, token)

        module.p_error = p_error

        # Build a new parser. write_tables=False skips the PLY table.
        try:
            parser = yacc.yacc(
                module=module,
                write_tables=False,
                debug=False,
                start=grammar.start,
                errorlog=yacc.NullLogger(),
            )
        except Exception as error:
            ServiceError.raise_for(
                PlyParser,
                READER_BUILD_FAILED_ID,
                message='Reader could not be built.',
                cause=error,
                grammar_id=grammar_id,
            )

        # Return the start action's p[0].
        return parser.parse(
            text,
            lexer=lexer,
            debug=False,
        )

    # * method: _build_lexer (static)
    @staticmethod
    def _build_lexer(
            grammar_id: str,
            grammars: list,
            tokens: list,
        ):
        '''
        Build one lexer through the shared reader.

        Compiled token actions have no module. PLY's ``optimize=0``
        validation then fails before any token is read. Bind those
        actions for this call only, then use ``PlyReader.build_lexer``.

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
                PlyParser._bind_compiled_actions(reader)
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
        Give module-less compiled token actions a module name.

        String tokens and the reader's error function already have a
        module. Only compiled actions need a name so validation can run.
        Production installation is left unchanged.

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
