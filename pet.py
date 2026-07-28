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
        APP_CONFIG["api_key"] = self.api_key_input.text().strip()
        APP_CONFIG["autostart"] = self.autostart_checkbox.isChecked()
        APP_CONFIG["enable_voice"] = self.voice_checkbox.isChecked()
        save_config(APP_CONFIG)
        set_autostart(APP_CONFIG["autostart"])
        QMessageBox.information(self, "成功", "设置已保存！彤彤记住了哦~")
        self.accept()

class ChatThread(QThread):
    reply_ready = pyqtSignal(str)

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
            "如果你想设定一个倒计时提醒累累做某事，请在回复内容的最后，按照这种格式加上一行标记：[REMINDER:秒数:提醒内容]。"
            f"例如：[REMINDER:600:该喝水啦！]{context_str}\n{sys_str}"
        )

    def run(self):
        self.history[0] = {"role": "system", "content": self.get_system_prompt()}
        
        url = "https://api.deepseek.com/chat/completions"
        api_key = APP_CONFIG.get("api_key", "")
        if not api_key:
            self.reply_ready.emit("累累，你还没有配置 API Key 哦，右键点击我进行设置吧！")
            return
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        current_messages = list(self.history)
        if self.is_idle:
            current_messages.append({"role": "user", "content": "（累累很久没理你了，你现在在想什么？主动跟他说一句话吧，要符合你的角色设定，不超过15个字）"})
        else:
            if self.message:
                self.history.append({"role": "user", "content": self.message})
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
                self.history.append({"role": "assistant", "content": reply_text})
                if len(self.history) > 21:
                    self.history = [self.history[0]] + self.history[-20:]
                save_encrypted_json("history.dat", self.history)
            
            self.reply_ready.emit(reply_text)
        except Exception as e:
            self.reply_ready.emit("呜呜，网络不通畅，我想不出来了...")
            print("API Error:", e)

    def send_message(self, text, is_idle=False):
        self.message = text
        self.is_idle = is_idle
        self.start()

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
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_text(self, text, pos, duration=3000):
        self.label.setText(text)
        self.label.adjustSize()
        self.resize(self.label.size())
        
        bubble_x = pos.x() - self.width() // 2
        bubble_y = pos.y() - self.height() - 10
        self.move(bubble_x, bubble_y)
        self.show()
        self.timer.start(duration)

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
        
        self.chat_thread = ChatThread(self)
        self.chat_thread.reply_ready.connect(self.on_chat_reply)
        
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.trigger_idle_chat)
        self.idle_timer.start(30000)

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
            self.chat_thread.send_message("", is_idle=True)

    def reset_idle_timer(self):
        self.idle_timer.stop()
        self.idle_timer.start(30000)

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
