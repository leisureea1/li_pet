import os
import requests
from PyQt5.QtCore import QThread, pyqtSignal

class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(str, str, object) # version, url, assets
    no_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, current_version, repo="leisureea1/li_pet", parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.repo = repo
        self.is_manual = False

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json"}
            # Set a timeout so we don't block forever
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "")
                release_url = data.get("html_url", "")
                assets = data.get("assets", [])
                
                # Simple string comparison or stripping 'v'
                # Assuming formats like 'v1.2.8'
                def parse_ver(v_str):
                    return [int(x) for x in v_str.lstrip('v').split('.') if x.isdigit()]

                curr = parse_ver(self.current_version)
                latest = parse_ver(latest_version)
                
                if latest > curr and release_url:
                    self.update_available.emit(latest_version, release_url, assets)
                else:
                    self.no_update.emit(self.current_version)
        except Exception as e:
            print(f"[Updater] Update check failed: {e}")
            self.error_occurred.emit(str(e))

class FileDownloaderThread(QThread):
    progress = pyqtSignal(int, int) # downloaded, total
    finished = pyqtSignal(str) # file_path
    error = pyqtSignal(str) # error_message

    def __init__(self, url, dest_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest_path = dest_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # We don't verify SSL purely in case users have weird corporate proxies, but standard is fine
            response = requests.get(self.url, stream=True, timeout=15)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(self.dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if self._is_cancelled:
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
                        
            if not self._is_cancelled:
                self.finished.emit(self.dest_path)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
