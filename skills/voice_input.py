import os
import sys
import json
import traceback
import whisper
import warnings
from core.utils import get_data_dir

warnings.filterwarnings("ignore", category=UserWarning)

TOOL_SCHEMA={
    "name":"voice_input",
    "description":"录制用户语音转文字",
    "category":"audio",
    "permission":"microphone",
    "version":"1.0.0",
    "parameters":{
        "filename":{
            "type":"object",
            "properties":{
                "seconds":{
                    "type":"integer",
                    "description":"录音时长"
                }
            }
        }
    }
}

model = None

def get_model():
    global model
    if model is None:
        print("[DEBUG] loading official whisper (CPU mode)...")
        # base 模型较小且在 CPU 上运行更快
        model = whisper.load_model("base", device="cpu")
        print("[DEBUG] official whisper loaded")
    return model

def speech_to_text(audio_path):
    print(f"[DEBUG] Starting official whisper on {audio_path}")
    try:
        w_model = get_model()
        result = w_model.transcribe(audio_path, language="zh", fp16=False)
        text = result["text"]
        print(f"[DEBUG] Recognition result: {text}")
        return text
    except Exception as e:
        print(f"[ERROR] STT Exception: {e}")
        traceback.print_exc()
        return ""

from skills.audio.recorder import record_audio

def execute(**kwargs):
    try:
        wav_file = record_audio()
        if not wav_file or not os.path.exists(wav_file):
            return {"success": False, "error": "No recordings found"}
            
        text = speech_to_text(wav_file)
        
        # Cleanup
        if os.path.exists(wav_file):
            os.remove(wav_file)
            
        return {
            "success": True,
            "data": {
                "text": text
            },
            "message": "识别完成"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
