from sublime_plugin import EventListener
from sublime import OP_EQUAL
from sublime import OP_NOT_EQUAL
from NeoVintageous.nv.settings import get_mode
from NeoVintageous.nv.utils import is_view

def _check_query_context_value(value: bool, operator: int, operand: bool, match_all: bool) -> bool:
    if operator == OP_EQUAL:
        if operand is True:
            return value
        elif operand is False:
            return not value
    elif operator is OP_NOT_EQUAL:
        if operand is True:
            return not value
        elif operand is False:
            return value

    return False


def _is_normal_mode(view, operator: int = OP_EQUAL, operand: bool = True, match_all: bool = False) -> bool:
    return _check_query_context_value(
        (get_mode(view) == 'mode_normal' and is_view(view)),
        operator,
        operand,
        match_all
    )

_query_contexts = {
    'my_vi_normal_mode': _is_normal_mode
}


class MyNeoVintageousEvents(EventListener): 
    def on_query_context(self, view, key: str, operator: int, operand, match_all: bool):
        # Called when determining to trigger a key binding with the given context key.
        #
        # If the plugin knows how to respond to the context, it should return
        # either True of False. If the context is unknown, it should return
        # None.
        #
        # Params:
        #   operand: str|bool
        #
        # Returns:
        #   bool: If the context is known.
        #   None: If the context is unknown.

        try:
            return _query_contexts[key](view, operator, operand, match_all)
        except KeyError:
            pass
