"""Tiferet Ly Mapper Core"""

# *** imports

# ** app
from tiferet import Aggregate

# *** functions

# ** function: expand_keyed_entries
def expand_keyed_entries(entries: list[dict[str, dict]]) -> list[dict]:
    '''
    Flatten a catalogue of single-key mappings into named dicts.

    Declared order is preserved. The mapping key becomes ``name`` and
    wins when the body already carries that key. The input is not mutated.

    :param entries: The keyed catalogue entries, in declared order.
    :type entries: list[dict[str, dict]]
    :return: A new list of flat dicts.
    :rtype: list[dict]
    '''

    # Copy each single-key body in order, letting the key win as name.
    expanded = []
    for entry in entries:
        (key, body), = entry.items()
        expanded.append({**body, 'name': key})

    # Return a new list and leave the input untouched.
    return expanded

# ** function: wrap_keyed_entries
def wrap_keyed_entries(entries: list[dict]) -> list[dict[str, dict]]:
    '''
    Fold flat named dicts back into single-key catalogue entries.

    Declared order is preserved. ``action`` is copied only when the flat
    dict already has it. The input is not mutated.

    :param entries: The flat named dicts, in declared order.
    :type entries: list[dict]
    :return: A new list of one-key catalogue entries.
    :rtype: list[dict[str, dict]]
    '''

    # Wrap each flat dict in order, omitting name from the body.
    wrapped = []
    for entry in entries:
        name = entry['name']
        body = {
            key: value
            for key, value in entry.items()
            if key != 'name'
        }
        wrapped.append({name: body})

    # Return a new list and leave the input untouched.
    return wrapped

# *** classes

# ** class: named_rule_aggregate
class NamedRuleAggregate(Aggregate):
    '''
    Shared mutation for a named rule's identity.

    Renaming and grammar reassignment change the stored fields only.
    Neither call checks uniqueness or resolves a grammar.
    '''

    # * method: rename
    def rename(self, name: str) -> None:
        '''
        Rename the rule.

        :param name: The new rule name.
        :type name: str
        :return: None
        :rtype: None
        '''

        # Assign the name without checking uniqueness.
        self.name = name

    # * method: reassign_grammar
    def reassign_grammar(self, grammar_id: str) -> None:
        '''
        Reassign the grammar that owns the rule.

        :param grammar_id: The new grammar identifier.
        :type grammar_id: str
        :return: None
        :rtype: None
        '''

        # Assign the grammar id without resolving it.
        self.grammar_id = grammar_id
