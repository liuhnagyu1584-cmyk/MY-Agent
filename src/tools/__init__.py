from typing import cast
from openai.types.chat import ChatCompletionToolParam

from . import get_current_location
from . import get_current_time
from . import web_search
from . import read_file
from . import write_file
from . import delete_file
from . import edit_file
from . import list_directory

TOOL_DEFINITIONS: list[ChatCompletionToolParam] = cast(
    list[ChatCompletionToolParam],
    [
        get_current_time.definition,
        get_current_location.definition,
        web_search.definition,
        read_file.definition,
        write_file.definition,
        delete_file.definition,
        edit_file.definition,
        list_directory.definition,
    ],
)

TOOL_HANDLERS = {
    "get_current_time": get_current_time.handler,
    "get_current_location": get_current_location.handler,
    "web_search": web_search.handler,
    "read_file": read_file.handler,
    "write_file": write_file.handler,
    "delete_file": delete_file.handler,
    "edit_file": edit_file.handler,
    "list_directory": list_directory.handler,

}
