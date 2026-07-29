TOOL_SCHEMA = {
    "name": "music",
    "description": "查询当前电脑正在播放的音乐或媒体信息（纯查询，不控制）",
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
        import sys
        if sys.platform != 'win32':
            return {"success": False, "error": "仅支持 Windows 系统"}
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        import asyncio
        async def fetch():
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if session:
                info = await session.try_get_media_properties_async()
                title = info.title if info.title else "未知"
                artist = info.artist if info.artist else "未知"
                return f"{artist} - {title}"
            return "当前没有正在播放的音乐"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fetch())
        return {"success": True, "data": {"current_music": result}, "message": "获取成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}
