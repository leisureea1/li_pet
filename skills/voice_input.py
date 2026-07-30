import os
import sys
import json
import traceback
import wave
from vosk import Model, KaldiRecognizer
from core.utils import get_resource_dir

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
        model_path = os.path.join(get_resource_dir(), "models", "vosk-model")
        if not os.path.exists(model_path):
            print(f"[ERROR] Vosk model not found at {model_path}")
            return None
            
        print("[DEBUG] Loading Vosk offline model...")
        model = Model(model_path)
        print("[DEBUG] Vosk model loaded")
    return model

def speech_to_text(audio_path):
    print(f"[DEBUG] Starting Vosk on {audio_path}")
    try:
        v_model = get_model()
        if not v_model:
            return ""

        wf = wave.open(audio_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("[ERROR] Audio file must be WAV format mono PCM.")
            return ""

        rec = KaldiRecognizer(v_model, wf.getframerate())
        rec.SetWords(True)
        
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                results.append(part_result.get("text", ""))

        part_result = json.loads(rec.FinalResult())
        results.append(part_result.get("text", ""))
        
        text = "".join(results).replace(" ", "")
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
