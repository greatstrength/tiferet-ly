"""Tiferet-Ly Keyed Catalogue Entry Helpers"""

# *** imports

# ** core
from typing import Any, Dict, List

# *** functions

# ** function: expand_keyed_entries
def expand_keyed_entries(entries: List[Any], key_field: str = 'name') -> List[Dict[str, Any]]:
    '''
    Expand a YAML-style sequence of single-key mappings into flat dicts.

    Each entry shaped ``{name: {body...}}`` becomes
    ``{key_field: name, **body}``. Iteration is straight and
    order-preserving; no sorting or grouping is performed.

    :param entries: The raw catalogue entries.
    :type entries: List[Any]
    :param key_field: The field name the single mapping key is injected under.
    :type key_field: str
    :return: The expanded, flat-dict entries in declared order.
    :rtype: List[Dict[str, Any]]
    '''

    # Expand each single-key YAML mapping into a flat dict.
    expanded: List[Dict[str, Any]] = []
    for entry in entries or []:
        ((key, body),) = entry.items()
        expanded.append({
            key_field: key,
            **(body or {}),
        })

    # Return the expanded entries.
    return expanded


# ** function: wrap_keyed_entries
def wrap_keyed_entries(entries: List[Dict[str, Any]], key_field: str = 'name') -> List[Dict[str, Any]]:
    '''
    Re-wrap flat dicts into a sequence of single-key mappings for YAML write.

    Each entry shaped ``{key_field: name, **body}`` becomes
    ``{name: body}``. Iteration is straight and order-preserving.

    :param entries: The flat-dict catalogue entries.
    :type entries: List[Dict[str, Any]]
    :param key_field: The field name holding the mapping key value.
    :type key_field: str
    :return: The re-wrapped single-key mapping entries in declared order.
    :rtype: List[Dict[str, Any]]
    '''

    # Re-wrap each flat dict into a single-key mapping.
    wrapped: List[Dict[str, Any]] = []
    for entry in entries or []:
        key = entry[key_field]
        body = {
            field: value
            for field, value in entry.items()
            if field != key_field
        }
        wrapped.append({
            key: body,
        })

    # Return the wrapped entries.
    return wrapped
