TOOL_SCHEMA = {
    "name": "memory",
    "description": "主动将用户的关键信息（如爱好、身份、重大事件）存入长期记忆库中",
    "category": "core",
    "permission": "database",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": "记忆类型：'profile'(画像) 或 'preference'(偏好) 或 'event'(事件)"},
            "key": {"type": "string", "description": "键名（如'hobby', 'name'）"},
            "value": {"type": "string", "description": "对应的值"},
            "summary": {"type": "string", "description": "对于事件类型的简短总结"}
        },
        "required": ["type"]
    }
}

def execute(type=None, key=None, value=None, summary=None, memory_manager=None, **kwargs):
    if not type or not memory_manager:
        return {"success": False, "error": "缺少参数或 memory_manager 实例"}
    try:
        if type == "profile" and key and value:
            memory_manager.add_profile(key, value)
            return {"success": True, "data": {}, "message": f"画像 {key}={value} 已保存"}
        elif type == "preference" and key and value:
            memory_manager.add_preference("general", key, value)
            return {"success": True, "data": {}, "message": f"偏好 {key}={value} 已保存"}
        elif type == "event" and summary:
            memory_manager.add_event("general", summary, 0.8)
            return {"success": True, "data": {}, "message": f"事件已保存: {summary}"}
        return {"success": False, "error": "参数不完整，请检查 key, value 或 summary"}
    except Exception as e:
        return {"success": False, "error": str(e)}
