"""Tiferet-Ly Render Domain Events"""

# *** imports

# ** core
from typing import Any

# ** app
from tiferet.events.core import DomainEvent
from ..utils.render import ResultRenderer

# *** events

# ** event: render_result
class RenderResult(DomainEvent):
    '''
    Thin Feature step that optionally turns a parse result into a string.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['result'])
    def execute(self,
            result: Any,
            render_result: bool = False,
            **kwargs) -> Any:
        '''
        Render the parse result as a string when asked; otherwise pass it through.

        :param result: The raw parse result.
        :type result: Any
        :param render_result: When true, return a string; otherwise the raw result.
        :type render_result: bool
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The rendered string, or the unchanged result.
        :rtype: Any
        '''

        # Pass the raw value through when the caller did not ask to render.
        if not render_result:
            return result

        # Delegate string strategy to the renderer; do not walk the value here.
        return ResultRenderer.render(result)
