TOOL_SCHEMA = {
    "name": "system",
    "description": "读取电脑系统的状态（CPU、内存等使用率）",
    "category": "system",
    "permission": "system_read",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

def execute(**kwargs):
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        batt_str = f"{battery.percent}%" if battery else "台式机/未知"
        data = {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "battery": batt_str
        }
        return {"success": True, "data": data, "message": "获取成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}
