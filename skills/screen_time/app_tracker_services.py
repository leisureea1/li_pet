import os
import time
import sqlite3
from datetime import datetime,date


import psutil
import win32gui
import win32process
import ctypes

DEBUG = True

def debug(msg):
    if DEBUG:
        print(msg)

app_data = os.getenv("APPDATA")
if app_data:
    db_dir = os.path.join(app_data, "LiTongtongPet")
    os.makedirs(db_dir, exist_ok=True)
else:
    db_dir = os.path.dirname(__file__)
DB_FILE = os.path.join(db_dir, "app_usage.db")

# 初始化数据库

def init_db():
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS usage(
        app TEXT,
        title TEXT,
        day TEXT,
        seconds INTEGER,
        PRIMARY KEY(app,title,day)
        )
""")
    conn.commit()
    conn.close()

#获取当前窗口

def get_foreground_app():
    hwnd = win32gui.GetForegroundWindow()

    if not hwnd:
        debug("未获取到窗口")
        return None

    pid = win32process.GetWindowThreadProcessId(hwnd)[1]

    try:
        p = psutil.Process(pid)
        app = p.name()
        title = win32gui.GetWindowText(hwnd)
        debug(
            f"当前窗口:{app} | pid:{pid} |标题:{title}"
        )
        return {
            "app": p.name(),
            "title": win32gui.GetWindowText(hwnd)
        }
    except:
        return None

# 判断用户是否有操作

def user_active():

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_uint),
            ("dwTime", ctypes.c_uint),
        ]

    info = LASTINPUTINFO()

    info.cbSize =ctypes.sizeof(info)

    ctypes.windll.user32.GetLastInputInfo(
        ctypes.byref(info)
    )
    ctypes.windll.Kernel32.GetTickCount64.restype = ctypes.c_uint64

    idle =(
        ctypes.windll.kernel32.GetTickCount64() - info.dwTime
    ) / 1000

    #超过五分钟认为离开电脑

    return idle < 300

#写入数据库

def add_usage(app,title,seconds):

    conn=sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO usage
        (
            app,
            title,
            day,
            seconds
        )
        VALUES
        (?,?,?,?)
        ON CONFLICT(app,title,day)
        DO UPDATE SET seconds = 
        seconds + excluded.seconds
        """,
        (
            app,
            title,
            str(date.today()),
            seconds
         )
    )
    conn.commit()
    conn.close()
    debug(
        f"记录 {app} + {seconds}s"
    )

#主循环

def run():

    init_db()

    print(
        "应用追踪已启动"
    )
    last_save_time = time.time()
    cache = {}
    while True:

        if user_active():

            info = get_foreground_app()

            if info:
                key = (info["app"], info["title"])
                cache[key] = cache.get(key, 0) + 1
        if time.time() - last_save_time > 60:
            if cache:
                conn = sqlite3.connect(DB_FILE)
                for (app,title),secs in cache.items():
                    conn.execute(
                        """
                        INSERT INTO usage(app,title,day,seconds)
                        VALUES(?,?,?,?)
                        ON CONFLICT(app,title,day)
                        DO UPDATE SET seconds = seconds + excluded.seconds""",
                        (app,title,str(date.today()),secs)
                    )
                conn.commit()
                conn.close()
                cache.clear()
                last_save_time = time.time()
        time.sleep(1)
if __name__ == "__main__":
    run()