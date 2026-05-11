from ddgs import DDGS

MAX_SNIPPET_LEN = 200  # 摘要最大长度

definition = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "联网搜索最新信息。当需要获取实时数据、新闻、事实核查，或用户明确要求搜索时，必须调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，建议使用简洁精准的英文或中文词条。",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量上限，默认 5，最大 10。精简结果有助于 LLM 高效处理。",
                },
            },
            "required": ["query"],
        },
    },
}


def handler(query: str, max_results: int = 5) -> str:
    max_results = min(max(max_results, 1), 10)

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return f"[web_search 错误] 搜索请求失败: {e}"

    if not results:
        return f'未找到与 "{query}" 相关的结果，请尝试更换关键词。'

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "无标题")
        href = r.get("href", "")
        body = r.get("body", "")
        snippet = body[:MAX_SNIPPET_LEN] + (
            "..." if len(body) > MAX_SNIPPET_LEN else ""
        )

        lines.append(f"{i}. {title}")
        lines.append(f"   URL: {href}")
        lines.append(f"   摘要: {snippet}")

    return "\n".join(lines)
