import os
import urllib.request
import zipfile
import shutil
import sys

def download_and_extract_vosk():
    MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
    ZIP_PATH = "vosk-model-small-cn-0.22.zip"
    EXTRACT_FOLDER = "vosk-model-small-cn-0.22"
    TARGET_DIR = "models/vosk-model"

    if os.path.exists(TARGET_DIR):
        print("Vosk model already exists.")
        return

    print("Downloading Vosk Chinese model...")
    urllib.request.urlretrieve(MODEL_URL, ZIP_PATH)
    
    print("Extracting model...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(".")
        
    print("Moving model to models/vosk-model...")
    os.makedirs("models", exist_ok=True)
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    shutil.move(EXTRACT_FOLDER, TARGET_DIR)
    
    print("Cleaning up...")
    os.remove(ZIP_PATH)
    print("Vosk model ready!")

if __name__ == "__main__":
    download_and_extract_vosk()
