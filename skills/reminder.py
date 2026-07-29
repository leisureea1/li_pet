TOOL_SCHEMA = {
    "name": "reminder",
    "description": "设置一个定时提醒任务",
    "category": "utility",
    "permission": "none",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {
            "seconds": {"type": "integer", "description": "多少秒之后提醒"},
            "message": {"type": "string", "description": "提醒的内容"}
        },
        "required": ["seconds", "message"]
    }
}

def execute(seconds=None, message=None, pet_instance=None, **kwargs):
    if not seconds or not message:
        return {"success": False, "error": "秒数和提醒内容不能为空"}
    try:
        # ChatThread will interpret this specific action and schedule the timer in the main thread
        return {"success": True, "data": {"action": "set_reminder", "seconds": seconds, "message": message}, "message": f"将在 {seconds} 秒后提醒: {message}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
