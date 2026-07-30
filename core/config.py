import os
import sys
import json
from .utils import get_data_dir, load_encrypted_json, save_encrypted_json

CURRENT_VERSION = "v1.4.2"

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
    return load_encrypted_json("config.dat", {"api_key": "", "qianfan_api_key": "", "autostart": False, "enable_voice": False, "tts_voice": "zh-CN-XiaoxiaoNeural"})

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
