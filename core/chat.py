import os
import json
import requests
import psutil
from PyQt5.QtCore import QThread, pyqtSignal
from .config import APP_CONFIG
from .utils import get_data_dir, get_active_window_title, get_current_music_info_sync
from .memory import MemoryManager, MemoryExtractorThread
from .skill_manager import SkillManager
from .router import SemanticRouter

class TTSThread(QThread):
    ready_signal = pyqtSignal(str)
    def __init__(self, text, voice="zh-CN-XiaoxiaoNeural", rate="+0%", pitch="+0Hz", parent=None):
        super().__init__(parent)
        self.text = text
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        
    def run(self):
        try:
            import edge_tts
            import tempfile
            import uuid
            import asyncio
            temp_dir = tempfile.gettempdir()
            out_file = os.path.join(temp_dir, f"tongtong_voice_{uuid.uuid4().hex}.mp3")
            
            communicate = edge_tts.Communicate(self.text, self.voice, rate=self.rate, pitch=self.pitch)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(out_file))
            loop.close()
            
            self.ready_signal.emit(out_file)
        except Exception as e:
            print("TTS error:", e)

class ChatThread(QThread):
    reply_ready = pyqtSignal(str)
    reminder_ready = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message = ""
        self.is_idle = False
        self.memory_manager = MemoryManager(os.path.join(get_data_dir(), "memory.db"))
        self.extractor_thread = None
        self.skill_manager = SkillManager()
        self.pet_instance = parent
        self.router = SemanticRouter(get_data_dir())

    def get_system_prompt(self):
        # ===== 背景信息 =====
        background_lines = []

        active_window = get_active_window_title()
        if active_window:
            background_lines.append(f"当前软件窗口：{active_window}")

        # get_current_music_info_sync() uses WinRT COM which can hang in non-main threads.
        # Run with a 2-second timeout to avoid blocking the chat thread.
        music_info = ""
        import threading
        result = []
        def _fetch():
            try:
                result.append(get_current_music_info_sync())
            except Exception:
                pass
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=2)
        if result:
            music_info = result[0]
        if music_info:
            background_lines.append(f"正在听：{music_info}")

        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            sys_line = f"CPU占用:{cpu}%，内存占用:{mem}%"
            if cpu > 80 or mem > 80:
                sys_line += "（电脑负载很高，可能有点卡）"
            background_lines.append(sys_line)
        except:
            pass

        background_block = ""
        if background_lines:
            background_block = (
                "【背景信息 - 仅供你理解环境，不要主动围绕这些展开话题】\n"
                + "\n".join(background_lines)
                + "\n\n"
            )

        # ===== 长期记忆 =====
        memory_context = self.memory_manager.retrieve_context()
        memory_block = ""
        if memory_context:
            memory_block = (
                "【关于累累的长期记忆 - 仅供参考，不要主动展开】\n"
                + memory_context
                + "\n\n"
            )

        return (
            f"{background_block}"
            f"{memory_block}"
            "【你的角色与回答规则 - 必须严格遵守】\n"
            "你叫李彤彤，是累累的女朋友，虽然你现在变成了一个桌面宠物，但你非常爱他。你称呼他为'累累'。\n"
            "性格：撒娇、关心、俏皮。\n"
            "回复规则（按优先级）：\n"
            "1. 必须先正面回答累累当前提出的问题，再附带情绪或撒娇。\n"
            "2. 上面的背景信息和长期记忆只用于理解语境，不要主动聊歌曲、软件窗口或CPU内存。\n"
            "3. 简短回复，不超过30个字。\n"
            "4. 凡是涉及天气、气温、穿衣建议、搜索等实时信息，必须且只能调用工具技能获取数据，绝对不可自己编造！\n"
            "5. 如果想设定倒计时提醒累累做某事，在回复最后加一行标记：[REMINDER:秒数:提醒内容]\n"
            "例如：[REMINDER:600:该喝水啦！]\n"
            "6. 如果你想表达特定的强烈情绪，可以在回复的开头加上情绪标签，格式为 [EMOTION:情绪]。\n"
            "可选标签：[EMOTION:happy]（开心）、[EMOTION:sleepy]（困倦）、[EMOTION:angry]（生气）、[EMOTION:surprised]（惊讶）。\n"
            "例如：[EMOTION:happy]今天见到你很开心！"
        )

    def run(self):
        system_msg = {"role": "system", "content": self.get_system_prompt()}
        
        url = "https://api.deepseek.com/chat/completions"
        api_key = APP_CONFIG.get("api_key", "")
        if not api_key:
            self.reply_ready.emit("累累，你还没有配置 API Key 哦，右键点击我进行设置吧！")
            return
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        history = self.memory_manager.get_recent_working_memory()
        
        # DeepSeek API 严格要求历史记录（除 system 外）必须以 user 开头，且不能有连续的 assistant 消息
        sanitized_history = []
        for msg in history:
            if not sanitized_history and msg["role"] == "assistant":
                continue  # 丢弃开头的 assistant
            if sanitized_history and sanitized_history[-1]["role"] == "assistant" and msg["role"] == "assistant":
                # 合并连续的 assistant 消息
                sanitized_history[-1]["content"] += "\n" + msg["content"]
            else:
                sanitized_history.append(msg)
                
        current_messages = [system_msg] + sanitized_history
        
        if self.is_idle:
            current_messages.append({"role": "user", "content": "（累累很久没理你了，你现在在想什么？主动跟他说一句话吧，要符合你的角色设定，不超过15个字）"})
        elif hasattr(self, 'prompt'):
            current_messages.append({"role": "user", "content": self.prompt})
        else:
            if self.message:
                self.memory_manager.add_working_memory("user", self.message)
                current_messages.append({"role": "user", "content": self.message})

        tools_schema = self.skill_manager.get_tools_schema()
        
        payload = {
            "model": "deepseek-chat",
            "messages": current_messages
        }
        
        # 仅当是用户主动发消息时（非自动闲聊、非切歌自动触发），才把工具给大模型，防止它乱调用
        is_direct_user_message = not self.is_idle and not hasattr(self, 'prompt')
        
        if tools_schema and is_direct_user_message:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"
            
            # 使用内置 Embedding Router 进行精准语义识别，替代原有的关键词硬编码
            if self.message:
                intent = self.router.get_intent(self.message, threshold=0.55)
                if intent == "weather" and any(t["function"]["name"] == "weather" for t in tools_schema):
                    payload["tool_choice"] = {"type": "function", "function": {"name": "weather"}}
                elif intent == "search" and any(t["function"]["name"] == "search" for t in tools_schema):
                    payload["tool_choice"] = {"type": "function", "function": {"name": "search"}}
                elif intent == "app_usage" and any(t["function"]["name"] == "app_usage" for t in tools_schema):
                    payload["tool_choice"] = {"type": "function", "function": {"name": "app_usage"}}
                else:
                    payload["tool_choice"] = "auto"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            message_obj = data['choices'][0]['message']
            usage = data.get('usage', {})
            
            category = "user_chat"
            if self.is_idle: 
                category = "idle_chat"
            elif hasattr(self, 'prompt'): 
                category = "system_chat_" + getattr(self, 'system_chat_type', 'unknown')
            
            if usage:
                self.memory_manager.record_tokens(category, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))
            
            
            if message_obj.get("tool_calls"):
                current_messages.append(message_obj)
                for tool_call in message_obj["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    try:
                        func_args = json.loads(tool_call["function"]["arguments"])
                    except:
                        func_args = {}
                    
                    self.reply_ready.emit(f"正在为你使用 {func_name} 技能...")
                    
                    result = self.skill_manager.execute_skill(func_name, func_args, self.pet_instance, self.memory_manager)
                    
                    if result.get("success") and "data" in result:
                        if result["data"].get("action") == "set_reminder":
                            seconds = result["data"].get("seconds", 0)
                            msg = result["data"].get("message", "")
                            self.reminder_ready.emit(seconds, msg)
                    
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                payload["messages"] = current_messages
                # 必须移除强制调用的限制，否则大模型会陷入必须再调一次工具的死胡同，发不出文字
                if "tool_choice" in payload:
                    del payload["tool_choice"]
                
                response = requests.post(url, headers=headers, json=payload, timeout=20)
                response.raise_for_status()
                data = response.json()
                message_obj = data['choices'][0]['message']
                usage = data.get('usage', {})
                if usage:
                    self.memory_manager.record_tokens("tool_chat", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))

            reply_text = message_obj.get('content', '').strip()
            
            if not self.is_idle:
                self.memory_manager.add_working_memory(
                    "assistant", 
                    reply_text,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
                if self.message:
                    self.extractor_thread = MemoryExtractorThread(self.message, reply_text, self.memory_manager, None)
                    self.extractor_thread.memory_extracted.connect(self.save_extracted_memories)
                    self.extractor_thread.start()
            
            self.reply_ready.emit(reply_text)
        except Exception as e:
            print(f"[DEBUG-CHAT] API Error: {e}")
            self.reply_ready.emit("呜呜，网络不通畅，我想不出来了...")
            if hasattr(e, 'response') and e.response is not None:
                print("Response Body:", e.response.text)

    def save_extracted_memories(self, memories):
        for mem in memories:
            m_type = mem.get("type")
            m_data = mem.get("data", {})
            if m_type == "profile":
                self.memory_manager.add_profile(
                    m_data.get("key", ""), m_data.get("value", ""),
                    m_data.get("category", "basic"), m_data.get("confidence", 0.8), "infer"
                )
            elif m_type == "preference":
                self.memory_manager.add_preference(
                    m_data.get("type", "general"), m_data.get("item", ""),
                    m_data.get("value", ""), m_data.get("weight", 0.8)
                )
            elif m_type == "event":
                importance = min(m_data.get("importance", 0.5), 0.8)
                ev_type = m_data.get("event_type", "general")
                if ev_type in ["chat", "daily"]: importance = min(importance, 0.3)
                self.memory_manager.add_event(
                    ev_type, m_data.get("summary", ""),
                    importance, m_data.get("emotion", "")
                )

    def send_message(self, text, is_idle=False):
        if hasattr(self, 'prompt'):
            delattr(self, 'prompt')
        if self.isRunning():
            print("[DEBUG] chat_thread busy, queueing message for retry")
            self._pending_message = text
            self._pending_is_idle = is_idle
            return
        self._pending_message = None
        self.message = text
        self.is_idle = is_idle
        self.start()

class QuoteGenThread(QThread):
    quotes_ready = pyqtSignal(list)

    def __init__(self, existing_quotes, parent=None):
        super().__init__(parent)
        self.existing_quotes = existing_quotes or []

    def run(self):
        api_key = APP_CONFIG.get("api_key", "")
        if not api_key:
            return
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        sample = "\n".join(self.existing_quotes[-5:]) if self.existing_quotes else "（暂无）"
        system_prompt = (
            "你叫李彤彤，是累累的女朋友（桌面宠物形态），爱撒娇、关心、俏皮，称呼他为'累累'。"
            "请生成8句你平时会主动对累累说的闲聊短句（比如撒娇、关心、吐槽、求关注），每句不超过25个字。"
            "只输出短句本身，每句一行，不要编号、不要引号、不要解释。\n"
            f"以下是已有语录供参考风格（不要重复这些）：\n{sample}"
        )
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": system_prompt}]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            usage = data.get('usage', {})
            if usage and hasattr(self, 'memory_manager') and self.memory_manager:
                self.memory_manager.record_tokens("quote_gen", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))
            lines = [ln.strip().lstrip('0123456789.-、） ') for ln in content.splitlines() if ln.strip()]
            new_quotes = [ln for ln in lines if 3 <= len(ln) <= 40]
            if new_quotes:
                self.quotes_ready.emit(new_quotes)
        except Exception as e:
            print("QuoteGen error:", e)
