"""Tiferet Ly Shared Reader Assembly"""

# *** imports

# ** infra
import ply.lex as lex

# ** app
from tiferet.interfaces.core import ServiceError
from tiferet_ly.assets.grammar import GRAMMAR_NOT_FOUND_ID
from tiferet_ly.assets.reader import (
    LEX_ERROR_ID,
    READER_BUILD_FAILED_ID,
)
from tiferet_ly.mappers.grammar import GrammarAggregate
from tiferet_ly.mappers.token import (
    ComplexTokenRuleAggregate,
    SimpleTokenRuleAggregate,
)
from tiferet_ly.utils.grammar import GrammarRuleSelector
from tiferet_ly.utils.translation import RuleTranslator

# *** classes

# ** class: token_module
class _TokenModule:
    '''
    A fresh attribute bag for one lexer build.

    PLY reads token rules from the instance. A new instance is created
    on every install so an earlier build cannot leak rules or a table.
    '''

# *** utils

# ** util: ply_reader
class PlyReader:
    '''
    Assemble a declared grammar into a PLY lexer without caching a table.

    The helper resolves the grammar, installs translated tokens in
    selected order, and raises span-bearing reader errors. It does not
    tokenize or parse.
    '''

    # * method: resolve_grammar (static)
    @staticmethod
    def resolve_grammar(
            grammar_id: str,
            grammars: list[GrammarAggregate],
        ) -> GrammarAggregate:
        '''
        Return the grammar with this identifier, or raise before PLY.

        The first matching aggregate in the supplied list is returned.
        A missing identifier raises ``GRAMMAR_NOT_FOUND_ID`` and does
        not build a lexer.

        :param grammar_id: The grammar identifier to resolve.
        :type grammar_id: str
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :return: The matching grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Return the first match. Do not call PLY.
        for grammar in grammars:
            if grammar.id == grammar_id:
                return grammar

        # A missing grammar fails before any lexer build.
        ServiceError.raise_for(
            PlyReader,
            GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar {grammar_id} was not found.',
            grammar_id=grammar_id,
        )

    # * method: install_tokens (static)
    @staticmethod
    def install_tokens(
            grammar: GrammarAggregate,
            grammars: list[GrammarAggregate],
            tokens: list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate],
        ) -> _TokenModule:
        '''
        Install selected token rules in selected order.

        Selection runs first. Each survivor is translated and stored
        under its ``t_`` name. The bare names on ``tokens`` stay in
        that same order, including a later simple token after an
        earlier complex token.

        :param grammar: The grammar whose ancestry to apply.
        :type grammar: GrammarAggregate
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :param tokens: The declared token catalogue, in input order.
        :type tokens: list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate]
        :return: A fresh module whose ``tokens`` list is the installed names.
        :rtype: _TokenModule
        '''

        # Select first. Do not translate tokens the selector drops.
        selected = GrammarRuleSelector.select_tokens(
            grammar,
            grammars,
            tokens,
        )

        # Install each translation in the selected order. Do not regroup.
        module = _TokenModule()
        names = []
        for rule in selected:
            attribute, value = RuleTranslator.translate_token_rule(rule)
            setattr(module, attribute, value)
            names.append(rule.name)

        # The name list is the selected order, not a PLY sort.
        module.tokens = names
        return module

    # * method: raise_lex_error (static)
    @staticmethod
    def raise_lex_error(
            grammar_id: str,
            lineno: int,
            lexpos: int,
            value: str,
        ) -> None:
        '''
        Raise a lexical failure carrying the source span.

        :param grammar_id: The grammar that owned the read.
        :type grammar_id: str
        :param lineno: The line where reading stopped.
        :type lineno: int
        :param lexpos: The character offset where reading stopped.
        :type lexpos: int
        :param value: The unmatched text.
        :type value: str
        :return: None
        :rtype: None
        '''

        # Carry the four span keys. Do not skip the character.
        ServiceError.raise_for(
            PlyReader,
            LEX_ERROR_ID,
            message=f'Lexical error in grammar {grammar_id}.',
            grammar_id=grammar_id,
            lineno=lineno,
            lexpos=lexpos,
            value=value,
        )

    # * method: build_lexer (static)
    @staticmethod
    def build_lexer(
            grammar_id: str,
            grammars: list[GrammarAggregate],
            tokens: list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate],
        ):
        '''
        Build a new lexer for one grammar.

        The grammar is resolved before PLY is called. Each call builds
        a new lexer with ``optimize=0``, so no PLY table is read or
        written. A PLY build failure raises ``READER_BUILD_FAILED_ID``.

        :param grammar_id: The grammar identifier to resolve.
        :type grammar_id: str
        :param grammars: The declared grammar catalogue.
        :type grammars: list[GrammarAggregate]
        :param tokens: The declared token catalogue, in input order.
        :type tokens: list[SimpleTokenRuleAggregate | ComplexTokenRuleAggregate]
        :return: A new PLY lexer.
        :rtype: ply.lex.Lexer
        '''

        # Resolve before PLY so a missing grammar never builds a lexer.
        grammar = PlyReader.resolve_grammar(grammar_id, grammars)

        # Install translated tokens in selected order on a fresh module.
        module = PlyReader.install_tokens(grammar, grammars, tokens)

        # Point lexical failures at the span-bearing helper.
        def t_error(token):
            PlyReader.raise_lex_error(
                grammar_id,
                token.lineno,
                token.lexpos,
                token.value,
            )

        module.t_error = t_error

        # Build a new lexer. optimize=0 skips the PLY table.
        try:
            return lex.lex(
                object=module,
                optimize=0,
                debug=False,
                errorlog=lex.NullLogger(),
            )
        except Exception as error:
            ServiceError.raise_for(
                PlyReader,
                READER_BUILD_FAILED_ID,
                message='Reader could not be built.',
                cause=error,
                grammar_id=grammar_id,
            )
