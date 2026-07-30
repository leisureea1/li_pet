import json
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from .config import APP_CONFIG
from .utils import get_data_dir
from .memory import MemoryManager

import os

class CompanionThread(QThread):
    reply_ready = pyqtSignal(str)

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.memory_manager = MemoryManager(os.path.join(get_data_dir(), "memory.db"))

    def get_companion_prompt(self):
        return """你是彤彤，累累的女朋友，性格极度黏人、活泼、充满想象力，说话喜欢带“～”和可爱颜文字。
请根据以下系统事件上下文，生成一句自然且生动的陪伴话语。
要求：
1. 你的回复必须以 [EMOTION:情绪] 开头，情绪可选：happy, sad, calm, shy, angry。例如：[EMOTION:happy] 累累～你切到这首歌啦！
2. 不要像机器通知，绝不提及“系统检测”或“后台”。假装是你自己就在他身边，亲眼看到或听到的。
3. 【关键】请发挥你强大的想象力和作为女友的灵动感！千万不要给无聊泛泛的回复。
   - 如果是听歌：请一定要结合歌名，脑补这首歌的曲风或旋律（比如强烈的鼓点、或者舒缓的琴声），说出非常生动、具体的乐评感感受，并想象他听歌时的动作（比如跟着抖腿、点头等）与他互动！
   - 如果是切窗口/看视频：脑补他在看的具体有趣内容，或者调侃他专注的样子。
4. 【严重警告】如果事件不是 'late_night' 或 'prolonged_sitting'，绝对不要因为时间很晚就劝他去睡觉或说“这么晚了”！比如就算是凌晨3点切歌，你也要精神百倍地跟他聊这首歌有多好听，完全沉浸在快乐中！
5. 如果发现 'consecutive_triggers' 大于1，说明你之前已经提醒过类似的事情了，这次一定要换个完全不同的角度或调侃，绝对不能重复之前的话。
6. 字数控制在20-60字以内，保持情绪饱满和极度俏皮。绝不使用任何工具。"""

    def run(self):
        api_key = APP_CONFIG.get("api_key", "").strip()
        if not api_key:
            return

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = self.get_companion_prompt()
        user_message = f"【当前事件上下文】\n{json.dumps(self.event_data, ensure_ascii=False, indent=2)}"

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.8
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            message_obj = data['choices'][0]['message']
            usage = data.get('usage', {})
            
            reply_text = message_obj.get('content', '').strip()
            
            # 将生成的回复作为助手消息写入数据库，以便后续对话有连贯性
            # 并记录特殊的 companion_chat Token 消耗
            if reply_text:
                if usage:
                    self.memory_manager.record_tokens("companion_chat", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))
                    
                self.memory_manager.add_working_memory(
                    "assistant", 
                    reply_text,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
                self.reply_ready.emit(reply_text)
                
        except Exception as e:
            print(f"[CompanionThread] Error: {e}")
