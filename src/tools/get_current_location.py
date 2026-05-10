import geocoder

definition = {
    "type": "function",
    "function": {
        "name": "get_current_location",
        "description": "获取用户当前设备所在的地理位置信息（基于 IP ），返回城市名称及经纬度坐标。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "required": [],
    },
}


def handler() -> str:
    """
    获取当前城市经纬度。
    """
    try:
        g = geocoder.ip("me")
        if g.ok:
            return f"城市: {g.city}, 经纬度: {g.latlng}"
        else:
            return "Error: 无法通过当前网络获取位置信息。"
    except Exception as e:
        return f"Error: 获取位置时发生异常 {e}"
