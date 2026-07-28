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

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction, QInputDialog, QLineEdit, QPushButton, QHBoxLayout, QDialog, QFormLayout, QCheckBox, QVBoxLayout, QMessageBox
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
            
    return load_encrypted_json("config.dat", {"api_key": "", "autostart": False, "enable_voice": True})

def save_config(config):
    save_encrypted_json("config.dat", config)

def set_autostart(enable=True):
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, "LiTongtongPet", 0, winreg.REG_SZ, sys.executable)
            else:
                try:
                    winreg.DeleteValue(key, "LiTongtongPet")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set autostart on Windows: {e}")
    elif sys.platform == 'darwin':
        try:
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.leisureea.litongtong.plist")
            if enable:
                plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.leisureea.litongtong</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
                with open(plist_path, "w") as f:
                    f.write(plist_content)
            else:
                if os.path.exists(plist_path):
                    os.remove(plist_path)
        except Exception as e:
            print(f"Failed to set autostart on Mac: {e}")

APP_CONFIG = load_config()

if not APP_CONFIG.get("api_key"):
    APP_CONFIG["api_key"] = "sk-1ad1dacb6e1d4cde851ce2488abfe001"
    save_config(APP_CONFIG)

class TTSThread(QThread):
    ready_signal = pyqtSignal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        
    def run(self):
        try:
            import edge_tts
            import tempfile
            temp_dir = tempfile.gettempdir()
            out_file = os.path.join(temp_dir, "tongtong_voice.mp3")
            
            communicate = edge_tts.Communicate(self.text, "zh-CN-XiaoxiaoNeural")
            asyncio.run(communicate.save(out_file))
            
            self.ready_signal.emit(out_file)
        except Exception as e:
            print("TTS error:", e)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 250)
        self.setStyleSheet('''
            QDialog { background-color: rgba(255, 240, 245, 240); border-radius: 15px; border: 2px solid #ffb6c1; }
            QLabel { color: #ff69b4; font-weight: bold; font-size: 14px; }
            QLineEdit { border: 2px solid #ffb6c1; border-radius: 8px; padding: 5px; background-color: white; color: #333; }
            QPushButton { background-color: #ffb6c1; color: white; border-radius: 10px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #ff69b4; }
            QCheckBox { color: #ff69b4; font-weight: bold; }
        ''')
        
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
        form_layout.addRow(QLabel("声音:"), self.voice_checkbox)
        
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addLayout(header_layout)
        layout.addLayout(form_layout)
        layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        self.old_pos = None

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
        api_key = self.api_key_input.text().strip()
        autostart = self.autostart_checkbox.isChecked()
        enable_voice = self.voice_checkbox.isChecked()
        APP_CONFIG["api_key"] = api_key
        APP_CONFIG["autostart"] = autostart
        APP_CONFIG["enable_voice"] = enable_voice
        save_config(APP_CONFIG)
        set_autostart(autostart)
        QMessageBox.information(self, "成功", "设置已保存！彤彤记住了哦~")
        self.accept()

class ChatThread(QThread):
    reply_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message = ""
        self.is_idle = False
        
        self.history = load_encrypted_json("history.dat", [])
        if not self.history:
            self.history = [{"role": "system", "content": self.get_system_prompt()}]
        else:
            self.history[0] = {"role": "system", "content": self.get_system_prompt()}

    def get_system_prompt(self):
        active_window = get_active_window_title()
        context_str = f"\n(累累当前正在使用的软件窗口是：{active_window})" if active_window else ""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            sys_str = f"当前电脑CPU占用:{cpu}%，内存占用:{mem}%。"
            if cpu > 80 or mem > 80:
                sys_str += " 电脑负载很高，可能有点卡！"
        except:
            sys_str = ""
            
        return (
            "你叫李彤彤，是我的女朋友，虽然你现在变成了一个桌面宠物，但你非常爱我。你称呼我为'累累'。"
            "请展现出女朋友的撒娇、关心和俏皮。请用简短的语言回复（不超过30个字）。"
            "如果你想设定一个倒计时提醒累累做某事（比如累累说'10分钟后提醒我喝水'），请在回复内容的最后，按照这种格式加上一行标记：[REMINDER:秒数:提醒内容]。"
            f"例如：[REMINDER:600:该喝水啦！]{context_str}\n{sys_str}"
        )

    def run(self):
        self.history[0] = {"role": "system", "content": self.get_system_prompt()}
        
        if self.message:
            self.history.append({"role": "user", "content": self.message})
            
        api_key = APP_CONFIG.get("api_key", "")
        if not api_key:
            self.reply_signal.emit("累累，你还没有配置 API Key 哦，右键点击我进行设置吧！")
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": "deepseek-chat",
            "messages": self.history,
            "temperature": 0.7
        }

        try:
            response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                reply_text = result["choices"][0]["message"]["content"]
                self.history.append({"role": "assistant", "content": reply_text})
                if len(self.history) > 21:
                    self.history = [self.history[0]] + self.history[-20:]
                save_encrypted_json("history.dat", self.history)
                self.reply_signal.emit(reply_text)
            else:
                self.reply_signal.emit("唔...我好像没听懂，再试一次吧~")
        except Exception as e:
            print(e)
            if self.is_idle:
                self.reply_signal.emit("呼噜噜...zzz")
            else:
                self.reply_signal.emit("呜呜，网络好像出问题了，连接不上大脑...")

    def send_message(self, text):
        self.message = text
        self.is_idle = False
        self.start()

    def send_idle_chat(self):
        self.message = ""
        self.is_idle = True
        self.start()

class Bubble(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet('''
            QLabel {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #ffb6c1;
                border-radius: 15px;
                padding: 10px;
                font-family: 'Microsoft YaHei';
                font-size: 14px;
                color: #333333;
            }
        ''')
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.hide()

    def show_message(self, text, pos, duration=5000):
        self.setText(text)
        self.adjustSize()
        bubble_x = pos.x() + 50
        bubble_y = pos.y() - self.height() + 20
        self.move(bubble_x, bubble_y)
        self.show()

        QTimer.singleShot(duration, self.hide)

class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.is_sleeping = False
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.trigger_idle_chat)
        
        self.chat_thread = ChatThread()
        self.chat_thread.reply_signal.connect(self.on_chat_reply)
        
        self.initUI()
        self.reset_idle_timer()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        
        self.image_label = QLabel(self)
        self.pixmap = QPixmap(os.path.join(get_resource_dir(), "character_fullbody.png"))
        if self.pixmap.isNull():
            self.pixmap = QPixmap(200, 200)
            self.pixmap.fill(QColor(255, 182, 193))
        
        scaled_pixmap = self.pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())
        
        self.resize(scaled_pixmap.size())
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 250, screen.height() - 250)

        self.bubble = Bubble()
        
        self.pat_label = QLabel(self)
        pat_pixmap = QPixmap(os.path.join(get_resource_dir(), "pat_hand_nobg.png")).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if pat_pixmap.isNull():
            pat_pixmap = QPixmap(50, 50)
            pat_pixmap.fill(Qt.transparent)
        self.pat_label.setPixmap(pat_pixmap)
        self.pat_label.hide()

        self.anim = QPropertyAnimation(self.pat_label, b"pos")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.setLoopCount(3)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        
        chat_action = QAction("陪我聊天", self)
        chat_action.triggered.connect(self.open_chat_input)
        menu.addAction(chat_action)
        
        sleep_action = QAction("睡觉", self)
        sleep_action.triggered.connect(self.sleep_pet)
        menu.addAction(sleep_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        
        menu.exec_(self.mapToGlobal(event.pos()))

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def open_chat_input(self):
        text, ok = QInputDialog.getText(self, '聊天', '和彤彤说点什么吧：')
        if ok and text:
            self.show_bubble("正在思考...")
            self.chat_thread.send_message(text)

    def sleep_pet(self):
        self.is_sleeping = True
        self.show_bubble("彤彤去睡觉啦，晚安累累~")
        self.idle_timer.stop()
        self.setWindowOpacity(0.5)

    def wake_pet(self):
        self.is_sleeping = False
        self.show_bubble("彤彤醒啦，累累在干嘛呢？")
        self.setWindowOpacity(1.0)
        self.reset_idle_timer()

    def show_bubble(self, text, duration=5000):
        self.bubble.show_message(text, self.pos(), duration)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            if self.bubble.isVisible():
                self.bubble.move(self.pos().x() + 50, self.pos().y() - self.bubble.height() + 20)
            event.accept()
            self.reset_idle_timer()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_sleeping:
                self.wake_pet()
            else:
                self.pat_pet()
            event.accept()

    def pat_pet(self):
        self.pat_label.show()
        
        start_pos = QPoint(50, -20)
        end_pos = QPoint(50, 10)
        
        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)
        
        self.anim.finished.connect(self.pat_label.hide)
        self.anim.start()
        
        self.show_bubble("贴贴~ (◍•ᴗ•◍)")
        self.reset_idle_timer()

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
            if APP_CONFIG.get("enable_voice", True):
                self.tts_thread = TTSThread(text, self)
                self.tts_thread.ready_signal.connect(lambda audio_file, txt=text: self.play_tts_and_show_bubble(txt, audio_file))
                self.tts_thread.start()
            else:
                self.show_bubble(text)
                
    def play_tts_and_show_bubble(self, text, audio_file):
        self.show_bubble(text)
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
        except:
            pass

    def trigger_reminder(self, msg):
        if APP_CONFIG.get("enable_voice", True):
            self.tts_thread = TTSThread(msg, self)
            self.tts_thread.ready_signal.connect(lambda audio_file, txt=msg: self.play_tts_and_show_bubble(txt, audio_file))
            self.tts_thread.start()
        else:
            self.show_bubble(msg)

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
        if not self.is_sleeping:
            self.chat_thread.send_idle_chat()
            self.reset_idle_timer()

    def reset_idle_timer(self):
        if not self.is_sleeping:
            idle_time = random.randint(300000, 600000)
            self.idle_timer.start(idle_time)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    pet = Pet()
    pet.show()
    sys.exit(app.exec_())
