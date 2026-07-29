TOOL_SCHEMA = {
    "name": "pet_state",
    "description": "获取当前桌宠（也就是你）自身的状态信息（如是否在睡觉、走路等）",
    "category": "core",
    "permission": "none",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

def execute(pet_instance=None, **kwargs):
    if not pet_instance:
        return {"success": False, "error": "缺少 pet_instance 实例"}
    try:
        data = {
            "is_sleeping": pet_instance.is_sleeping,
            "is_walking": pet_instance.is_walking,
            "is_following_mouse": pet_instance.is_following_mouse,
            "position": f"({pet_instance.x()}, {pet_instance.y()})"
        }
        return {"success": True, "data": data, "message": "获取成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}
