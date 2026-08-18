"""Tiferet-Ly PLY Lexer and Parser Utilities"""

# *** imports

# ** core
import re
import sys
import types
from typing import Any, Callable, Dict, List, Optional, Tuple

# ** infra
from ply import lex, yacc

# ** app
from tiferet.interfaces.core import ServiceError
from ..interfaces.lexer import LexerService
from ..interfaces.parser import ParserService
from ..mappers.grammar import GrammarAggregate
from ..mappers.lexeme import LexemeAggregate
from ..mappers.production import ProductionRuleAggregate
from ..mappers.token import TokenRuleAggregate
from .grammar import GrammarRuleSelector
from .translation import RuleTranslator

# *** constants

# ** constant: grammar_not_found_id
GRAMMAR_NOT_FOUND_ID = 'GRAMMAR_NOT_FOUND'

# ** constant: lex_error_id
LEX_ERROR_ID = 'LEX_ERROR'

# ** constant: parse_error_id
PARSE_ERROR_ID = 'PARSE_ERROR'

# ** constant: reader_build_failed_id
READER_BUILD_FAILED_ID = 'READER_BUILD_FAILED'

# ** constant: action_execution_failed_id
ACTION_EXECUTION_FAILED_ID = 'ACTION_EXECUTION_FAILED'

# *** functions

# ** function: resolve_grammar
def resolve_grammar(
        grammar_id: str,
        grammars: List[GrammarAggregate],
        service: Any) -> GrammarAggregate:
    '''
    Resolve a grammar by id from a collected catalogue.

    :param grammar_id: The target grammar identifier.
    :type grammar_id: str
    :param grammars: The unfiltered grammar catalogue.
    :type grammars: List[GrammarAggregate]
    :param service: The service raising on a miss.
    :type service: Any
    :return: The matching grammar aggregate.
    :rtype: GrammarAggregate
    '''

    # Find the first catalogue entry whose id matches.
    for grammar in grammars:
        if grammar.id == grammar_id:
            return grammar

    # Missing grammar is a structured failure before any ply call.
    ServiceError.raise_for(
        service,
        GRAMMAR_NOT_FOUND_ID,
        message=f'Grammar not found: {grammar_id}.',
        grammar_id=grammar_id,
    )


# ** function: unique_production_attr
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


# ** function: bind_callable
def bind_callable(
        module: Any,
        attr_name: str,
        value: Any,
        regex: Optional[str] = None) -> Any:
    '''
    Give a synthesized function the throwaway module as its __module__.

    :param module: The throwaway module the function will live on.
    :type module: Any
    :param attr_name: The attribute name being installed.
    :type attr_name: str
    :param value: The translated string or function.
    :type value: Any
    :param regex: Optional raw pattern attached as ``.regex`` for ply.
    :type regex: Optional[str]
    :return: The value, rebound onto the module when it is callable.
    :rtype: Any
    '''

    # Strings stay strings; only compiled functions need a real module.
    if not callable(value):
        return value

    # Copy the function into the module dict so inspect.getmodule can find it.
    value.__module__ = module.__name__
    if regex is not None:
        value.regex = regex
    module.__dict__[attr_name] = value
    return value


# ** function: install_token_attrs
def install_token_attrs(
        module: Any,
        selected_tokens: List[TokenRuleAggregate],
        rewrites: Optional[Dict[str, type]]) -> None:
    '''
    Install selected token attributes onto a throwaway module.

    :param module: The module receiving tokens and t_* attrs.
    :type module: Any
    :param selected_tokens: Tokens in selected order.
    :type selected_tokens: List[TokenRuleAggregate]
    :param rewrites: Optional action shorthand bindings.
    :type rewrites: Optional[Dict[str, type]]
    '''

    # Derive the tokens list in selected order, never sorted.
    module.tokens = RuleTranslator.derive_tokens(selected_tokens)

    # Translate each token and bind callables onto the module they live in.
    for rule in selected_tokens:
        attr_name, value = RuleTranslator.translate_token_rule(
            rule,
            rewrites=rewrites,
        )
        setattr(
            module,
            attr_name,
            bind_callable(
                module,
                attr_name,
                value,
                regex=rule.pattern if callable(value) else None,
            ),
        )


# ** function: install_production_attrs
def install_production_attrs(
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
        attr_name = unique_production_attr(rule.name, used)
        setattr(
            module,
            attr_name,
            bind_callable(module, attr_name, func),
        )


# ** function: make_t_error
def make_t_error(service: Any, grammar_id: str) -> Callable:
    '''
    Build a fail-loud t_error for an assembled lexer module.

    :param service: The service raising LEX_ERROR_ID.
    :type service: Any
    :param grammar_id: The target grammar identifier.
    :type grammar_id: str
    :return: The t_error function.
    :rtype: Callable
    '''

    # Raise with the same span keys a Lexeme carries.
    def t_error(t):
        value = t.value[0] if t.value else t.value
        ServiceError.raise_for(
            service,
            LEX_ERROR_ID,
            message=f'Illegal character {value!r}.',
            grammar_id=grammar_id,
            type='error',
            value=value,
            lineno=t.lineno,
            lexpos=t.lexpos,
        )

    # Return the installed error handler.
    return t_error


# ** function: make_p_error
def make_p_error(service: Any, grammar_id: str) -> Callable:
    '''
    Build a fail-loud p_error for an assembled parser module.

    :param service: The service raising PARSE_ERROR_ID.
    :type service: Any
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
            service,
            PARSE_ERROR_ID,
            message='Syntax error.',
            **kwargs,
        )

    # Return the installed error handler.
    return p_error


# ** function: wrap_action_failure
def wrap_action_failure(
        service: Any,
        grammar_id: str,
        error: Exception) -> None:
    '''
    Re-raise a compiled-action exception as ACTION_EXECUTION_FAILED_ID.

    :param service: The service raising the structured error.
    :type service: Any
    :param grammar_id: The target grammar identifier.
    :type grammar_id: str
    :param error: The originating exception.
    :type error: Exception
    '''

    # Recover the synthesized rule name from the traceback when present.
    rule_name = None
    traceback = error.__traceback__
    while traceback is not None:
        filename = traceback.tb_frame.f_code.co_filename
        if filename.startswith('<tiferet_ly:'):
            rule_name = filename[len('<tiferet_ly:'):-1]
            break
        traceback = traceback.tb_next

    # Raise the structured action-execution failure.
    ServiceError.raise_for(
        service,
        ACTION_EXECUTION_FAILED_ID,
        message=str(error),
        cause=error,
        grammar_id=grammar_id,
        rule_name=rule_name,
    )


# ** function: build_lexer_module
def build_lexer_module(
        service: Any,
        grammar: GrammarAggregate,
        grammars: List[GrammarAggregate],
        tokens: List[TokenRuleAggregate],
        rewrites: Optional[Dict[str, type]]) -> Tuple[Any, Any]:
    '''
    Select, translate, and assemble a throwaway ply lexer.

    :param service: The service assembling the lexer.
    :type service: Any
    :param grammar: The resolved target grammar.
    :type grammar: GrammarAggregate
    :param grammars: The unfiltered grammar catalogue.
    :type grammars: List[GrammarAggregate]
    :param tokens: The unfiltered token catalogue.
    :type tokens: List[TokenRuleAggregate]
    :param rewrites: Optional action shorthand bindings.
    :type rewrites: Optional[Dict[str, type]]
    :return: The assembled lexer and the throwaway module.
    :rtype: Tuple[Any, Any]
    '''

    # Select then translate in returned order.
    selected = GrammarRuleSelector.select_tokens(grammar, grammars, tokens)
    module = types.ModuleType('tiferet_ly_lexer')
    module.__file__ = __file__
    sys.modules[module.__name__] = module
    install_token_attrs(module, selected, rewrites)
    module.t_error = bind_callable(
        module,
        't_error',
        make_t_error(service, grammar.id),
    )

    # Rebuild every call; never write a lextab.
    try:
        lexer = lex.lex(module=module, optimize=0, reflags=0)
    except ServiceError:
        raise
    except Exception as error:
        ServiceError.raise_for(
            service,
            READER_BUILD_FAILED_ID,
            message=str(error),
            cause=error,
            grammar_id=grammar.id,
        )

    # Return the assembled lexer and the module it was built from.
    return lexer, module


# *** utils

# ** util: ply_lexer
class PlyLexer(LexerService):
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
        grammar = resolve_grammar(grammar_id, grammars, self)

        # Assemble a fresh lexer from the selected token set.
        lexer, _module = build_lexer_module(
            self,
            grammar,
            grammars,
            tokens,
            rewrites,
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
            wrap_action_failure(self, grammar_id, error)

        # Return the ply-free lexeme stream.
        return lexemes


# ** util: ply_parser
class PlyParser(ParserService):
    '''
    Assembles a throwaway ply parser from selected, translated rules and
    returns whatever the start-symbol action left in p[0].
    '''

    # * method: parse
    def parse(self,
            grammar_id: str,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            productions: List[ProductionRuleAggregate],
            text: str,
            rewrites: Optional[Dict[str, type]] = None) -> Any:
        '''
        Parse text against the selected rules for a grammar.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param productions: The unfiltered production catalogue.
        :type productions: List[ProductionRuleAggregate]
        :param text: The source text to parse.
        :type text: str
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :return: Whatever the start-symbol action left in p[0].
        :rtype: Any
        '''

        # Resolve the target before any ply call.
        grammar = resolve_grammar(grammar_id, grammars, self)

        # Build the parser's lexer from the same selected token set.
        lexer, module = build_lexer_module(
            self,
            grammar,
            grammars,
            tokens,
            rewrites,
        )

        # Select productions, install unique p_* attrs, and assemble yacc.
        selected = GrammarRuleSelector.select_productions(
            grammar,
            grammars,
            productions,
        )
        install_production_attrs(module, selected, rewrites)
        module.start = grammar.start
        module.p_error = bind_callable(
            module,
            'p_error',
            make_p_error(self, grammar.id),
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

        # Run the parser against the assembled lexer.
        try:
            return parser.parse(text, lexer=lexer)
        except ServiceError:
            raise
        except Exception as error:
            wrap_action_failure(self, grammar_id, error)
