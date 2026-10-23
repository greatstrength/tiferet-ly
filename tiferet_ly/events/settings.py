"""Tiferet-Ly Domain Event Settings"""

# *** imports

# ** core
import functools
import inspect
from typing import Callable, List

# ** infra
from tiferet.events.core import DomainEvent

# *** functions

# ** function: parameters_required
def parameters_required(param_names: List[str]) -> Callable:
    '''
    Bind positional and keyword arguments to the execute signature before
    the Tiferet required-parameter check, so a positional call is checked
    the same way as a keyword call.

    :param param_names: The list of required parameter names.
    :type param_names: List[str]
    :return: The decorator function.
    :rtype: Callable
    '''

    def decorator(method: Callable) -> Callable:
        '''
        Wrap a synchronous execute method with argument binding.

        :param method: The execute method to wrap.
        :type method: Callable
        :return: The wrapped method.
        :rtype: Callable
        '''

        # Read the signature once and wrap the Tiferet check around the method.
        signature = inspect.signature(method)
        validated = DomainEvent.parameters_required(param_names)(method)

        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):

            # Bind what was passed, without applying defaults.
            bound = signature.bind_partial(self, *args, **kwargs)

            # Rebuild the call as keywords, keeping extra keywords as given.
            call_kwargs = {}
            for name, value in list(bound.arguments.items())[1:]:
                if signature.parameters[name].kind is inspect.Parameter.VAR_KEYWORD:
                    call_kwargs.update(value)
                else:
                    call_kwargs[name] = value

            # Run the Tiferet check and the method on the keyword call.
            return validated(self, **call_kwargs)

        return wrapper

    return decorator
