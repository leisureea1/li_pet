from faster_whisper import download_model
import os

def download():
    target_dir = "models/faster-whisper-model"
    if os.path.exists(target_dir):
        # We assume if the folder exists and is not empty, it's downloaded
        if len(os.listdir(target_dir)) > 0:
            print("Model already exists in models/faster-whisper-model.")
            return
        
    print("Downloading faster-whisper base model...")
    downloaded_path = download_model("base", output_dir=target_dir)
    print(f"Model successfully downloaded to {target_dir}")

if __name__ == "__main__":
    download()
