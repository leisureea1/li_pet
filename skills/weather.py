import requests

TOOL_SCHEMA = {
    "name": "weather",
    "description": "【强制调用】只要用户询问天气、气温、下雨、出门穿搭等相关问题，必须使用此技能，绝对不能凭空回答！",
    "category": "environment",
    "permission": "network",
    "version": "1.0",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称，例如：北京。如果用户没说，请留空。"},
            "forecast_days": {"type": "integer", "description": "预报天数（可选）。如果不填则查询当前实时天气。如果填入3，则查询今天、明天、后天3天的预报。支持3, 7, 10, 15"},
            "need_indices": {"type": "boolean", "description": "是否需要查询今日的生活指数（如穿衣、感冒、运动、紫外线等）。当用户询问穿衣建议或是否适合外出等，设为true。"}
        }
    }
}

def execute(city=None, forecast_days=None, need_indices=False, **kwargs):
    print(f"[DEBUG] [Weather API] Requesting: city={city}, forecast_days={forecast_days}, need_indices={need_indices}")
    if not city:
        return {"success": False, "error": "你必须回复询问用户想查询哪个城市的天气"}
    
    # QWeather Key
    api_key = "0f95c1de07944c60b0c3340e6ad486c3"
    
    try:
        # Step 1: Get location ID
        geo_url = f"https://geoapi.qweather.com/v2/city/lookup?location={city}&key={api_key}"
        geo_resp = requests.get(geo_url, timeout=5).json()
        
        if geo_resp.get("code") != "200" or not geo_resp.get("location"):
            return {"success": False, "error": f"找不到城市：{city}"}
            
        location_id = geo_resp["location"][0]["id"]
        city_name = geo_resp["location"][0]["name"]
        
        weather_desc = ""
        
        if forecast_days:
            # 兼容非标准天数，适配最近的枚举值
            days = 3
            if forecast_days > 10: days = 15
            elif forecast_days > 7: days = 10
            elif forecast_days > 3: days = 7
                
            weather_url = f"https://np6heqnajn.re.qweatherapi.com/v7/weather/{days}d?location={location_id}&key={api_key}"
            weather_resp = requests.get(weather_url, timeout=5).json()
            
            if weather_resp.get("code") == "200":
                daily_data = weather_resp.get("daily", [])
                result_lines = [f"{city_name}预报："]
                for day in daily_data:
                    date = day.get("fxDate")
                    textDay = day.get("textDay")
                    tempMin = day.get("tempMin")
                    tempMax = day.get("tempMax")
                    result_lines.append(f"{date}: 白天{textDay}，气温 {tempMin}~{tempMax}℃")
                
                weather_desc = "\n".join(result_lines)
            else:
                return {"success": False, "error": "无法获取预报信息"}
        else:
            # Step 2: Get current weather
            weather_url = f"https://np6heqnajn.re.qweatherapi.com/v7/weather/now?location={location_id}&key={api_key}"
            weather_resp = requests.get(weather_url, timeout=5).json()
            
            if weather_resp.get("code") == "200":
                now = weather_resp["now"]
                temp = now["temp"]
                text = now["text"]
                wind_dir = now["windDir"]
                wind_scale = now["windScale"]
                
                weather_desc = f"{city_name}当前天气：{text}，气温 {temp}℃，{wind_dir} {wind_scale}级"
            else:
                return {"success": False, "error": "无法获取天气信息"}
                
        # Step 3: Get indices if requested
        if need_indices:
            idx_url = f"https://np6heqnajn.re.qweatherapi.com/v7/indices/1d?type=1,3,5,9&location={location_id}&key={api_key}"
            idx_resp = requests.get(idx_url, timeout=5).json()
            if idx_resp.get("code") == "200":
                indices_list = []
                for idx in idx_resp.get("daily", []):
                    indices_list.append(f"{idx['name']}: {idx['category']} ({idx['text']})")
                
                if indices_list:
                    weather_desc += "\n\n【生活指数】\n" + "\n".join(indices_list)

        print(f"[DEBUG] [Weather API] Result returned to LLM:\n{weather_desc}")
        return {"success": True, "data": {"weather": weather_desc}, "message": f"成功获取{city_name}天气信息"}
    except Exception as e:
        return {"success": False, "error": str(e)}
