import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

def record_audio(
        filename="input.wav",
        samplerate=16000,
        silence_threshold=0.015, # 音量阈值 (0-1)，可以根据麦克风底噪微调
        silence_duration=1.5,    # 说话停顿几秒认为结束
        timeout=5.0,             # 如果一开始不说话，几秒后自动放弃
        max_duration=30.0        # 最大录音时长，防止无限录音
):
    print("🎤 正在听你说话... (自动检测停顿)")
    
    recording = []
    chunk_duration = 0.1 # 每次读取 100ms 的声音片段
    chunk_samples = int(samplerate * chunk_duration)
    
    max_chunks = int(max_duration / chunk_duration)
    silence_limit = int(silence_duration / chunk_duration)
    timeout_limit = int(timeout / chunk_duration)
    
    silent_chunks = 0
    initial_silent_chunks = 0
    has_spoken = False
    
    try:
        # 使用 InputStream 流式读取麦克风数据
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
            for _ in range(max_chunks):
                chunk, overflow = stream.read(chunk_samples)
                recording.append(chunk)
                
                # 计算这个片段的均方根音量 (RMS)，并归一化到 0.0 - 1.0 的范围
                rms = np.sqrt(np.mean(chunk.astype(np.float32)**2)) / 32768.0
                
                if rms > silence_threshold:
                    # 声音超过阈值，说明正在说话
                    has_spoken = True
                    silent_chunks = 0 # 重置停顿计数器
                else:
                    # 声音低于阈值
                    if has_spoken:
                        silent_chunks += 1
                    else:
                        initial_silent_chunks += 1
                        
                # 判断是否该结束录音
                if has_spoken and silent_chunks >= silence_limit:
                    print("✅ 检测到说话结束。")
                    break
                    
                if not has_spoken and initial_silent_chunks >= timeout_limit:
                    print("⏱️ 太久没说话，自动结束监听。")
                    break
                    
    except Exception as e:
        print(f"录音出错: {e}")

    # 将所有片段拼接为完整的音频数组并保存
    if recording:
        audio_data = np.concatenate(recording, axis=0)
        write(filename, samplerate, audio_data)
        print("💾 录音保存完成")
        
    return filename