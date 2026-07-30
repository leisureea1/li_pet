import os
import sys
import sqlite3
from datetime import date

from skills.screen_time.app_tracker_services import (
get_foreground_app,
DB_FILE
)

TOOL_SCHEMA ={
    "name": "app_usage",
    "description":
    "查询windows应用使用时间，包括当前应用和今日使用统计",
    "category":"system",
    "permission":"system_read",
    "version":"1.0.0",
    "parameters":
        {
            "type":"object",
            "properties":{
                "action":{
                "type":"string",
                "enum":[
                    "current",
                    "today"
                ],
                "description":
                "current获取当前应用，today获取今日应用使用时间",
            }
        },
    "required":[
        "action"
    ]
}
}

def get_today_usage():
    try:
        conn = sqlite3.connect(DB_FILE)

        rows = conn.execute(
        """
        SELECT
           app,
           title,
           seconds
        FROM usage
        WHERE day=?
        ORDER BY seconds DESC
        """,
        (
            str(date.today()),
        )
    ).fetchall()

        conn.close()
    except sqlite3.OperationalError:
      return[]

    result = []

    for app,title,seconds in rows:
        result.append(
            {
                "app": app,
                "title": title,
                "minutes":
                    round((seconds/60),1),
                "hours":
                    round((seconds/3600),2),
            }
        )
    return result

def execute(
        action="today",
        **kwargs
):
    try:
        data = None
        if action == "current":
            data = get_foreground_app()
        elif action == "today":
            data = get_today_usage()

        else:
            return{
                "success": False,
                "error":"未知action"
            }
        return {
            "success": True,
            "data":{"action":"app_usage","list":data},
            "message":"数据获取成功。请务必严格根据这些真实数据回答累累，具体列出他用了哪些软件、用了多少分钟。不许胡编乱造时间，也不许因为时间太短就不报！"

        }
    except Exception as e:
        return {
            "success": False,
            "error":str(e)
        }