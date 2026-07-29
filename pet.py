import sqlite3
from datetime import datetime
import sys
import os
import random
import math
import requests
import json
import asyncio
import re
import base64
import psutil

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_data_dir():
    if sys.platform == 'win32':
        app_data = os.getenv('APPDATA')
        if app_data:
            path = os.path.join(app_data, "LiTongtongPet")
            os.makedirs(path, exist_ok=True)
            return path
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def xor_crypt(data_str, key="tongtong"):
    res = []
    for i in range(len(data_str)):
        res.append(chr(ord(data_str[i]) ^ ord(key[i % len(key)])))
    return "".join(res)

def load_encrypted_json(filename, default):
    filepath = os.path.join(get_data_dir(), filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                b64_str = f.read()
            decrypted = xor_crypt(base64.b64decode(b64_str).decode('utf-8'))
            return json.loads(decrypted)
        except Exception:
            pass
    return default

def save_encrypted_json(filename, data):
    filepath = os.path.join(get_data_dir(), filename)
    try:
        json_str = json.dumps(data)
        encrypted = base64.b64encode(xor_crypt(json_str).encode('utf-8')).decode('utf-8')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(encrypted)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def get_active_window_title():
    if sys.platform == 'win32':
        import ctypes
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else ""
        except:
            return ""
    elif sys.platform == 'darwin':
        import subprocess
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        try:
            res = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.DEVNULL)
            return res.decode('utf-8').strip()
        except:
            return ""
    return ""

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction, QInputDialog, QLineEdit, QPushButton, QHBoxLayout, QDialog, QFormLayout, QCheckBox, QVBoxLayout, QMessageBox, QComboBox
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QPoint, pyqtProperty, QSize, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QCursor, QTransform, QFont, QPainter, QColor

def load_config():
    old_config_path = os.path.join(get_data_dir(), "config.json")
    if os.path.exists(old_config_path):
        try:
            with open(old_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            save_encrypted_json("config.dat", config)
            os.remove(old_config_path)
            return config
        except:
            pass
    return load_encrypted_json("config.dat", {"api_key": "", "autostart": False, "enable_voice": True, "tts_voice": "zh-CN-XiaoxiaoNeural"})

def save_config(config):
    save_encrypted_json("config.dat", config)

def set_autostart(enable=True):
    if sys.platform == 'win32':
        import winreg
        try:
            key = winreg.HKEY_CURRENT_USER
            key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(sys.argv[0])
                
            open_key = winreg.OpenKey(key, key_value, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(open_key, "LiTongtongPet", 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(open_key, "LiTongtongPet")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(open_key)
        except Exception as e:
            print("Failed to set autostart (win32):", e)
    elif sys.platform == 'darwin':
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.litongtong.pet.plist")
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(sys.argv[0])
            
        if enable:
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.litongtong.pet</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            try:
                os.makedirs(os.path.dirname(plist_path), exist_ok=True)
                with open(plist_path, "w", encoding="utf-8") as f:
                    f.write(plist_content)
            except Exception as e:
                print("Failed to set autostart (darwin):", e)
        else:
            if os.path.exists(plist_path):
                try:
                    os.remove(plist_path)
                except Exception as e:
                    print("Failed to remove autostart (darwin):", e)

APP_CONFIG = load_config()
if not APP_CONFIG.get("api_key"):
    APP_CONFIG["api_key"] = "sk-1ad1dacb6e1d4cde851ce2488abfe001"
    save_config(APP_CONFIG)

class TTSThread(QThread):
    ready_signal = pyqtSignal(str)
    def __init__(self, text, voice="zh-CN-XiaoxiaoNeural", parent=None):
        super().__init__(parent)
        self.text = text
        self.voice = voice
        
    def run(self):
        try:
            import edge_tts
            import tempfile
            import uuid
            import asyncio
            temp_dir = tempfile.gettempdir()
            out_file = os.path.join(temp_dir, f"tongtong_voice_{uuid.uuid4().hex}.mp3")
            
            communicate = edge_tts.Communicate(self.text, self.voice)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(out_file))
            loop.close()
            
            self.ready_signal.emit(out_file)
        except Exception as e:
            print("TTS error:", e)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 250)
        self.setStyleSheet("""
            QDialog { background-color: rgba(255, 240, 245, 240); border-radius: 15px; border: 2px solid #ffb6c1; }
            QLabel { color: #ff69b4; font-weight: bold; font-size: 14px; }
            QLineEdit { border: 2px solid #ffb6c1; border-radius: 8px; padding: 5px; background-color: white; color: #333; }
            QPushButton { background-color: #ffb6c1; color: white; border-radius: 10px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #ff69b4; }
            QCheckBox { color: #ff69b4; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        title = QLabel("彤彤的设置 (´｡• ᵕ •｡`)")
        close_btn = QPushButton("✖")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("QPushButton {background-color: transparent; color: #ff69b4; font-size: 16px; border:none;} QPushButton:hover {color: red;}")
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(APP_CONFIG.get("api_key", ""))
        form_layout.addRow(QLabel("DeepSeek API Key:"), self.api_key_input)
        
        self.autostart_checkbox = QCheckBox("开机自启动")
        self.autostart_checkbox.setChecked(APP_CONFIG.get("autostart", False))
        form_layout.addRow(QLabel("自启动:"), self.autostart_checkbox)
        
        self.voice_checkbox = QCheckBox("允许彤彤说话")
        self.voice_checkbox.setChecked(APP_CONFIG.get("enable_voice", True))
        form_layout.addRow(QLabel("声音开关:"), self.voice_checkbox)
        
        self.voice_combo = QComboBox()
        self.voice_combo.setStyleSheet("QComboBox { border: 2px solid #ffb6c1; border-radius: 5px; padding: 3px; background-color: white; color: #333; }")
        self.voices = {
            "晓晓 (温暖亲切)": "zh-CN-XiaoxiaoNeural",
            "晓伊 (活泼可爱)": "zh-CN-XiaoyiNeural",
            "晓北 (东北幽默)": "zh-CN-liaoning-XiaobeiNeural",
            "晓妮 (陕西明快)": "zh-CN-shaanxi-XiaoniNeural",
            "晓臻 (台湾轻柔)": "zh-TW-HsiaoChenNeural"
        }
        for name in self.voices.keys():
            self.voice_combo.addItem(name)
            
        current_voice = APP_CONFIG.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        for i, (name, v_id) in enumerate(self.voices.items()):
            if v_id == current_voice:
                self.voice_combo.setCurrentIndex(i)
                break
                
        preview_btn = QPushButton("▶️ 试听")
        preview_btn.setFixedSize(60, 26)
        preview_btn.setStyleSheet("QPushButton { background-color: #ff91a4; color: white; border-radius: 5px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #ff69b4; }")
        preview_btn.clicked.connect(self.preview_voice)
        
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(self.voice_combo)
        voice_layout.addWidget(preview_btn)
        form_layout.addRow(QLabel("选择音色:"), voice_layout)
        
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addLayout(header_layout)
        layout.addLayout(form_layout)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        self.old_pos = None

    def preview_voice(self):
        voice_name = self.voice_combo.currentText()
        voice_id = self.voices[voice_name]
        self.preview_thread = TTSThread("你好呀，累累！我是彤彤，以后就用这个声音陪着你啦！", voice=voice_id)
        self.preview_thread.ready_signal.connect(self.play_preview)
        self.preview_thread.start()

    def play_preview(self, audio_file):
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
        except Exception as e:
            QMessageBox.warning(self, "播放失败", f"无法播放试听音频: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def save_settings(self):
        APP_CONFIG["api_key"] = self.api_key_input.text().strip()
        APP_CONFIG["autostart"] = self.autostart_checkbox.isChecked()
        APP_CONFIG["enable_voice"] = self.voice_checkbox.isChecked()
        APP_CONFIG["tts_voice"] = self.voices.get(self.voice_combo.currentText(), "zh-CN-XiaoxiaoNeural")
        save_config(APP_CONFIG)
        set_autostart(APP_CONFIG["autostart"])
        QMessageBox.information(self, "成功", "设置已保存！彤彤记住了哦~")
        self.accept()

class MemoryManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    value TEXT,
                    category TEXT,
                    confidence REAL,
                    source TEXT,
                    active BOOLEAN,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    item TEXT,
                    value TEXT,
                    weight REAL,
                    active BOOLEAN,
                    replaced_by INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT,
                    event_type TEXT,
                    summary TEXT,
                    importance REAL,
                    emotion TEXT,
                    related TEXT,
                    decay_rate REAL,
                    last_used TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS working_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            ''')
            conn.commit()

    def add_profile(self, key, value, category="basic", confidence=1.0, source="infer"):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_profile (key, value, category, confidence, source, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (key, value, category, confidence, source, True, now, now))
            conn.commit()

    def add_preference(self, p_type, item, value, weight=1.0):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE preferences SET active = 0, updated_at = ? WHERE type = ? AND item = ? AND active = 1
            ''', (now, p_type, item))
            cursor.execute('''
                INSERT INTO preferences (type, item, value, weight, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (p_type, item, value, weight, True, now, now))
            conn.commit()

    def add_event(self, event_type, summary, importance, emotion="", related="", decay_rate=30.0):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (time, event_type, summary, importance, emotion, related, decay_rate, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (now, event_type, summary, importance, emotion, related, decay_rate, now))
            conn.commit()

    def add_working_memory(self, role, content):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO working_memory (role, content, timestamp) VALUES (?, ?, ?)', (role, content, now))
            conn.commit()
            
            cursor.execute('SELECT count(*) FROM working_memory')
            if cursor.fetchone()[0] > 100:
                cursor.execute('DELETE FROM working_memory WHERE id NOT IN (SELECT id FROM working_memory ORDER BY timestamp DESC LIMIT 100)')
                conn.commit()

    def get_recent_working_memory(self, limit=20):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role, content FROM working_memory ORDER BY timestamp DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def retrieve_context(self):
        context_parts = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT key, value FROM user_profile WHERE active = 1 ORDER BY confidence DESC LIMIT 10')
            profiles = cursor.fetchall()
            if profiles:
                context_parts.append("【用户画像】\n" + "\n".join([f"- {r[0]}: {r[1]}" for r in profiles]))
                
            cursor.execute('SELECT item, value FROM preferences WHERE active = 1 ORDER BY weight DESC LIMIT 10')
            prefs = cursor.fetchall()
            if prefs:
                context_parts.append("【用户偏好】\n" + "\n".join([f"- {r[0]}: {r[1]}" for r in prefs]))
                
            cursor.execute('SELECT id, time, summary, importance, decay_rate FROM events')
            events = cursor.fetchall()
            now = datetime.now()
            scored_events = []
            for ev in events:
                try:
                    ev_time = datetime.fromisoformat(ev[1])
                    days_diff = (now - ev_time).days
                    decay = ev[4] if ev[4] else 30.0
                    score = ev[3] * math.exp(-days_diff / decay)
                    scored_events.append((score, ev[2]))
                except:
                    pass
            scored_events.sort(key=lambda x: x[0], reverse=True)
            top_events = scored_events[:5]
            if top_events:
                context_parts.append("【近期事件/状态】\n" + "\n".join([f"- {r[1]}" for r in top_events]))
                
        return "\n\n".join(context_parts)

class MemoryExtractorThread(QThread):
    def __init__(self, user_msg, ai_reply, memory_manager, parent=None):
        super().__init__(parent)
        self.user_msg = user_msg
        self.ai_reply = ai_reply
        self.memory_manager = memory_manager
        
    def run(self):
        api_key = APP_CONFIG.get("api_key", "")
        if not api_key: return
            
        system_prompt = (
            "你是一个记忆管理器。你的任务是判断下面对话是否产生值得长期保存的信息。\n"
            "规则：\n"
            "1. 不记录一次性行为（如“今天吃火锅”）\n"
            "2. 不记录临时情绪，除非影响长期关系\n"
            "3. 不推测用户信息，用户明确表达优先级最高\n"
            "输出 JSON 数组格式，包含 type (profile/preference/event) 和 data，不要输出其他废话。\n"
            "例如: [{\"type\":\"event\", \"data\":{\"event_type\":\"project\", \"summary\":\"用户正在开发AI桌宠\", \"importance\":0.8}}]"
        )
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户: {self.user_msg}\nAI: {self.ai_reply}"}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                memories = json.loads(match.group(0))
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
        except Exception as e:
            print("Memory Extractor Error:", e)

def get_title_from_pid(target_pid):
    if sys.platform != 'win32':
        return ""
    try:
        import ctypes
        titles = []
        def callback(hwnd, hwnds):
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == target_pid:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    titles.append(buff.value)
            return True
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
        
        valid_titles = [t for t in titles if t not in ["Default IME", "MSCTFIME UI", "网易云音乐"] and len(t) > 2]
        if valid_titles:
            for t in valid_titles:
                if " - " in t:
                    return t
            return valid_titles[0]
    except Exception:
        pass
    return ""

def get_current_music_info_sync():
    if sys.platform != 'win32':
        return ""
    try:
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        async def fetch():
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            sessions = manager.get_sessions()
            for s in sessions:
                try:
                    playback_info = s.get_playback_info()
                    if playback_info:
                        status = playback_info.playback_status
                        status_val = status.value if hasattr(status, 'value') else status
                        if status_val == 4:
                            info = await s.try_get_media_properties_async()
                            title = info.title if info.title else "未知"
                            artist = info.artist if info.artist else "未知"
                            return f"{artist} - {title}"
                except Exception:
                    continue
                    
            # Fallback to current session
            session = manager.get_current_session()
            if session:
                info = await session.try_get_media_properties_async()
                title = info.title if info.title else "未知"
                artist = info.artist if info.artist else "未知"
                return f"{artist} - {title}"
            return ""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch())
    except Exception as e:
        print("Music fetch error:", e)
        return ""

class ChatThread(QThread):
    reply_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message = ""
        self.is_idle = False
        self.memory_manager = MemoryManager(os.path.join(get_data_dir(), "memory.db"))
        self.extractor_thread = None

    def get_system_prompt(self):
        # ===== 背景信息（仅供理解语境，不主动展开）=====
        background_lines = []

        active_window = get_active_window_title()
        if active_window:
            background_lines.append(f"当前软件窗口：{active_window}")

        music_info = get_current_music_info_sync()
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

        # ===== 长期记忆（仅供参考）=====
        memory_context = self.memory_manager.retrieve_context()
        memory_block = ""
        if memory_context:
            memory_block = (
                "【关于累累的长期记忆 - 仅供参考，不要主动展开】\n"
                + memory_context
                + "\n\n"
            )

        # ===== 角色与回答规则（放末尾，强约束）=====
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
            "4. 如果想设定倒计时提醒累累做某事，在回复最后加一行标记：[REMINDER:秒数:提醒内容]\n"
            "例如：[REMINDER:600:该喝水啦！]"
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
        current_messages = [system_msg] + history
        
        if self.is_idle:
            current_messages.append({"role": "user", "content": "（累累很久没理你了，你现在在想什么？主动跟他说一句话吧，要符合你的角色设定，不超过15个字）"})
        elif hasattr(self, 'prompt'):
            current_messages.append({"role": "user", "content": self.prompt})
        else:
            if self.message:
                self.memory_manager.add_working_memory("user", self.message)
                current_messages.append({"role": "user", "content": self.message})

        payload = {
            "model": "deepseek-chat",
            "messages": current_messages
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            reply_text = data['choices'][0]['message']['content'].strip()
            
            if not self.is_idle:
                self.memory_manager.add_working_memory("assistant", reply_text)
                if self.message:
                    # Launch Memory Extractor
                    self.extractor_thread = MemoryExtractorThread(self.message, reply_text, self.memory_manager, None)
                    self.extractor_thread.start()
            
            self.reply_ready.emit(reply_text)
        except Exception as e:
            self.reply_ready.emit("呜呜，网络不通畅，我想不出来了...")
            print("API Error:", e)

    def send_message(self, text, is_idle=False):
        # 清除可能残留的主动触发 prompt（切歌/切窗口），确保用户消息优先
        if hasattr(self, 'prompt'):
            del self.prompt
        self.message = text
        self.is_idle = is_idle
        self.start()

class QuoteGenThread(QThread):
    """后台请求大模型批量生成语录，补充本地语录库。"""
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
        # 让模型参考已有语录风格，生成不重复的新语录
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
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            # 按行拆分，清理每行
            lines = [ln.strip().lstrip('0123456789.-、） ') for ln in content.splitlines() if ln.strip()]
            # 过滤太长/太短的
            new_quotes = [ln for ln in lines if 3 <= len(ln) <= 40]
            if new_quotes:
                self.quotes_ready.emit(new_quotes)
        except Exception as e:
            print("QuoteGen error:", e)

class DialogBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.label = QLabel(self)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border: 2px solid #ffb6c1;
                border-radius: 10px;
                padding: 5px;
                color: #333333;
            }
        """)
        self.label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(400)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_text(self, text, pos, duration=3000):
        self.label.setText(text)
        self.label.adjustSize()
        self.resize(self.label.size())
        
        bubble_x = pos.x() - self.width() // 2
        bubble_y = pos.y() - self.height() - 10
        
        # Prevent overflow
        screen_rect = QApplication.desktop().availableGeometry(self)
        if bubble_x < screen_rect.left(): bubble_x = screen_rect.left()
        if bubble_x + self.width() > screen_rect.right(): bubble_x = screen_rect.right() - self.width()
        if bubble_y < screen_rect.top(): bubble_y = screen_rect.top()
        if bubble_y + self.height() > screen_rect.bottom(): bubble_y = screen_rect.bottom() - self.height()
        
        self.move(bubble_x, bubble_y)
        self.show()
        if duration > 0:
            self.timer.start(duration)
        else:
            self.timer.stop()

class InputDialogBubble(QWidget):
    text_entered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QWidget#BubbleWidget {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #ffb6c1;
                border-radius: 12px;
            }
            QLineEdit {
                border: none;
                background: transparent;
                font-family: 'Microsoft YaHei';
                font-size: 14px;
                color: #333333;
            }
            QPushButton {
                background-color: #ffb6c1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 5px 12px;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff91a4;
            }
        """)

        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("BubbleWidget")
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("对彤彤说点什么...")
        self.line_edit.setMinimumWidth(160)
        self.line_edit.returnPressed.connect(self.send_text)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_text)
        
        layout = QHBoxLayout(self.main_widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.send_btn)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_widget)
        
        self.hide()

    def show_input(self, pos):
        self.line_edit.clear()
        self.adjustSize()
        self.move(pos)
        self.show()
        self.line_edit.setFocus()
        self.activateWindow()

    def send_text(self):
        text = self.line_edit.text().strip()
        if text:
            self.text_entered.emit(text)
        self.hide()

class Particle(QLabel):
    def __init__(self, parent, text, color, start_pos, end_pos, duration=1500):
        super().__init__(text, parent)
        self.setFont(QFont("Arial", 16, QFont.Bold))
        self.setStyleSheet(f"color: {color};")
        self.adjustSize()
        self.move(start_pos)
        self.show()
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(duration)
        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.finished.connect(self.deleteLater)
        self.anim.start()

class HandEffect(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.image_label = QLabel(self)
        pixmap = QPixmap(os.path.join(get_resource_dir(), "pat_hand_nobg.png"))
        if pixmap.isNull():
            self.image_label.setText("✋")
            self.image_label.setFont(QFont("Arial", 40))
        else:
            pixmap = pixmap.scaledToWidth(100, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
            
        self.image_label.adjustSize()
        self.resize(self.image_label.size())
        self.hide()
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        
        self.pats_done = 0
        self.max_pats = 3
        self.base_pos = QPoint()
        
        self.anim.finished.connect(self.on_anim_finished)

    def start_patting(self, target_pos):
        self.base_pos = target_pos
        self.pats_done = 0
        self.move(self.base_pos)
        self.show()
        self.pat_cycle()
        
    def pat_cycle(self):
        if self.pats_done >= self.max_pats * 2:
            self.hide()
            return
            
        self.anim.setStartValue(self.pos())
        if self.pats_done % 2 == 0:
            self.anim.setEndValue(self.base_pos + QPoint(0, 30))
        else:
            self.anim.setEndValue(self.base_pos)
            
        self.pats_done += 1
        self.anim.start()
        
    def on_anim_finished(self):
        self.pat_cycle()


class Pet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.is_following_mouse = False
        self.is_walking = False
        self.is_sleeping = False
        self.walk_direction = 1
        
        self.initUI()
        
        self.action_timer = QTimer(self)
        self.action_timer.timeout.connect(self.update_action)
        self.action_timer.start(50)
        
        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.spawn_sleep_particle)
        
        self.dialog_bubble = DialogBubble()
        
        self.input_bubble = InputDialogBubble()
        self.input_bubble.text_entered.connect(self.on_input_entered)
        
        self.hand_effect = HandEffect()
        
        self.dialogs = [
            "你在干嘛呀？累累", "好无聊哦~累累", "别戳我啦！累累", "带我出去玩嘛！累累", 
            "嘻嘻~累累", "饿饿，饭饭累累", "今天天气真好！累累", "摸摸头~累累"
        ]
        
        # 加载自动保存的语录库（AI 回复中沉淀下来的短句）
        self.saved_quotes = load_encrypted_json("quotes.dat", [])
        if not isinstance(self.saved_quotes, list):
            self.saved_quotes = []
        self._quote_save_pending = False
        # 空闲搭话计数：每 N 次后触发一次语录补充
        self._idle_count = 0
        self._quote_gen_thread = None
        
        self.chat_thread = ChatThread(self)
        self.chat_thread.reply_ready.connect(self.on_chat_reply)
        
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.trigger_idle_chat)
        self.idle_timer.start(600000)

        # Proactive observation timer (5 seconds)
        self.observe_timer = QTimer(self)
        self.observe_timer.timeout.connect(self.proactive_observe)
        self.observe_timer.start(5000)
        self.last_active_window = get_active_window_title()
        import time
        self.last_proactive_time = time.time()
        
        # Music detection timer (2 seconds)
        self.music_timer = QTimer(self)
        self.music_timer.timeout.connect(self.check_music)
        self.music_timer.start(2000)

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        
        self.image_label = QLabel(self)
        self.pixmap = QPixmap(os.path.join(get_resource_dir(), "character_fullbody.png"))
        if self.pixmap.isNull():
            self.pixmap = QPixmap(os.path.join(get_resource_dir(), "character_nobg.png"))
            if self.pixmap.isNull():
                self.pixmap = QPixmap(200, 200)
                self.pixmap.fill(Qt.red)
        
        self.scale_factor = 1.0
        self.base_height = 300
        aspect = self.pixmap.width() / self.pixmap.height()
        self.base_width = int(self.base_height * aspect)
        
        self.update_image()
        self.dragging = False
        self.offset = QPoint()
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 250, screen.height() - 350)

    def update_image(self, transform=None):
        scaled_pixmap = self.pixmap.scaled(
            int(self.base_width * self.scale_factor),
            int(self.base_height * self.scale_factor),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        if transform:
            scaled_pixmap = scaled_pixmap.transformed(transform, Qt.SmoothTransformation)
            
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())
        self.resize(scaled_pixmap.size())

    def update_action(self):
        if self.is_following_mouse:
            target = QCursor.pos()
            current = self.pos()
            dx = target.x() - current.x() - self.width() // 2
            dy = target.y() - current.y() - self.height() // 2
            
            if abs(dx) > 10 or abs(dy) > 10:
                self.move(int(current.x() + dx * 0.05), int(current.y() + dy * 0.05))
                transform = QTransform()
                if dx > 0:
                    transform.scale(-1, 1)
                self.update_image(transform)
                
        elif self.is_walking:
            current = self.pos()
            screen_rect = QApplication.primaryScreen().availableGeometry()
            
            new_x = current.x() + self.walk_direction * 2
            
            if new_x <= 0 or new_x + self.width() >= screen_rect.width():
                self.walk_direction *= -1
                
            self.move(new_x, current.y())
            
            transform = QTransform()
            if self.walk_direction > 0:
                transform.scale(-1, 1)
            
            bounce = math.sin(new_x * 0.1) * 2
            self.move(new_x, int(current.y() + bounce))
            self.update_image(transform)
            
        if not self.dialog_bubble.isHidden():
            center_x = self.pos().x() + self.width() // 2
            bubble_x = center_x - self.dialog_bubble.width() // 2
            bubble_y = self.pos().y() - self.dialog_bubble.height() - 10
            self.dialog_bubble.move(bubble_x, bubble_y)
            
    def on_chat_reply(self, text):
        match = re.search(r'\[REMINDER:(\d+):(.*?)\]', text)
        if match:
            try:
                seconds = int(match.group(1))
                msg = match.group(2)
                text = text.replace(match.group(0), "").strip()
                QTimer.singleShot(seconds * 1000, lambda: self.trigger_reminder(msg))
            except:
                pass
                
        if text:
            # 自动保存短句到语录库（去掉提醒标记后的纯文本，长度合理才存）
            clean = text.strip()
            if 3 <= len(clean) <= 40 and clean not in self.saved_quotes:
                self.saved_quotes.append(clean)
                # 限制语录库大小，保留最近200条
                if len(self.saved_quotes) > 200:
                    self.saved_quotes = self.saved_quotes[-200:]
                try:
                    save_encrypted_json("quotes.dat", self.saved_quotes)
                except Exception:
                    pass
            if APP_CONFIG.get("enable_voice", True):
                voice_id = APP_CONFIG.get("tts_voice", "zh-CN-XiaoxiaoNeural")
                self.tts_thread = TTSThread(text, voice=voice_id, parent=self)
                self.tts_thread.ready_signal.connect(lambda audio_file, txt=text: self.play_tts_and_show_bubble(txt, audio_file))
                self.tts_thread.start()
            else:
                duration = max(3000, len(text) * 200) # dynamic duration based on length
                self.show_bubble(text, duration)

    def play_tts_and_show_bubble(self, text, audio_file):
        self.show_bubble(text, duration=0) # Keeps open until audio finishes
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Start timer to check when music stops
            if not hasattr(self, 'audio_check_timer'):
                self.audio_check_timer = QTimer(self)
                self.audio_check_timer.timeout.connect(self.check_audio_status)
            self.audio_check_timer.start(100)
        except:
            # Fallback if audio fails
            duration = max(3000, len(text) * 200)
            self.show_bubble(text, duration)

    def check_audio_status(self):
        try:
            import pygame
            if not pygame.mixer.music.get_busy():
                self.audio_check_timer.stop()
                self.dialog_bubble.hide()
        except:
            if hasattr(self, 'audio_check_timer'):
                self.audio_check_timer.stop()
            self.dialog_bubble.hide()

    def trigger_reminder(self, msg):
        if APP_CONFIG.get("enable_voice", True):
            voice_id = APP_CONFIG.get("tts_voice", "zh-CN-XiaoxiaoNeural")
            self.tts_thread = TTSThread(msg, voice=voice_id, parent=self)
            self.tts_thread.ready_signal.connect(lambda audio_file, txt=msg: self.play_tts_and_show_bubble(txt, audio_file))
            self.tts_thread.start()
        else:
            duration = max(3000, len(msg) * 200)
            self.show_bubble(msg, duration)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(2000)
                    prompt = f"累累刚才拖拽丢给我了一份文件，文件名是 {os.path.basename(file_path)}，部分内容如下：\n{content}\n请你结合这份文件对累累说点什么吧。"
                    self.chat_thread.send_message(prompt)
                    self.show_bubble("正在看你给我的文件哦...")
                except Exception:
                    self.show_bubble("这个文件彤彤看不懂啦~")

    def trigger_idle_chat(self):
        if self.is_sleeping:
            return
        # 优先用本地语录（沉淀的AI回复 + 内置），不请求大模型
        import random as _random
        pool = self.saved_quotes + self.dialogs
        if pool:
            quote = _random.choice(pool)
            self.show_bubble(quote, max(3000, len(quote) * 200))
        # 每 6 次空闲（≈1小时）且语录库不足 50 条时，后台补充新语录
        self._idle_count += 1
        if self._idle_count >= 6 and len(self.saved_quotes) < 50:
            if self._quote_gen_thread is None or not self._quote_gen_thread.isRunning():
                self._idle_count = 0
                self._quote_gen_thread = QuoteGenThread(self.saved_quotes, self)
                self._quote_gen_thread.quotes_ready.connect(self.on_quotes_ready)
                self._quote_gen_thread.start()

    def on_quotes_ready(self, new_quotes):
        """语录生成线程返回新语录时，去重后存入"""
        added = 0
        for q in new_quotes:
            if q not in self.saved_quotes:
                self.saved_quotes.append(q)
                added += 1
        if added > 0:
            # 限制总量 200 条
            if len(self.saved_quotes) > 200:
                self.saved_quotes = self.saved_quotes[-200:]
            try:
                save_encrypted_json("quotes.dat", self.saved_quotes)
                print(f"[语录] 补充 {added} 句，总计 {len(self.saved_quotes)} 句")
            except Exception:
                pass

    def reset_idle_timer(self):
        self.idle_timer.stop()
        self.idle_timer.start(600000)

    def mousePressEvent(self, event):
        self.reset_idle_timer()
        if not self.input_bubble.isHidden():
            self.input_bubble.hide()
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            if not self.is_sleeping:
                self.random_interaction()
                if random.random() < 0.5:
                    self.show_bubble(random.choice(self.dialogs))
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        self.reset_idle_timer()
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)
            tilt = math.sin(self.pos().x() * 0.2) * 10
            transform = QTransform().rotate(tilt)
            self.update_image(transform)
            if random.random() < 0.02:
                 self.show_bubble("呜哇，飞起来啦！", 1000)

    def mouseReleaseEvent(self, event):
        self.reset_idle_timer()
        if event.button() == Qt.LeftButton:
            self.dragging = False
            if not self.is_sleeping:
                self.update_image()

    def wheelEvent(self, event):
        self.reset_idle_timer()
        delta = event.angleDelta().y()
        if delta > 0:
            self.scale_factor = min(self.scale_factor + 0.1, 3.0)
        else:
            self.scale_factor = max(self.scale_factor - 0.1, 0.5)
        self.update_image()
        
    def show_bubble(self, text, duration=3000):
        center_x = self.pos().x() + self.width() // 2
        pos = QPoint(center_x, self.pos().y())
        self.dialog_bubble.show_text(text, pos, duration)

    def random_interaction(self):
        choice = random.randint(0, 2)
        if choice == 0:
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(300)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.5, self.pos() - QPoint(0, 50))
            self.anim.setEndValue(self.pos())
            self.anim.start()
        elif choice == 1:
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(300)
            start_pos = self.pos()
            self.anim.setStartValue(start_pos)
            self.anim.setKeyValueAt(0.25, start_pos + QPoint(10, 0))
            self.anim.setKeyValueAt(0.75, start_pos - QPoint(10, 0))
            self.anim.setEndValue(start_pos)
            self.anim.start()
        elif choice == 2:
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(200)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.5, self.pos() + QPoint(0, 20))
            self.anim.setEndValue(self.pos())
            self.anim.start()

    def spawn_sleep_particle(self):
        if self.is_sleeping:
            start_x = self.width() // 2
            start_y = self.height() // 4
            end_x = start_x + random.randint(20, 60)
            end_y = start_y - random.randint(50, 80)
            Particle(self, "Z", "#87ceeb", QPoint(start_x, start_y), QPoint(end_x, end_y), duration=2000)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        settings_action = menu.addAction("设置...")
        chat_action = menu.addAction("陪我聊聊天")
        hide_action = menu.addAction("暂时隐藏")
        quit_action = menu.addAction("退出")
        
        action = menu.exec_(self.mapToGlobal(event.pos()))

    def check_music(self):
        if sys.platform != 'win32':
            return
        try:
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            sessions = AudioUtilities.GetAllSessions()
            playing = False
            playing_pid = None
            for s in sessions:
                if getattr(s, 'Process', None) and "pet" not in s.Process.name().lower():
                    try:
                        meter = s._ctl.QueryInterface(IAudioMeterInformation)
                        if meter.GetPeakValue() > 0.001:
                            playing = True
                            playing_pid = s.Process.pid
                            break
                    except Exception:
                        pass
            
            if playing:
                import random
                note = random.choice(["🎵", "🎶", "🎸"])
                start_x = self.width() // 2 + random.randint(-20, 20)
                start_y = 20
                start_pos = QPoint(start_x, start_y)
                end_pos = QPoint(start_x + random.randint(-30, 30), start_y - random.randint(30, 60))
                Particle(self, note, "#ff69b4", start_pos, end_pos, duration=2000)
                
            current_music = get_current_music_info_sync()
            if not current_music and playing_pid:
                current_music = get_title_from_pid(playing_pid)
            
            import time
            if not hasattr(self, 'last_music_info'):
                self.last_music_info = current_music
                self.last_music_proactive_time = 0
                
            print(f"[DEBUG] playing={playing}, current_music='{current_music}', last_music_info='{self.last_music_info}'")
                
            if playing and current_music and current_music != self.last_music_info:
                if time.time() - self.last_music_proactive_time > 15:
                    self.last_music_proactive_time = time.time()
                    self.last_music_info = current_music
                    print("[DEBUG] Triggering chat thread!")
                    # 若用户正在对话（chat_thread 运行中），跳过切歌评论避免抢占
                    if self.chat_thread is not None and self.chat_thread.isRunning():
                        print("[DEBUG] chat_thread running, skip music proactive")
                    else:
                        prompt = f"（系统后台提示：累累切歌了，当前正在听 {current_music}。请主动发一两句话关心他或评价这首歌，不要太长，假装是你自己不经意听到的，不要提系统后台。）"
                        self.chat_thread = ChatThread(self)
                        self.chat_thread.prompt = prompt
                        self.chat_thread.reply_ready.connect(self.on_chat_reply)
                        self.chat_thread.start()
                else:
                    self.last_music_info = current_music
        except Exception as e:
            print(f"[DEBUG] Exception in check_music: {e}")

    def proactive_observe(self):
        active_window = get_active_window_title()
        if not active_window: return
        
        if active_window != self.last_active_window:
            self.last_active_window = active_window
            import time
            if time.time() - self.last_proactive_time > 60:
                self.last_proactive_time = time.time()
                # 若用户正在对话（chat_thread 运行中），跳过主动评论避免抢占
                if self.chat_thread is not None and self.chat_thread.isRunning():
                    return
                prompt = f"（系统后台提示：累累当前主动打开了新软件 '{active_window}'。请你主动发一两句话关心他或撒娇吐槽，不要太长，假装是你自己不经意看到的，不要提系统后台。）"
                self.chat_thread = ChatThread(self)
                self.chat_thread.prompt = prompt
                self.chat_thread.reply_ready.connect(self.on_chat_reply)
                self.chat_thread.start()
        
    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.show_settings)
        
        chat_action = QAction("陪我聊聊天", self)
        chat_action.triggered.connect(self.action_chat)
        
        pat_action = QAction("摸摸头", self)
        pat_action.triggered.connect(self.action_pat_head)
        
        feed_action = QAction("喂吃的", self)
        feed_action.triggered.connect(lambda: self.show_bubble("啊呜，真好吃！"))
        
        walk_action = QAction("让她走路", self)
        walk_action.setCheckable(True)
        walk_action.setChecked(self.is_walking)
        walk_action.triggered.connect(self.toggle_walk)
        
        sleep_action = QAction("让她睡觉", self)
        sleep_action.setCheckable(True)
        sleep_action.setChecked(self.is_sleeping)
        sleep_action.triggered.connect(self.toggle_sleep)
        
        follow_action = QAction("跟随鼠标", self)
        follow_action.setCheckable(True)
        follow_action.setChecked(self.is_following_mouse)
        follow_action.triggered.connect(self.toggle_follow)
        
        top_action = QAction("置顶开关", self)
        top_action.setCheckable(True)
        top_action.setChecked(self.windowFlags() & Qt.WindowStaysOnTopHint)
        top_action.triggered.connect(self.toggle_top)
        
        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        menu.addAction(chat_action)
        menu.addAction(pat_action)
        menu.addAction(feed_action)
        menu.addSeparator()
        menu.addAction(walk_action)
        menu.addAction(sleep_action)
        menu.addAction(follow_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addAction(top_action)
        menu.addAction(exit_action)
        
        menu.exec_(pos)

    def on_input_entered(self, text):
        self.show_bubble("思考中...")
        self.chat_thread.send_message(text, is_idle=False)

    def action_chat(self):
        screen_rect = QApplication.primaryScreen().availableGeometry()
        self.input_bubble.adjustSize()
        input_w = self.input_bubble.width()
        if input_w < 200:
            input_w = 250
            
        pet_right = self.pos().x() + self.width() + 10
        pet_left = self.pos().x() - input_w - 10
        y_pos = self.pos().y() + self.height() // 3
        
        if pet_right + input_w < screen_rect.width():
            x_pos = pet_right
        else:
            x_pos = max(0, pet_left)
            
        self.input_bubble.show_input(QPoint(x_pos, y_pos))

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def action_pat_head(self):
        self.show_bubble("嘿嘿，好舒服~")
        hand_x = self.pos().x() + self.width() // 2 - self.hand_effect.width() // 2
        hand_y = self.pos().y() - 20 
        self.hand_effect.start_patting(QPoint(hand_x, hand_y))
        
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setStartValue(self.pos())
        self.anim.setKeyValueAt(0.25, self.pos() + QPoint(0, 15))
        self.anim.setKeyValueAt(0.75, self.pos() + QPoint(0, 15))
        self.anim.setEndValue(self.pos())
        self.anim.start()

    def toggle_walk(self, checked):
        self.is_walking = checked
        self.is_following_mouse = False
        self.is_sleeping = False
        if not checked:
            self.update_image()

    def toggle_follow(self, checked):
        self.is_following_mouse = checked
        self.is_walking = False
        self.is_sleeping = False
        if not checked:
            self.update_image()
            
    def toggle_sleep(self, checked):
        self.is_sleeping = checked
        self.is_walking = False
        self.is_following_mouse = False
        if checked:
            transform = QTransform().rotate(90)
            self.update_image(transform)
            self.sleep_timer.start(1500)
            self.spawn_sleep_particle()
        else:
            self.sleep_timer.stop()
            self.update_image()
            
    def toggle_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = Pet()
    pet.show()
    sys.exit(app.exec_())
