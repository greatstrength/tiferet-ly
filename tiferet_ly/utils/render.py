"""Tiferet Ly Result Renderer"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet_ly.mappers.ast import AstNodeAggregate

# *** utils

# ** util: result_renderer
class ResultRenderer:
    '''
    Turn a parse result into a string without drawing a foreign tree.

    A string is already rendered. An aggregate draws itself. Every other
    value uses its ordinary string form, even when it has kind and children.
    '''

    # * method: render (static)
    @staticmethod
    def render(value: Any) -> str:
        '''
        Render one value as a string.

        :param value: The value to render.
        :type value: Any
        :return: The rendered string.
        :rtype: str
        '''

        # A string is already rendered. Return it unchanged.
        if isinstance(value, str):
            return value

        # An aggregate draws itself. Do not walk a foreign tree.
        if isinstance(value, AstNodeAggregate):
            return value.format()

        # Every other value uses its ordinary string form.
        return str(value)
