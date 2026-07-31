import os
import sys
import json
import traceback
from faster_whisper import WhisperModel
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
        model_path = os.path.join(get_resource_dir(), "models", "faster-whisper-model")
        
        if not os.path.exists(model_path):
            print(f"[ERROR] faster-whisper model not found at {model_path}")
            from faster_whisper import download_model
            model_path = download_model("base", output_dir=model_path)
            
        print("[DEBUG] Loading faster-whisper offline model...")
        for compute_type in ("default", "auto", "int8", "int8_float16"):
            try:
                model = WhisperModel(
                    model_path, device="cpu", compute_type=compute_type,
                    cpu_threads=2, num_workers=1
                )
                print(f"[DEBUG] faster-whisper model loaded (compute_type={compute_type})")
                break
            except Exception as e:
                print(f"[WARN] compute_type={compute_type} failed: {e}")
        else:
            raise RuntimeError("All compute_type attempts failed for faster-whisper")
    return model


def speech_to_text(audio_path):
    print(f"[DEBUG] Starting faster-whisper on {audio_path}")
    try:
        w_model = get_model()
        if not w_model:
            return ""

        segments, info = w_model.transcribe(audio_path, beam_size=5, language="zh",initial_prompt="李彤彤是一只桌宠，她的名字叫李彤彤。")
        
        text = "".join([segment.text for segment in segments]).replace(" ", "")
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
