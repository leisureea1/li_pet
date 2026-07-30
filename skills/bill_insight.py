import os
import sys

from skills.bill.importer import load_bill
from skills.bill.analyzer import analyze_basic_stats
from skills.bill.relationship import analyze_relationships
from skills.bill.portrait import build_portrait
from skills.bill.storyteller import format_story_and_memory

TOOL_SCHEMA = {
    "name": "bill_insight",
    "description": "【高级工具】深度读取并分析用户的账单 Excel/CSV 文件，提取精准的收支数据、人际关系和行为画像。",
    "category": "utility",
    "permission": "local",
    "version": "2.0",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "账单文件的绝对路径"}
        },
        "required": ["file_path"]
    }
}

def execute(file_path=None, pet_instance=None, memory_manager=None, **kwargs):
    if not file_path or not os.path.exists(file_path):
        return {"success": False, "error": f"找不到账单文件: {file_path}"}
        
    try:
        # 1. Load and parse the bill
        df = load_bill(file_path)
        if df is None or df.empty:
            return {"success": False, "error": "无法解析此文件格式，请确保是从微信或支付宝下载的原版账单。"}
            
        # 2. Extract basic stats
        stats = analyze_basic_stats(df)
        
        # 3. Extract relationships (money loops)
        relationships = analyze_relationships(df)
        
        # 4. Extract behavior portrait
        router = getattr(pet_instance, 'event_manager', None)
        if router and hasattr(router, 'router'):
            router = router.router # Attempt to grab the semantic router instance from pet.py event_manager
        else:
            router = None
            
        portrait = build_portrait(df, router=router)
        
        # 5. Format to JSON and inject memory
        story_payload = format_story_and_memory(stats, relationships, portrait, memory_manager)
        
        # [DEBUG] Print the generated JSON for the user to inspect
        print("====== [DEBUG] BILL INSIGHT LOCAL JSON PAYLOAD ======")
        print(story_payload)
        print("=====================================================")
        
        return {
            "success": True, 
            "data": {"insights": story_payload}, 
            "message": "账单洞察分析完成，请立刻用俏皮可爱的语气向累累汇报这些发现！"
        }
    except Exception as e:
        return {"success": False, "error": f"分析账单时发生错误: {e}"}
