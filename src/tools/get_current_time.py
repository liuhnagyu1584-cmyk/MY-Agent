from datetime import datetime
from typing import Any
import pytz

definition = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前系统的实时时间、日期和星期。当用户询问'现在几点'、'今天几号'，或者需要基于当前时间进行逻辑计算（如判断是否逾期、计算倒计时）时，必须调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "可选参数。IANA 时区格式字符串，例如 'Asia/Shanghai'、'America/New_York'。如果不提供，默认使用 'Asia/Shanghai'。",
                }
            },
        },
        "required": [],
    },
}


def handler(timezone: str = "Asia/Shanghai") -> str:
    """
    获取指定时区的当前实时时间。
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M:%S %A") + f" ({timezone})"
    except Exception as e:
        return f"Error: 无法获取时区 {timezone} 的时间，请确认时区格式是否正确。"
