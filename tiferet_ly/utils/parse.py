"""Tiferet-Ly PLY Parser Utility"""

# *** imports

# ** core
from typing import Any, Callable, Dict, List, Optional

# ** infra
from ply import yacc

# ** app
from tiferet.interfaces.core import ServiceError
from ..interfaces.parser import ParserService
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate
from .core import (
    PARSE_ERROR_ID,
    PARSE_INPUT_INVALID_ID,
    READER_BUILD_FAILED_ID,
    PlyReader,
)
from .grammar import GrammarRuleSelector
from .stream import LexemeStream
from .translation import RuleTranslator

# *** utils

# ** util: ply_parser
class PlyParser(PlyReader, ParserService):
    '''
    Assembles a throwaway ply parser from selected, translated rules and
    returns whatever the start-symbol action left in p[0].
    '''

    # * method: unique_production_attr (static)
    @staticmethod
    def unique_production_attr(name: str, used: Dict[str, int]) -> str:
        '''
        Return a unique p_* attribute name for a production alternative.

        :param name: The declared production name.
        :type name: str
        :param used: Counts of names already installed.
        :type used: Dict[str, int]
        :return: The unique attribute name.
        :rtype: str
        '''

        # First alternative keeps p_{name}; later ones suffix _2, _3, ...
        used[name] = used.get(name, 0) + 1
        if used[name] == 1:
            return f'p_{name}'
        return f'p_{name}_{used[name]}'

    # * method: make_p_error
    def make_p_error(self, grammar_id: str) -> Callable:
        '''
        Build a fail-loud p_error for an assembled parser module.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :return: The p_error function.
        :rtype: Callable
        '''

        # Name the token at the failed shift/reduce, or unexpected EOF.
        def p_error(p):
            kwargs: Dict[str, Any] = {
                'grammar_id': grammar_id,
            }
            if p is not None:
                kwargs.update(
                    type=p.type,
                    value=p.value,
                    lineno=p.lineno,
                    lexpos=p.lexpos,
                )
            ServiceError.raise_for(
                self,
                PARSE_ERROR_ID,
                message='Syntax error.',
                **kwargs,
            )

        # Return the installed error handler.
        return p_error

    # * method: install_production_attrs
    def install_production_attrs(
            self,
            module: Any,
            selected_productions: List[ProductionRuleAggregate],
            rewrites: Optional[Dict[str, type]]) -> None:
        '''
        Install selected production functions under unique p_* names.

        :param module: The module receiving p_* attrs.
        :type module: Any
        :param selected_productions: Productions in selected order.
        :type selected_productions: List[ProductionRuleAggregate]
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        '''

        # Disambiguate alternatives that share a name; leave RFP-003's return alone.
        used: Dict[str, int] = {}
        for rule in selected_productions:
            _attr_name, func = RuleTranslator.translate_production_rule(
                rule,
                rewrites=rewrites,
            )
            attr_name = self.unique_production_attr(rule.name, used)
            setattr(
                module,
                attr_name,
                self.bind_callable(module, attr_name, func),
            )

    # * method: parse
    def parse(self,
            grammar_id: str,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            productions: List[ProductionRuleAggregate],
            text: Optional[str] = None,
            lexemes: Optional[List[LexemeAggregate]] = None,
            rewrites: Optional[Dict[str, type]] = None) -> Any:
        '''
        Parse against the selected rules for a grammar, from source text
        or from an already-recognized lexeme stream.

        Exactly one of text or lexemes must be supplied. When lexemes is
        given, no PLY lexer is built or run at all: token names are
        derived directly, and the assembled parser is driven by a
        LexemeStream instead of a live PLY lexer.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The unfiltered production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param text: The source text to parse. Mutually exclusive with lexemes.
        :type text: Optional[str]
        :param lexemes: An already-recognized lexeme stream to parse. Mutually exclusive with text.
        :type lexemes: Optional[List[LexemeAggregate]]
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: Whatever the start-symbol action left in p[0].
        :rtype: Any
        '''

        # Exactly one of text/lexemes must be supplied, before any ply call.
        if (text is None) == (lexemes is None):
            ServiceError.raise_for(
                self,
                PARSE_INPUT_INVALID_ID,
                message='Exactly one of text or lexemes must be supplied.',
                grammar_id=grammar_id,
                reason='missing' if text is None else 'ambiguous',
            )

        # Resolve the target before any ply call.
        grammar = self.resolve_grammar(grammar_id, grammars)

        # Build a real lexer from text, or a lexer-free token list from lexemes.
        if lexemes is not None:
            module = self.new_module('tiferet_ly_parser')
            module.tokens = self.select_token_names(grammar, grammars, tokens)
            reader = LexemeStream(lexemes)
        else:
            reader, module = self.build_lexer_module(
                grammar,
                grammars,
                tokens,
                rewrites,
                self.make_t_error(grammar.id),
            )

        # Select productions, install unique p_* attrs, and assemble yacc.
        selected = GrammarRuleSelector.select_productions(
            grammar,
            grammars,
            productions,
        )
        self.install_production_attrs(module, selected, rewrites)
        module.start = grammar.start
        module.p_error = self.bind_callable(
            module,
            'p_error',
            self.make_p_error(grammar.id),
        )
        try:
            parser = yacc.yacc(
                module=module,
                write_tables=False,
                debug=False,
                start=grammar.start,
            )
        except ServiceError:
            raise
        except Exception as error:
            ServiceError.raise_for(
                self,
                READER_BUILD_FAILED_ID,
                message=str(error),
                cause=error,
                grammar_id=grammar.id,
            )

        # Run the parser; a lexeme stream never takes a text input argument.
        try:
            if lexemes is not None:
                return parser.parse(lexer=reader)
            return parser.parse(text, lexer=reader)
        except ServiceError:
            raise
        except Exception as error:
            self.wrap_action_failure(grammar_id, error)
