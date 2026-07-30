import os
import sys


from skills.audio.recorder import record_audio
from faster_whisper import WhisperModel

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

# 模型初始化


model = None

def get_model():
    global model
    if model is None:
        print("[DEBUG] loading whisper...")
        import faulthandler
        faulthandler.enable()
        
        model = WhisperModel(
            "small",
            device="cpu",
            compute_type="default",
            cpu_threads=4
        )
        print("[DEBUG] whisper loaded")
    return model

def speech_to_text(
        file
):
    whisper = get_model()

    segments,info = whisper.transcribe(
        file,
        language="zh",
        vad_filter=True,
        initial_prompt="这是一个电脑助手语音指令："

    )
    text = ""
    for segment in segments:
        text += segment.text

    return text
def execute(
        **kwargs
):
    try:
        wav = record_audio()
        text = speech_to_text(wav)
        
        # 识别完成后自动删除临时录音文件
        import os
        if os.path.exists(wav):
            os.remove(wav)
            
        print(
            "[debug]",
            text
        )
        return {
            "success": True,
            "data":{
                "text":text
            },
            "message":"识别完成"
        }
    except Exception as e:
        return {
            "success": False,
            "error":str(e)
        }
