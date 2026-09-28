"""Tiferet Ly Render Events"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet.events.core import DomainEvent
from tiferet_ly.utils.render import ResultRenderer

# *** events

# ** event: render_result
class RenderResult(DomainEvent):
    '''
    Choose whether a finished result is shown or handed back as itself.

    Rendering is a flag on the terminal read, not a write. False or an
    absent flag keeps the original result object.
    '''

    # * method: execute
    def execute(
            self,
            result: Any,
            render_result: bool = False,
            **kwargs,
        ) -> Any:
        '''
        Render the result when asked, otherwise return it unchanged.

        :param result: The result to render or return.
        :type result: Any
        :param render_result: When true, render the result. Defaults to False.
        :type render_result: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The rendered string, or the original result.
        :rtype: Any
        '''

        # True renders. False and an absent flag keep the same object.
        if render_result:
            return ResultRenderer.render(result)

        # Do not copy, save, or delete.
        return result
