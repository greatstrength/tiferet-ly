"""Tiferet Ly Lexeme-Stream Layout Utility"""

# *** imports

# ** app
from tiferet_ly.mappers.lexeme import LexemeAggregate

# *** functions

# ** function: find_column
def find_column(lexpos: int, text: str) -> int:
    '''
    Resolve the 0-based column of a source position from the original text.

    Every character counts as one column, including a tab. The column is
    counted from the last newline before lexpos, or from the start of the
    text when there is none.

    :param lexpos: The source position to resolve.
    :type lexpos: int
    :param text: The original source text the position indexes into.
    :type text: str
    :return: The 0-based column.
    :rtype: int
    '''

    # Position zero is column zero. Do not search the text.
    if lexpos == 0:
        return 0

    # Search only the span before lexpos for the last newline.
    last_newline = text.rfind('\n', 0, lexpos)
    if last_newline < 0:
        return lexpos

    # Count the columns after that newline.
    return lexpos - last_newline - 1

# ** function: track_delimiter_depth
def track_delimiter_depth(lexeme_type: str, paren_depth: int, profile) -> int:
    '''
    Update the delimiter depth for one lexeme type.

    :param lexeme_type: The type name of the lexeme being walked.
    :type lexeme_type: str
    :param paren_depth: The delimiter depth before this lexeme.
    :type paren_depth: int
    :param profile: The layout profile in effect.
    :type profile: LayoutProfile
    :return: The updated delimiter depth.
    :rtype: int
    '''

    # Opens are checked first, so a type listed in both sets is an open.
    if lexeme_type in profile.open_delimiters:
        return paren_depth + 1

    # A close lowers the depth, never below zero.
    if lexeme_type in profile.close_delimiters:
        return max(0, paren_depth - 1)

    # Any other type leaves the depth unchanged.
    return paren_depth

# ** function: should_suppress_newline
def should_suppress_newline(lexeme_type: str, paren_depth: int, profile) -> bool:
    '''
    Decide whether a lexeme is a newline to drop inside an open delimiter.

    :param lexeme_type: The type name of the lexeme being walked.
    :type lexeme_type: str
    :param paren_depth: The delimiter depth for this lexeme.
    :type paren_depth: int
    :param profile: The layout profile in effect.
    :type profile: LayoutProfile
    :return: True only for a declared newline at nonzero depth with suppression on.
    :rtype: bool
    '''

    # A newline is dropped only inside an open delimiter, and only when asked.
    if not profile.suppress_newline_in_delimiters or paren_depth <= 0:
        return False

    # Only the newline this profile named is eligible. An unnamed token never matches.
    if lexeme_type != profile.newline_token:
        return False

    return True

# ** function: flush_trailing_dedents
def flush_trailing_dedents(current_col: int, profile, lexemes: list[LexemeAggregate]) -> list[LexemeAggregate]:
    '''
    Build the dedents for indentation still open at the end of the stream.

    :param current_col: The column tracked at the end of the walk.
    :type current_col: int
    :param profile: The layout profile in effect.
    :type profile: LayoutProfile
    :param lexemes: The original input stream, used only for span attribution.
    :type lexemes: list[LexemeAggregate]
    :return: The trailing dedent lexemes, in order.
    :rtype: list[LexemeAggregate]
    '''

    # Nothing is open, so nothing is flushed.
    if current_col <= 0:
        return []

    # Attribute every dedent to the last input lexeme, or to line 1, position 0.
    if lexemes:
        lineno = lexemes[-1].lineno
        lexpos = lexemes[-1].lexpos
    else:
        lineno = 1
        lexpos = 0

    # Build one dedent per open level. The value is left absent.
    return [
        LexemeAggregate.synthesize(profile.dedent_token, lineno, lexpos)
        for _ in range(current_col // profile.tab_size)
    ]

# ** function: apply_block
def apply_block(next_lexpos: int,
                lineno: int,
                current_col: int,
                saw_block_start: bool,
                profile,
                text: str,
                result: list[LexemeAggregate]) -> tuple[int, bool]:
    '''
    Append indent or dedent lexemes for one column change, in place.

    :param next_lexpos: The position of the upcoming lexeme.
    :type next_lexpos: int
    :param lineno: The line of the upcoming lexeme.
    :type lineno: int
    :param current_col: The column tracked before the upcoming lexeme.
    :type current_col: int
    :param saw_block_start: Whether a block start is pending.
    :type saw_block_start: bool
    :param profile: The layout profile in effect.
    :type profile: LayoutProfile
    :param text: The original source text.
    :type text: str
    :param result: The output stream that receives injected lexemes.
    :type result: list[LexemeAggregate]
    :return: The updated column and pending block-start flag.
    :rtype: tuple[int, bool]
    '''

    # Resolve the upcoming lexeme's column.
    new_col = find_column(next_lexpos, text)

    # A lower column appends one dedent per whole level exited. The flag stays.
    if new_col < current_col:
        for _ in range((current_col - new_col) // profile.tab_size):
            result.append(LexemeAggregate.synthesize(profile.dedent_token, lineno, next_lexpos))
        return new_col, saw_block_start

    # A higher column after a pending block start appends exactly one indent.
    if new_col > current_col and saw_block_start:
        result.append(LexemeAggregate.synthesize(profile.indent_token, lineno, next_lexpos))
        return new_col, False

    # Otherwise nothing is appended and the tracked column does not move.
    return current_col, saw_block_start

# ** function: inject_for_new_line
def inject_for_new_line(lexeme: LexemeAggregate,
                        paren_depth: int,
                        current_col: int,
                        saw_block_start: bool,
                        profile,
                        text: str,
                        result: list[LexemeAggregate]) -> tuple[int, bool, int, bool]:
    '''
    Handle the first lexeme of a new line, injecting layout lexemes ahead of it when due.

    :param lexeme: The first lexeme of the new line.
    :type lexeme: LexemeAggregate
    :param paren_depth: The delimiter depth for this lexeme.
    :type paren_depth: int
    :param current_col: The column tracked before this lexeme.
    :type current_col: int
    :param saw_block_start: Whether a block start is pending.
    :type saw_block_start: bool
    :param profile: The layout profile in effect.
    :type profile: LayoutProfile
    :param text: The original source text.
    :type text: str
    :param result: The output stream that receives appended lexemes.
    :type result: list[LexemeAggregate]
    :return: The column, the pending block-start flag, this lexeme's line, and whether it was already appended.
    :rtype: tuple[int, bool, int, bool]
    '''

    # A newline lexeme is appended unchanged, with nothing injected ahead of it.
    if profile.newline_token is not None and lexeme.type == profile.newline_token:
        result.append(lexeme)
        return current_col, saw_block_start, lexeme.lineno, True

    # Outside delimiters, and not on a close, resolve the column change.
    if paren_depth == 0 and lexeme.type not in profile.close_delimiters:
        current_col, saw_block_start = apply_block(
            lexeme.lexpos,
            lexeme.lineno,
            current_col,
            saw_block_start,
            profile,
            text,
            result,
        )

        # A block token re-arms the flag after its own column change.
        if lexeme.type in profile.block_tokens:
            saw_block_start = True

    # The caller appends this lexeme.
    return current_col, saw_block_start, lexeme.lineno, False

# *** utils

# ** util: layout_filter
class LayoutFilter:
    '''
    Reshape a recognized lexeme stream by a declared layout profile.

    A language whose blocks are marked by indentation needs indent and
    dedent lexemes that no pattern can match. The filter adds them from
    column changes and drops line breaks inside open delimiters, without
    lexing, parsing, or reading a grammar.
    '''

    # * method: apply (static)
    @staticmethod
    def apply(lexemes: list[LexemeAggregate], profile, text: str) -> list[LexemeAggregate]:
        '''
        Apply a layout profile to an already-produced lexeme stream.

        The stream is reshaped, not re-matched: text is read only to
        resolve columns. The input list is not mutated.

        :param lexemes: The already-produced lexeme stream.
        :type lexemes: list[LexemeAggregate]
        :param profile: The layout profile in effect.
        :type profile: LayoutProfile
        :param text: The original source text.
        :type text: str
        :return: A new stream with indents and dedents injected and suppressed newlines dropped.
        :rtype: list[LexemeAggregate]
        '''

        # Start every call from a clean state.
        paren_depth = 0
        saw_block_start = False
        current_col = 0
        prev_lineno = 0
        result = []

        # Walk the stream in order.
        for lexeme in lexemes:
            # Track delimiter depth, then arm a pending block start.
            paren_depth = track_delimiter_depth(lexeme.type, paren_depth, profile)
            if lexeme.type in profile.block_tokens:
                saw_block_start = True

            # Drop a newline inside an open delimiter. The line is not advanced.
            if should_suppress_newline(lexeme.type, paren_depth, profile):
                continue

            # The first lexeme of a later line may receive injected lexemes.
            already_appended = False
            if lexeme.lineno > prev_lineno:
                current_col, saw_block_start, prev_lineno, already_appended = inject_for_new_line(
                    lexeme,
                    paren_depth,
                    current_col,
                    saw_block_start,
                    profile,
                    text,
                    result,
                )

            # Append the original lexeme object unless it is already in place.
            if not already_appended:
                result.append(lexeme)

        # Close any indentation still open at the end of the stream.
        result.extend(flush_trailing_dedents(current_col, profile, lexemes))

        # Return the reshaped stream.
        return result
