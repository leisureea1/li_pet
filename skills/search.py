import requests
import json

TOOL_SCHEMA = {
    "name": "search",
    "description": "进行智能联网搜索，可根据关键词搜索全网实时信息并返回总结",
    "category": "utility",
    "permission": "network",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["query"]
    }
}

def execute(query=None, **kwargs):
    if not query:
        return {"success": False, "error": "搜索关键词不能为空"}
    
    from core.config import APP_CONFIG
    api_key = APP_CONFIG.get("qianfan_api_key", "")
    if not api_key:
        return {"success": False, "error": "系统未配置千帆搜索 API Key，请提醒主人在设置中配置 qianfan_api_key"}
        
    try:
        url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Appbuilder-Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "content": query,
                    "role": "user"
                }
            ],
            "search_source": "baidu_search_v2",
            "stream": False,
            "enable_deep_search": False,
            "search_mode": "required",
            "model": "ernie-4.5-turbo-32k"
        }
        
        print(f"[DEBUG] [Qianfan Search API] Requesting query: {query}")
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"[DEBUG] [Qianfan Search API] Response Code: {resp.status_code}")
        print(f"[DEBUG] [Qianfan Search API] Response Text: {resp.text[:500]}...") # Print first 500 chars

        if resp.status_code == 200:
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                summary = data["choices"][0]["message"].get("content", "无摘要")
                print(f"[DEBUG] [Qianfan Search API] Extracted summary: {summary[:100]}...")
                return {"success": True, "data": {"summary": summary}, "message": "搜索成功"}
            else:
                print("[DEBUG] [Qianfan Search API] No choices found in response")
                return {"success": False, "error": "未能生成搜索总结"}
        else:
            return {"success": False, "error": f"API请求失败: {resp.status_code} - {resp.text}"}
            
    except Exception as e:
        print(f"[DEBUG] [Qianfan Search API] Exception: {e}")
        return {"success": False, "error": str(e)}
