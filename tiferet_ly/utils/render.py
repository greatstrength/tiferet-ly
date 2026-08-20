"""Tiferet-Ly Result Rendering Utility"""

# *** imports

# ** core
from typing import Any

# ** app
from ..mappers.ast import AstNodeAggregate

# *** utils

# ** util: result_renderer
class ResultRenderer:
    '''
    Turns a parse result into a string so the framework never has to
    walk a tree. Only AstNodeAggregate formats itself; everything else
    is already a string or falls back to str(value).
    '''

    # * method: render (static)
    @staticmethod
    def render(value: Any) -> str:
        '''
        Render a parse result as a string.

        :param value: The raw parse result.
        :type value: Any
        :return: The string rendering.
        :rtype: str
        '''

        # A string is already done; do not re-quote it.
        if isinstance(value, str):
            return value

        # The optional generic tree formats itself.
        if isinstance(value, AstNodeAggregate):
            return value.format()

        # Every other value, including a foreign tree, uses str(value).
        return str(value)
