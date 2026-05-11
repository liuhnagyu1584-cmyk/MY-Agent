from typing import cast
from openai.types.chat import ChatCompletionToolParam

from . import get_current_location
from . import get_current_time
from . import web_search

TOOL_DEFINITIONS: list[ChatCompletionToolParam] = cast(
    list[ChatCompletionToolParam],
    [
        get_current_time.definition,
        get_current_location.definition,
        web_search.definition,
    ],
)

TOOL_HANDLERS = {
    "get_current_time": get_current_time.handler,
    "get_current_location": get_current_location.handler,
    "web_search": web_search.handler,
}
