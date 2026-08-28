"""Tiferet-Ly Shared PLY Reader Utility"""

# *** imports

# ** core
import sys
import types
from typing import Any, Callable, Dict, List, Optional, Tuple

# ** infra
from ply import lex

# ** app
from tiferet.interfaces.core import ServiceError
from ..mappers.grammar import GrammarAggregate
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

# ** constant: parse_input_invalid_id
PARSE_INPUT_INVALID_ID = 'PARSE_INPUT_INVALID'

# *** utils

# ** util: ply_reader
class PlyReader:
    '''
    Shared helper surface for throwaway ply lexer and parser assembly.
    '''

    # * method: resolve_grammar
    def resolve_grammar(
            self,
            grammar_id: str,
            grammars: List[GrammarAggregate]) -> GrammarAggregate:
        '''
        Resolve a grammar by id from a collected catalogue.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :return: The matching grammar aggregate.
        :rtype: GrammarAggregate
        '''

        # Find the first catalogue entry whose id matches.
        for grammar in grammars:
            if grammar.id == grammar_id:
                return grammar

        # Missing grammar is a structured failure before any ply call.
        ServiceError.raise_for(
            self,
            GRAMMAR_NOT_FOUND_ID,
            message=f'Grammar not found: {grammar_id}.',
            grammar_id=grammar_id,
        )

    # * method: bind_callable (static)
    @staticmethod
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

    # * method: make_t_error
    def make_t_error(self, grammar_id: str) -> Callable:
        '''
        Build a fail-loud t_error for an assembled lexer module.

        :param grammar_id: The target grammar identifier.
        :type grammar_id: str
        :return: The t_error function.
        :rtype: Callable
        '''

        # Raise with the same span keys a Lexeme carries.
        def t_error(t):
            value = t.value[0] if t.value else t.value
            ServiceError.raise_for(
                self,
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

    # * method: wrap_action_failure
    def wrap_action_failure(self, grammar_id: str, error: Exception) -> None:
        '''
        Re-raise a compiled-action exception as ACTION_EXECUTION_FAILED_ID.

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
            self,
            ACTION_EXECUTION_FAILED_ID,
            message=str(error),
            cause=error,
            grammar_id=grammar_id,
            rule_name=rule_name,
        )

    # * method: select_token_names
    def select_token_names(
            self,
            grammar: GrammarAggregate,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate]) -> List[str]:
        '''
        Derive a grammar's selected token names with no lexer built.

        The completeness-satisfying half of build_lexer_module with the
        lexer-building half removed: no regex compilation, no t_*
        installation, no lex.lex() call. Includes a synthetic token's
        name exactly as derive_tokens already does for the text path.

        :param grammar: The resolved target grammar.
        :type grammar: GrammarAggregate
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :return: Bare, unprefixed token names in selected order.
        :rtype: List[str]
        '''

        # Select then derive names only; no installation, no lexer.
        selected = GrammarRuleSelector.select_tokens(grammar, grammars, tokens)
        return RuleTranslator.derive_tokens(selected)

    # * method: new_module (static)
    @staticmethod
    def new_module(name: str) -> Any:
        '''
        Construct a throwaway module registered in sys.modules.

        Shared plumbing for any assembled reader that needs a module
        object PLY (or a caller's own attribute installation) can bind
        callables onto and inspect.getmodule can resolve.

        :param name: The module name to register.
        :type name: str
        :return: The constructed, registered module.
        :rtype: Any
        '''

        # Register the throwaway module so inspect.getmodule can find it.
        module = types.ModuleType(name)
        module.__file__ = __file__
        sys.modules[module.__name__] = module
        return module

    # * method: install_token_attrs
    def install_token_attrs(
            self,
            module: Any,
            selected_tokens: List[TokenRuleAggregate],
            rewrites: Optional[Dict[str, type]]) -> None:
        '''
        Install selected token attributes onto a throwaway module.

        A synthetic rule translates to None and is skipped here — it
        contributes no t_* attribute, though its name is already present
        in module.tokens via derive_tokens below.

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
            translated = RuleTranslator.translate_token_rule(
                rule,
                rewrites=rewrites,
            )

            # A synthetic rule translates to None; nothing to install for it.
            if translated is None:
                continue

            attr_name, value = translated
            setattr(
                module,
                attr_name,
                self.bind_callable(
                    module,
                    attr_name,
                    value,
                    regex=rule.pattern if callable(value) else None,
                ),
            )

    # * method: build_lexer_module
    def build_lexer_module(
            self,
            grammar: GrammarAggregate,
            grammars: List[GrammarAggregate],
            tokens: List[TokenRuleAggregate],
            rewrites: Optional[Dict[str, type]],
            t_error: Any) -> Tuple[Any, Any]:
        '''
        Select, translate, and assemble a throwaway ply lexer.

        :param grammar: The resolved target grammar.
        :type grammar: GrammarAggregate
        :param grammars: The unfiltered grammar catalogue.
        :type grammars: List[GrammarAggregate]
        :param tokens: The unfiltered token catalogue.
        :type tokens: List[TokenRuleAggregate]
        :param rewrites: Optional action shorthand bindings.
        :type rewrites: Optional[Dict[str, type]]
        :param t_error: The fail-loud t_error handler to install.
        :type t_error: Any
        :return: The assembled lexer and the throwaway module.
        :rtype: Tuple[Any, Any]
        '''

        # Select then translate in returned order.
        selected = GrammarRuleSelector.select_tokens(grammar, grammars, tokens)
        module = self.new_module('tiferet_ly_lexer')
        self.install_token_attrs(module, selected, rewrites)
        module.t_error = self.bind_callable(module, 't_error', t_error)

        # Install the declared ignore pattern as PLY's own t_ignore convention.
        if grammar.ignore is not None:
            module.t_ignore = grammar.ignore

        # Rebuild every call; never write a lextab.
        try:
            lexer = lex.lex(module=module, optimize=0, reflags=0)
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

        # Return the assembled lexer and the module it was built from.
        return lexer, module
