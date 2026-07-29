import sqlite3
import math
import json
import requests
import re
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from .config import APP_CONFIG

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
            try:
                cursor.execute('ALTER TABLE working_memory ADD COLUMN prompt_tokens INTEGER DEFAULT 0')
                cursor.execute('ALTER TABLE working_memory ADD COLUMN completion_tokens INTEGER DEFAULT 0')
                cursor.execute('ALTER TABLE working_memory ADD COLUMN total_tokens INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
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

    def add_working_memory(self, role, content, prompt_tokens=0, completion_tokens=0, total_tokens=0):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO working_memory (role, content, timestamp, prompt_tokens, completion_tokens, total_tokens) VALUES (?, ?, ?, ?, ?, ?)', 
                               (role, content, now, prompt_tokens, completion_tokens, total_tokens))
            except sqlite3.OperationalError:
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

    def get_chat_history(self, limit=50):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT role, content, timestamp, prompt_tokens, completion_tokens, total_tokens FROM working_memory ORDER BY timestamp DESC LIMIT ?', (limit,))
                rows = cursor.fetchall()
                return [{"role": r[0], "content": r[1], "timestamp": r[2], "prompt_tokens": r[3], "completion_tokens": r[4], "total_tokens": r[5]} for r in rows]
            except sqlite3.OperationalError:
                cursor.execute('SELECT role, content, timestamp FROM working_memory ORDER BY timestamp DESC LIMIT ?', (limit,))
                rows = cursor.fetchall()
                return [{"role": r[0], "content": r[1], "timestamp": r[2], "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0} for r in rows]

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

    def record_tokens(self, category, prompt_tokens, completion_tokens, total_tokens):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO token_usage (category, prompt_tokens, completion_tokens, total_tokens, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (category, prompt_tokens, completion_tokens, total_tokens, now))
            conn.commit()

    def get_token_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 获取各分类汇总
            cursor.execute('''
                SELECT category, SUM(total_tokens)
                FROM token_usage
                GROUP BY category
            ''')
            category_totals = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 获取最近7天的每日总消耗
            cursor.execute('''
                SELECT date(timestamp), SUM(total_tokens)
                FROM token_usage
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY date(timestamp)
                ORDER BY date(timestamp) ASC
            ''')
            daily_totals = [{"date": row[0], "tokens": row[1]} for row in cursor.fetchall()]
            
            return {
                "categories": category_totals,
                "daily": daily_totals
            }

class MemoryExtractorThread(QThread):
    memory_extracted = pyqtSignal(list)
    
    def __init__(self, user_msg, ai_reply, memory_manager=None, parent=None):
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
            
            usage = data.get('usage', {})
            if usage and self.memory_manager:
                self.memory_manager.record_tokens("memory_extractor", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))
            
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                memories = json.loads(match.group(0))
                self.memory_extracted.emit(memories)
        except Exception as e:
            print("Memory Extractor Error:", e)
