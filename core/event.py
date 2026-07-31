import time
from datetime import datetime
import psutil
import ctypes
from PyQt5.QtCore import QObject, pyqtSignal

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint)]

def get_idle_duration():
    """获取系统空闲时间（秒）"""
    try:
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
            millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
    except:
        pass
    return 0.0

class EventManager(QObject):
    companion_event_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        
        self.state = {
            "window": {"name": "", "start_time": 0, "last_notified": ""},
            "music": {"title": "", "start_time": 0, "last_notified": "", "cd_seconds": 15},
            "user": {"idle_start_time": 0, "active_start_time": time.time(), "is_idle": False}
        }
        
        # 冷却记录
        self.last_triggered = {
            "late_night": 0,
            "prolonged_sitting": 0,
            "waiting": 0,
            "window_change": 0,
            "music": 0,
            "global": 0
        }
        
        self.COOLDOWN = {
            "late_night": 14400,       # 4小时
            "prolonged_sitting": 3600, # 1小时
            "waiting": 300,            # 5分钟
            "window_change": 60,       # 切窗口：60秒内不重复
            "music": 10,               # 切歌：10秒内不重复
            "global": 0                # 全局冷却关闭 —— 各事件独立冷却足够
        }
        
        # 记录触发次数，用于情绪状态
        self.trigger_counts = {
            "focus": 0,
            "prolonged_sitting": 0
        }

    def update_window(self, active_window):
        now = time.time()
        
        # 更新窗口状态
        if active_window != self.state["window"]["name"]:
            self.state["window"]["name"] = active_window or ""
            self.state["window"]["start_time"] = now
            
        self._evaluate_events(now)

    def update_music(self, current_music):
        now = time.time()
        
        # 过滤掉由于 API 延迟导致 fallback 读取到播放器纯名称的情况，防止频繁触发切歌
        if current_music and current_music.strip() in ["网易云音乐", "QQ音乐", "Spotify", "Spotify Free", "Spotify Premium", "酷狗音乐", "酷我音乐", "Apple Music"]:
            return
            
        current_music = current_music or ""
        old = self.state["music"]["title"]
        if current_music != old:
            self.state["music"]["title"] = current_music
            self.state["music"]["start_time"] = now if current_music else 0
            if not current_music:
                self.state["music"]["last_notified"] = ""
            
        self._evaluate_events(now)

    def _evaluate_events(self, now):
        # 更新用户空闲状态
        idle_duration = get_idle_duration()
        if idle_duration > 300: # 5分钟没动鼠标键盘算空闲
            if not self.state["user"]["is_idle"]:
                self.state["user"]["is_idle"] = True
                self.state["user"]["idle_start_time"] = now
        else:
            if self.state["user"]["is_idle"]:
                self.state["user"]["is_idle"] = False
                self.state["user"]["active_start_time"] = now

        # 全局冷却拦截
        if now - self.last_triggered["global"] < self.COOLDOWN["global"]:
            return

        # 候选事件队列
        candidates = []
        
        window_duration = now - self.state["window"]["start_time"]
        music_duration = now - self.state["music"]["start_time"] if self.state["music"]["title"] else 0
        active_duration = now - self.state["user"]["active_start_time"] if not self.state["user"]["is_idle"] else 0
        
        window_lower = self.state["window"]["name"].lower() if self.state["window"]["name"] else ""

        # 1. 久坐检测 (URGENT) - 连续活跃 90 分钟
        if active_duration > 5400 and (now - self.last_triggered["prolonged_sitting"] > self.COOLDOWN["prolonged_sitting"]):
            self.trigger_counts["prolonged_sitting"] += 1
            candidates.append({"type": "prolonged_sitting", "priority": 100, "event": "prolonged_sitting", "details": {"active_time": "90+ minutes"}, "context": {"consecutive_triggers": self.trigger_counts["prolonged_sitting"]}})

        # 2. 熬夜检测 (URGENT)
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        is_late_night = (current_hour == 0 and current_minute >= 30) or (1 <= current_hour <= 4)
        if is_late_night and active_duration > 3600 and (now - self.last_triggered["late_night"] > self.COOLDOWN["late_night"]):
            candidates.append({"type": "late_night", "priority": 90, "event": "late_night", "details": {"time": datetime.now().strftime("%H:%M")}})

        # 3. 下载/编译等待检测 (HIGH)
        if now - self.last_triggered["waiting"] > self.COOLDOWN["waiting"]:
            score = 0
            if any(kw in window_lower for kw in ["pip install", "npm", "build", "gradle", "make", "docker"]):
                score += 40
            if idle_duration > 120:  # 2分钟没碰键盘
                score += 30
            if window_duration > 120: # 窗口停留超2分钟
                score += 20
            
            try:
                cpu = psutil.cpu_percent(interval=None)
                if cpu > 20:
                    score += 10
            except:
                pass
                
            if score >= 70:
                candidates.append({"type": "waiting", "priority": 80, "event": "waiting_process", "details": {"window": self.state["window"]["name"], "score": score}})

        # 4. 黏人窗口检测 (HIGH) - 只要换了新窗口且过了 60 秒冷却，就立刻触发
        if self.state["window"]["name"] and self.state["window"]["name"] != self.state["window"]["last_notified"]:
            if now - self.last_triggered["window_change"] > self.COOLDOWN["window_change"]:
                candidates.append({"type": "window_change", "priority": 50, "event": "window_changed", "details": {"app": self.state["window"]["name"]}})

        # 5. 黏人听歌检测 (HIGH) - 只要换了新歌，立刻秒触发，然后进入冷却
        if self.state["music"]["title"] and self.state["music"]["title"] != self.state["music"]["last_notified"]:
            if (now - self.last_triggered["music"] > self.COOLDOWN["music"]):
                parts = self.state["music"]["title"].split(" - ", 1)
                music_desc = f"《{parts[0]}》" + (f" - {parts[1]}" if len(parts) == 2 else "")
                candidates.append({"type": "music", "priority": 60, "event": "music_changed", "details": {"song": music_desc}})

        # 优先级判决与触发
        if candidates:
            # 排序取 priority 最高的
            candidates.sort(key=lambda x: x["priority"], reverse=True)
            winner = candidates[0]
            
            # 更新已通知状态
            if winner["type"] == "window_change":
                self.state["window"]["last_notified"] = self.state["window"]["name"]
            elif winner["type"] == "music":
                self.state["music"]["last_notified"] = self.state["music"]["title"]
            
            # 记录冷却
            self.last_triggered[winner["type"]] = now
            self.last_triggered["global"] = now
            
            # 构建发给 AI 的上下文
            payload = {
                "name": "累累",
                "event": winner["event"],
                "details": winner["details"]
            }
            
            # 只有熬夜等特殊事件才告诉她具体时间，防止她在听歌时老是像老干部一样催睡觉
            if winner["type"] in ["late_night", "prolonged_sitting"]:
                payload["time"] = datetime.now().strftime("%H:%M")
                
            if "context" in winner:
                payload["context"] = winner["context"]
                
            self.companion_event_ready.emit(payload)
