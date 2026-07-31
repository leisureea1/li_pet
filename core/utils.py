import sys
import os
import json
import base64

MUSIC_PLAYER_PROCESSES = frozenset({
    "aimp.exe",
    "applemusic.exe",
    "cloudmusic.exe",
    "foobar2000.exe",
    "kugou.exe",
    "kuwo.exe",
    "musicbee.exe",
    "qqmusic.exe",
    "spotify.exe",
    "vlc.exe",
    "wmplayer.exe",
})

def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_dir():
    if sys.platform == 'win32':
        app_data = os.getenv('APPDATA')
        if app_data:
            path = os.path.join(app_data, "LiTongtongPet")
            os.makedirs(path, exist_ok=True)
            return path
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

def get_active_window_process_name():
    if sys.platform != 'win32':
        return ""
    try:
        import ctypes
        import psutil
        pid = ctypes.c_ulong()
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name().lower() if pid.value else ""
    except Exception:
        return ""

def get_music_title_from_player_window(window_title, process_name):
    """Return a title fallback only for known player processes."""
    title = (window_title or "").strip()
    process = os.path.basename(process_name or "").lower()
    if process not in MUSIC_PLAYER_PROCESSES or " - " not in title:
        return ""
    return title if len(title) > 5 else ""

def get_title_from_pid(target_pid):
    if sys.platform != 'win32':
        return ""
    try:
        import ctypes
        from ctypes import wintypes
        titles = []
        def callback(hwnd, lParam):
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == target_pid:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    titles.append(buff.value)
            return True
            
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), 0)
        
        valid_titles = [t for t in titles if t not in ["Default IME", "MSCTFIME UI", "网易云音乐"] and len(t) > 2]
        if valid_titles:
            for t in valid_titles:
                if " - " in t:
                    return t
            return valid_titles[0]
    except Exception:
        pass
    return ""

def get_current_music_info_sync(timeout=2.0):
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
                    
            session = manager.get_current_session()
            if session:
                playback_info = session.get_playback_info()
                if playback_info:
                    status = playback_info.playback_status
                    status_val = status.value if hasattr(status, 'value') else status
                    if status_val == 4:
                        info = await session.try_get_media_properties_async()
                        title = info.title if info.title else "未知"
                        artist = info.artist if info.artist else "未知"
                        return f"{artist} - {title}"
            return ""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(asyncio.wait_for(fetch(), timeout=timeout))
        finally:
            loop.close()
    except Exception:
        return ""
