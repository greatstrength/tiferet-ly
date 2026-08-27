"""Tiferet-Ly PLY Lexer Utility"""

# *** imports

# ** core
from typing import Dict, List, Optional

# ** app
from tiferet.interfaces.core import ServiceError
from ..interfaces.lexer import LexerService
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.token import TokenRuleAggregate
from .core import PlyReader
from .layout import LayoutFilter

# *** utils

# ** util: ply_lexer
class PlyLexer(PlyReader, LexerService):
    '''
    Assembles a throwaway ply lexer from selected, translated token rules
    and returns a ply-free stream of LexemeAggregates.
    '''

    # * method: tokenize
    def tokenize(self,
            grammar_id: str,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            text: str,
            rewrites: Optional[Dict[str, type]] = None) -> List[LexemeAggregate]:
        '''
        Tokenize text against the selected token rules for a grammar.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param text: The source text to tokenize.
        :type text: str
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: The recognized lexemes in source order.
        :rtype: List[LexemeAggregate]
        '''

        # Resolve the target before any ply call.
        grammar = self.resolve_grammar(grammar_id, grammars)

        # Assemble a fresh lexer from the selected token set.
        lexer, _module = self.build_lexer_module(
            grammar,
            grammars,
            tokens,
            rewrites,
            self.make_t_error(grammar.id),
        )

        # Run the lexer and map each ply token through the single factory.
        lexer.input(text)
        lexemes: List[LexemeAggregate] = []
        try:
            while True:
                tok = lexer.token()
                if tok is None:
                    break
                lexemes.append(LexemeAggregate.from_ply_token(tok))
        except ServiceError:
            raise
        except Exception as error:
            self.wrap_action_failure(grammar_id, error)

        # Apply the grammar's declared layout profile, when it has one.
        if grammar.layout is not None:
            lexemes = LayoutFilter.apply(lexemes, grammar.layout, text)

        # Return the ply-free lexeme stream.
        return lexemes
