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
    Thin Feature step that turns a parse result into a string.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['result'])
    def execute(self, result: Any, **kwargs) -> str:
        '''
        Render the parse result as a string.

        :param result: The raw parse result.
        :type result: Any
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The rendered string.
        :rtype: str
        '''

        # Delegate string strategy to the renderer; do not walk the value here.
        return ResultRenderer.render(result)


# ** event: return_result
class ReturnResult(DomainEvent):
    '''
    Thin Feature step that promotes the raw parse result to request.result.
    '''

    # * method: execute
    @DomainEvent.parameters_required(['result'])
    def execute(self, result: Any, **kwargs) -> Any:
        '''
        Return the parse result unchanged.

        :param result: The raw parse result.
        :type result: Any
        :param kwargs: Additional keyword arguments.
        :type kwargs: dict
        :return: The same result.
        :rtype: Any
        '''

        # Promote $r.result onto request.result without converting it.
        return result
