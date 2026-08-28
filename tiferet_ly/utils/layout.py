"""Tiferet-Ly Lexeme-Stream Layout Utility"""

# *** imports

# ** core
from typing import List, Tuple

# ** app
from ..domain.layout import LayoutProfile
from ..mappers.lexeme import LexemeAggregate

# *** functions

# ** function: find_column
def find_column(lexpos: int, text: str) -> int:
    '''
    Compute the 0-based column of a lexpos from the original source text.

    :param lexpos: The source position to resolve a column for.
    :type lexpos: int
    :param text: The original source text the lexpos indexes into.
    :type text: str
    :return: The 0-based column offset.
    :rtype: int
    '''

    # A lexpos of zero is always column zero; no lookup needed.
    if lexpos == 0:
        return 0

    # Column is the distance from the previous newline, or the raw
    # lexpos when there is no preceding newline at all.
    last_newline = text.rfind('\n', 0, lexpos)
    if last_newline < 0:
        return lexpos

    return lexpos - last_newline - 1

# ** function: track_delimiter_depth
def track_delimiter_depth(lexeme_type: str, paren_depth: int, profile: LayoutProfile) -> int:
    '''
    Update tracked delimiter depth for one lexeme's type.

    :param lexeme_type: The type name of the lexeme being processed.
    :type lexeme_type: str
    :param paren_depth: The delimiter depth tracked before this lexeme.
    :type paren_depth: int
    :param profile: The declared layout profile in effect.
    :type profile: LayoutProfile
    :return: The updated delimiter depth.
    :rtype: int
    '''

    # An open delimiter increases depth; a close delimiter decreases it, never below zero.
    if lexeme_type in profile.open_delimiters:
        return paren_depth + 1
    if lexeme_type in profile.close_delimiters:
        return max(0, paren_depth - 1)

    return paren_depth

# ** function: should_suppress_newline
def should_suppress_newline(lexeme_type: str, paren_depth: int, profile: LayoutProfile) -> bool:
    '''
    Determine whether one newline-typed lexeme should be dropped from the output.

    :param lexeme_type: The type name of the lexeme being processed.
    :type lexeme_type: str
    :param paren_depth: The delimiter depth tracked for this lexeme.
    :type paren_depth: int
    :param profile: The declared layout profile in effect.
    :type profile: LayoutProfile
    :return: True when the lexeme should be dropped from the output stream.
    :rtype: bool
    '''

    return (
        profile.suppress_newline_in_delimiters
        and profile.newline_token is not None
        and lexeme_type == profile.newline_token
        and paren_depth > 0
    )

# ** function: flush_trailing_dedents
def flush_trailing_dedents(
        current_col: int,
        profile: LayoutProfile,
        lexemes: List[LexemeAggregate]) -> List[LexemeAggregate]:
    '''
    Build the trailing dedent lexemes for indentation still open at end of stream.

    :param current_col: The column tracked at the end of the walk.
    :type current_col: int
    :param profile: The declared layout profile in effect.
    :type profile: LayoutProfile
    :param lexemes: The original input lexeme stream, for trailing span attribution.
    :type lexemes: List[LexemeAggregate]
    :return: The synthesized trailing dedent lexemes, in order.
    :rtype: List[LexemeAggregate]
    '''

    # No indentation left open; nothing to flush.
    if current_col <= 0:
        return []

    # Attribute every flushed dedent to the last real lexeme's own span.
    dedent_count = current_col // profile.tab_size
    last = lexemes[-1] if lexemes else None
    lineno = last.lineno if last is not None else 1
    lexpos = last.lexpos if last is not None else 0

    return [
        LexemeAggregate.synthesize(profile.dedent_token, lineno, lexpos)
        for _ in range(dedent_count)
    ]

# ** function: apply_block
def apply_block(
        next_lexpos: int,
        lineno: int,
        current_col: int,
        saw_block_start: bool,
        profile: LayoutProfile,
        text: str,
        result: List[LexemeAggregate]) -> Tuple[int, bool]:
    '''
    Inject indent/dedent lexemes for one column change, appending in place.

    :param next_lexpos: The lexpos of the upcoming lexeme.
    :type next_lexpos: int
    :param lineno: The line number the injected lexeme(s) are attributed to.
    :type lineno: int
    :param current_col: The column tracked before this lexeme.
    :type current_col: int
    :param saw_block_start: Whether a block-introducing lexeme is pending.
    :type saw_block_start: bool
    :param profile: The declared layout profile in effect.
    :type profile: LayoutProfile
    :param text: The original source text.
    :type text: str
    :param result: The output lexeme list injected lexemes are appended to.
    :type result: List[LexemeAggregate]
    :return: The updated tracked column and pending block-start flag.
    :rtype: Tuple[int, bool]
    '''

    # Resolve the upcoming lexeme's column.
    new_col = find_column(next_lexpos, text)

    # Column decreased — inject one dedent per indentation level exited.
    if new_col < current_col:
        dedent_count = (current_col - new_col) // profile.tab_size
        for _ in range(dedent_count):
            result.append(LexemeAggregate.synthesize(profile.dedent_token, lineno, next_lexpos))
        return new_col, saw_block_start

    # Column increased — inject one indent only if a block start is pending.
    if new_col > current_col:
        if saw_block_start:
            result.append(LexemeAggregate.synthesize(profile.indent_token, lineno, next_lexpos))
            return new_col, False
        return current_col, saw_block_start

    # No column change; state is unchanged.
    return current_col, saw_block_start

# ** function: inject_for_new_line
def inject_for_new_line(
        lexeme: LexemeAggregate,
        paren_depth: int,
        current_col: int,
        saw_block_start: bool,
        profile: LayoutProfile,
        text: str,
        result: List[LexemeAggregate]) -> Tuple[int, bool, int, bool]:
    '''
    Handle the first lexeme of a new source line: append a newline lexeme
    as-is, or inject indent/dedent lexemes ahead of any other lexeme.

    :param lexeme: The lexeme beginning a new source line.
    :type lexeme: LexemeAggregate
    :param paren_depth: The delimiter depth tracked for this lexeme.
    :type paren_depth: int
    :param current_col: The column tracked before this lexeme.
    :type current_col: int
    :param saw_block_start: Whether a block-introducing lexeme is pending.
    :type saw_block_start: bool
    :param profile: The declared layout profile in effect.
    :type profile: LayoutProfile
    :param text: The original source text.
    :type text: str
    :param result: The output lexeme list injected/appended lexemes go to.
    :type result: List[LexemeAggregate]
    :return: The updated column, pending block-start flag, this lexeme's
        own line number, and whether this lexeme was already appended.
    :rtype: Tuple[int, bool, int, bool]
    '''

    lexeme_type = lexeme.type

    # A newline lexeme is appended as-is; injection follows it, not precedes it.
    if profile.newline_token is not None and lexeme_type == profile.newline_token:
        result.append(lexeme)
        return current_col, saw_block_start, lexeme.lineno, True

    # Being inside an open delimiter, or closing one, never triggers injection.
    if paren_depth == 0 and lexeme_type not in profile.close_delimiters:
        current_col, saw_block_start = apply_block(
            lexeme.lexpos,
            lexeme.lineno,
            current_col,
            saw_block_start,
            profile,
            text,
            result,
        )

        # Re-arm a block start this same lexeme itself introduces.
        if lexeme_type in profile.block_tokens:
            saw_block_start = True

    return current_col, saw_block_start, lexeme.lineno, False

# *** utils

# ** util: layout_filter
class LayoutFilter:
    '''
    Applies a declared LayoutProfile to an already-produced, ply-free
    lexeme stream: injects synthetic indent/dedent lexemes on column
    change and suppresses a newline lexeme while delimiter depth is
    nonzero.
    '''

    # * method: apply (static)
    @staticmethod
    def apply(
            lexemes: List[LexemeAggregate],
            profile: LayoutProfile,
            text: str) -> List[LexemeAggregate]:
        '''
        Apply a declared layout profile to an already-produced lexeme stream.

        :param lexemes: The ply-free lexeme stream a PlyLexer already produced.
        :type lexemes: List[LexemeAggregate]
        :param profile: The declared layout profile in effect for the grammar.
        :type profile: LayoutProfile
        :param text: The original source text, for column resolution.
        :type text: str
        :return: The lexeme stream with indent/dedent lexemes injected and
            delimiter-suppressed newlines dropped.
        :rtype: List[LexemeAggregate]
        '''

        # State carried across the walk.
        paren_depth = 0
        saw_block_start = False
        current_col = 0
        prev_lineno = 0
        result: List[LexemeAggregate] = []

        # Walk the already-produced stream in order.
        for lexeme in lexemes:
            lexeme_type = lexeme.type

            # Track delimiter depth and a pending block start for this lexeme.
            paren_depth = track_delimiter_depth(lexeme_type, paren_depth, profile)
            if lexeme_type in profile.block_tokens:
                saw_block_start = True

            # Drop a newline occurrence while delimiter depth is nonzero.
            if should_suppress_newline(lexeme_type, paren_depth, profile):
                continue

            # Inject indent/dedent lexemes ahead of the first lexeme of a new line,
            # or append this lexeme directly when it is not one.
            already_appended = False
            if lexeme.lineno > prev_lineno:
                current_col, saw_block_start, prev_lineno, already_appended = inject_for_new_line(
                    lexeme, paren_depth, current_col, saw_block_start, profile, text, result,
                )
            if not already_appended:
                result.append(lexeme)

        # Flush any remaining open indentation levels at end of stream.
        result.extend(flush_trailing_dedents(current_col, profile, lexemes))

        # Return the filtered, layout-annotated lexeme stream.
        return result
