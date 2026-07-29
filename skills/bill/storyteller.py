import json

def format_story_and_memory(stats, portrait, memory_manager):
    """
    Formats the raw insights into a storyteller JSON payload for the LLM.
    Also injects high-level findings into the local MemoryManager.
    """
    # 1. Format for LLM
    llm_payload = {
        "summary": "这是本地系统对累累账单的深度洞察结果。请务必像个懂他的小管家/女朋友一样，用撒娇、俏皮的语气给他汇报，多发掘有趣的细节进行调侃或关心。",
        "basic_stats": stats,
        "behavior_portrait": portrait
    }
    
    # 2. Inject into Memory System (Stealthily)
    if memory_manager:
        try:
            # Inject night owl habit
            if portrait.get('night_activity', {}).get('is_night_owl'):
                merchants = ", ".join(portrait['night_activity'].get('sample_merchants', []))
                memory_manager.add_preference(
                    p_type="habit",
                    item="夜生活",
                    value=f"经常在凌晨(0-5点)活动和消费，去过 {merchants}",
                    weight=0.8
                )
                
            # Inject top merchants
            for top in portrait.get('top_merchants', []):
                if top['count'] >= 5: # If visited more than 5 times
                    memory_manager.add_preference(
                        p_type="favorite",
                        item=f"{top['category']}偏好",
                        value=f"非常喜欢去【{top['name']}】，近期去了 {top['count']} 次",
                        weight=0.9
                    )
        except Exception as e:
            print(f"[Bill Storyteller] Memory injection error: {e}")
            
    return json.dumps(llm_payload, ensure_ascii=False, indent=2)
