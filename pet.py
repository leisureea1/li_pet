import sqlite3
from datetime import datetime
import sys
import os
try:
    import onnxruntime
    import tokenizers
except ImportError:
    pass
import random
import math
import requests
import json
import asyncio
import re
import base64
import psutil

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction, QInputDialog, QLineEdit, QPushButton, QHBoxLayout, QDialog, QFormLayout, QCheckBox, QVBoxLayout, QMessageBox, QComboBox, QSizePolicy, QProgressDialog
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QPoint, pyqtProperty, QSize, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QCursor, QTransform, QFont, QPainter, QColor

from core.utils import get_resource_dir, get_data_dir, get_active_window_title, get_title_from_pid, get_current_music_info_sync, load_encrypted_json, save_encrypted_json
from core.config import APP_CONFIG, save_config, set_autostart, CURRENT_VERSION
from core.chat import TTSThread, ChatThread, QuoteGenThread
from core.companion import CompanionThread
from core.event import EventManager
from core.memory import MemoryManager
from core.skill_manager import SkillManager
from core.web_server import WebServerThread
from core.updater import UpdateCheckerThread
import webbrowser


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
                color: #333333;
            }
        """)
        self.label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def resizeEvent(self, event):
        # label 充满整个 DialogBubble（padding 由 label 的 margin 控制）
        self.label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def show_text(self, text, pos, duration=3000):
        self.label.setText(text)
        self.label.setWordWrap(True)

        # 获取宠物所在屏幕（双屏安全：用宠物中心点，回退到主屏）
        pet_center = QPoint(pos.x(), pos.y())
        screen = QApplication.screenAt(pet_center)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        max_w = int(screen_rect.width() * 0.6)

        # 让 QLabel 自己算尺寸，不用 QFontMetrics
        self.label.setMaximumWidth(max_w)
        self.label.adjustSize()
        hint = self.label.sizeHint()
        bubble_w = hint.width()
        bubble_h = hint.height()

        self.resize(bubble_w, bubble_h)

        screen_left = screen_rect.left()
        screen_right = screen_rect.right()
        screen_top = screen_rect.top()
        screen_bottom = screen_rect.bottom()

        pet_x = pos.x()
        pet_y = pos.y()

        # 默认气泡居中于宠物上方
        bubble_x = pet_x - bubble_w // 2
        bubble_y = pet_y - bubble_h - 10

        # 若气泡会溢出右侧，改为在宠物左侧显示
        if bubble_x + bubble_w > screen_right:
            bubble_x = pet_x - bubble_w  # 气泡右边贴着宠物，向左展开
        # 若气泡会溢出左侧，改为在宠物右侧显示
        elif bubble_x < screen_left:
            bubble_x = pet_x  # 气泡左边贴着宠物，向右展开

        # 最终兜底：确保不越界
        if bubble_x < screen_left:
            bubble_x = screen_left
        if bubble_x + bubble_w > screen_right:
            bubble_x = screen_right - bubble_w
        if bubble_y < screen_top:
            bubble_y = screen_top
        if bubble_y + bubble_h > screen_bottom:
            bubble_y = screen_bottom - bubble_h

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
        
        # Initialize MemoryManager before WebServer
        db_path = os.path.join(get_data_dir(), "memory.db")
        self.memory_manager = MemoryManager(db_path)
        
        self.tts_thread = None
        self.web_server_thread = WebServerThread(self.memory_manager, port=5050, parent=self, update_callback=self.manual_check_update)
        self.web_server_thread.start()
        
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
        
        self.companion_thread = None
        self.event_manager = EventManager()
        self.event_manager.companion_event_ready.connect(self.trigger_companion_chat)
        
        self.chat_thread = ChatThread(self)
        self.chat_thread.reply_ready.connect(self.on_chat_reply)
        self.chat_thread.reminder_ready.connect(self.schedule_reminder)
        
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

        # Update checker
        self.updater_thread = UpdateCheckerThread(CURRENT_VERSION, parent=self)
        self.updater_thread.update_available.connect(self.on_update_available)
        self.updater_thread.no_update.connect(self.on_no_update)
        self.updater_thread.error_occurred.connect(self.on_update_error)
        # Delay the update check slightly to not block startup
        QTimer.singleShot(3000, self.updater_thread.start)

    def manual_check_update(self):
        self.updater_thread.is_manual = True
        self.updater_thread.start()
        
    def on_no_update(self, version):
        if self.updater_thread.is_manual:
            QMessageBox.information(self, "检查更新", f"当前已经是最新版本 {version} 啦！")
            
    def on_update_error(self, error):
        if self.updater_thread.is_manual:
            QMessageBox.warning(self, "检查更新", f"检查更新失败：{error}")

    def on_update_available(self, version, url, assets):
        import platform
        
        target_name = ""
        if sys.platform == 'win32':
            target_name = "LiTongtong_Setup.exe"
        elif sys.platform == 'darwin':
            if platform.machine() == 'arm64':
                target_name = "LiTongtong-Apple.dmg"
            else:
                target_name = "LiTongtong-Intel.dmg"
                
        download_url = None
        for asset in assets:
            if asset.get('name') == target_name:
                download_url = asset.get('browser_download_url')
                break

        msg = QMessageBox(self)
        msg.setWindowTitle("发现新版本")
        if download_url:
            msg.setText(f"发现新版本 {version}，是否立即更新？")
            msg.button(QMessageBox.Yes).setText("立即更新")
        else:
            msg.setText(f"发现新版本 {version}，是否前往下载更新？")
            msg.button(QMessageBox.Yes).setText("前往下载")
            
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.button(QMessageBox.No).setText("暂不更新")
        msg.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        
        if msg.exec_() == QMessageBox.Yes:
            if download_url:
                self.start_download(download_url, target_name)
            else:
                import webbrowser
                webbrowser.open(url)

    def start_download(self, url, filename):
        import tempfile
        self.download_path = os.path.join(tempfile.gettempdir(), filename)
        
        self.progress_dialog = QProgressDialog("正在下载更新...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("自动更新")
        self.progress_dialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        
        from core.updater import FileDownloaderThread
        self.downloader = FileDownloaderThread(url, self.download_path, parent=self)
        self.downloader.progress.connect(self.on_download_progress)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.on_download_error)
        
        self.progress_dialog.canceled.connect(self.downloader.cancel)
        
        self.downloader.start()
        self.progress_dialog.show()
        
    def on_download_progress(self, downloaded, total):
        if total > 0:
            percentage = int((downloaded / total) * 100)
            self.progress_dialog.setValue(percentage)
            mb_dl = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.progress_dialog.setLabelText(f"正在下载更新... ({mb_dl:.1f}MB / {mb_total:.1f}MB)")
            
    def on_download_finished(self, file_path):
        self.progress_dialog.close()
        import subprocess
        if sys.platform == 'win32':
            os.startfile(file_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', file_path])
        QApplication.quit()
        
    def on_download_error(self, error_msg):
        self.progress_dialog.close()
        QMessageBox.warning(self, "更新失败", f"下载失败: {error_msg}\n请稍后重试或手动前往官网下载。")

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
            center_y = self.pos().y() + self.height() // 2
            bubble_w = self.dialog_bubble.width()
            bubble_h = self.dialog_bubble.height()
            bubble_x = center_x - bubble_w // 2
            bubble_y = self.pos().y() - bubble_h - 10
            # 屏幕边界避让：用宠物中心所在屏幕（双屏安全）
            pet_center = QPoint(center_x, center_y)
            screen = QApplication.screenAt(pet_center) or QApplication.primaryScreen()
            screen_rect = screen.availableGeometry()
            if bubble_x + bubble_w > screen_rect.right():
                bubble_x = self.pos().x() - bubble_w
            elif bubble_x < screen_rect.left():
                bubble_x = self.pos().x() + self.width()
            if bubble_x < screen_rect.left():
                bubble_x = screen_rect.left()
            if bubble_x + bubble_w > screen_rect.right():
                bubble_x = screen_rect.right() - bubble_w
            if bubble_y < screen_rect.top():
                bubble_y = screen_rect.top()
            if bubble_y + bubble_h > screen_rect.bottom():
                bubble_y = screen_rect.bottom() - bubble_h
            self.dialog_bubble.move(bubble_x, bubble_y)
            
    def on_chat_reply(self, text):
        emotion = "normal"
        # 查找所有的 emotion 标签，我们只用最后一个作为最终的动画状态
        matches = re.findall(r'\[EMOTION:([a-zA-Z]+)\]', text)
        if matches:
            emotion = matches[-1].lower()
            
        # 移除文本中所有的 [EMOTION:xxx] 标签
        text = re.sub(r'\[EMOTION:[a-zA-Z]+\]\s*', '', text).strip()

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
            if emotion != "normal":
                self.trigger_emotion_animation(emotion)
                
            rate = "+0%"
            pitch = "+0Hz"
            if emotion == "happy":
                rate = "+10%"
                pitch = "+10Hz"
            elif emotion == "sleepy":
                rate = "-20%"
                pitch = "-10Hz"
            elif emotion == "angry":
                rate = "+0%"
                pitch = "-10Hz"
            elif emotion == "surprised":
                rate = "+10%"
                pitch = "+20Hz"

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
                self.tts_thread = TTSThread(text, voice=voice_id, rate=rate, pitch=pitch, parent=self)
                self.tts_thread.ready_signal.connect(lambda audio_file, txt=text: self.play_tts_and_show_bubble(txt, audio_file))
                self.tts_thread.start()
            else:
                duration = max(3000, len(text) * 200) # dynamic duration based on length
                self.show_bubble(text, duration)

    def trigger_emotion_animation(self, emotion):
        if emotion == "happy":
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(400)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.25, self.pos() - QPoint(0, 30))
            self.anim.setKeyValueAt(0.5, self.pos())
            self.anim.setKeyValueAt(0.75, self.pos() - QPoint(0, 30))
            self.anim.setEndValue(self.pos())
            self.anim.start()
        elif emotion == "sleepy":
            self.spawn_sleep_particle()
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(1000)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.5, self.pos() + QPoint(0, 10))
            self.anim.setEndValue(self.pos())
            self.anim.start()
        elif emotion == "angry":
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(300)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.2, self.pos() + QPoint(10, 0))
            self.anim.setKeyValueAt(0.4, self.pos() - QPoint(10, 0))
            self.anim.setKeyValueAt(0.6, self.pos() + QPoint(10, 0))
            self.anim.setKeyValueAt(0.8, self.pos() - QPoint(10, 0))
            self.anim.setEndValue(self.pos())
            self.anim.start()
        elif emotion == "surprised":
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(300)
            self.anim.setStartValue(self.pos())
            self.anim.setKeyValueAt(0.3, self.pos() - QPoint(0, 50))
            self.anim.setEndValue(self.pos())
            self.anim.setEasingCurve(QEasingCurve.OutElastic)
            self.anim.start()

    def play_tts_and_show_bubble(self, text, audio_file):
        self.show_bubble(text, duration=0) # Keeps open until audio finishes
        self.current_audio_file = audio_file
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
            import os
            if not pygame.mixer.music.get_busy():
                self.audio_check_timer.stop()
                self.dialog_bubble.hide()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                if hasattr(self, 'current_audio_file') and os.path.exists(self.current_audio_file):
                    try:
                        os.remove(self.current_audio_file)
                    except Exception as e:
                        print(f"Failed to delete temp audio {self.current_audio_file}: {e}")
        except:
            if hasattr(self, 'audio_check_timer'):
                self.audio_check_timer.stop()
            self.dialog_bubble.hide()

    def schedule_reminder(self, seconds, msg):
        QTimer.singleShot(seconds * 1000, lambda m=msg: self.trigger_reminder(m))

    def trigger_reminder(self, message):
        if APP_CONFIG.get("enable_voice", True):
            voice_id = APP_CONFIG.get("tts_voice", "zh-CN-XiaoxiaoNeural")
            self.tts_thread = TTSThread(message, voice=voice_id, parent=self)
            self.tts_thread.ready_signal.connect(lambda audio_file, txt=message: self.play_tts_and_show_bubble(txt, audio_file))
            self.tts_thread.start()
        else:
            duration = max(3000, len(message) * 200)
            self.show_bubble(message, duration)

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
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.xlsx', '.xls', '.csv']:
                        self.show_bubble("正在像小管家一样仔细核对你的账单哦...")
                        
                        # Process locally first
                        from skills.bill_insight import execute as bill_execute
                        result = bill_execute(file_path=file_path, pet_instance=self, memory_manager=self.chat_thread.memory_manager)
                        
                        if result.get('success'):
                            prompt = (
                                "【系统提示：以下是本地技能分析出的累累的账单洞察数据】\n"
                                f"{result['data']['insights']}\n\n"
                                "【重要要求】请根据以上数据，务必用小管家/女朋友的撒娇口吻给他汇报。不要干瘪地念数字，多发掘有趣的细节进行调侃或关心。\n"
                                "注意：\n"
                                "1. 单向转账不代表借钱或欠债（有可能是家人给的生活费等），绝对不要用“欠债小可怜”等词汇。\n"
                                "2. 重点发掘【充值游戏】的支出，适度调侃他玩游戏。\n"
                                "3. 重点发掘【熬夜买吃的】（如凌晨的美团、每日鲜超市），像女朋友一样关心他是不是失眠、睡不着，告诉他下次睡不着可以找你聊天。\n"
                                "4. 注意【抢买单/推诿】的循环转账现象，如果有，可以调侃他们是不是在玩小游戏。\n"
                                "请像这样俏皮：『[EMOTION:happy] 累累～我偷看了你的账单，你居然晚上不睡觉去买好吃的！是不是失眠啦？下次睡不着找我聊天嘛！...』"
                            )
                            self.chat_thread.send_message(prompt)
                        else:
                            self.show_bubble(f"账单解析失败啦：{result.get('error')}")
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read(8000)
                        if len(content) >= 8000:
                            content += "\n...(内容过长已截断)"
                        prompt = f"累累刚才拖拽丢给我了一份文件，文件名是 {os.path.basename(file_path)}，部分内容如下：\n{content}\n请你结合这份文件对累累说点什么吧。"
                        self.chat_thread.send_message(prompt)
                        self.show_bubble("正在看你给我的文件哦...")
                except Exception as e:
                    print(e)
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
            
            self.event_manager.update_music(current_music)
            
        except Exception as e:
            print(f"[DEBUG] Exception in check_music: {e}")

    def proactive_observe(self):
        active_window = get_active_window_title()
        self.event_manager.update_window(active_window)
        
    def trigger_companion_chat(self, event_data):
        print(f"[DEBUG] Triggering companion chat: {event_data['event']}")
        if self.chat_thread is not None and self.chat_thread.isRunning():
            return
        if self.companion_thread is not None and self.companion_thread.isRunning():
            return
            
        self.companion_thread = CompanionThread(event_data, self)
        self.companion_thread.reply_ready.connect(self.on_chat_reply)
        self.companion_thread.start()
        
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
        exit_action.triggered.connect(self.quit_app)
        
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
        webbrowser.open('http://localhost:5050')

    def quit_app(self):
        if hasattr(self, 'web_server_thread') and self.web_server_thread:
            self.web_server_thread.stop()
            self.web_server_thread.wait(2000)
        QApplication.instance().quit()

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
