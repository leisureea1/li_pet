import os
import sys

if getattr(sys, 'frozen', False):
    ort_path = os.path.join(
        sys._MEIPASS,
        'onnxruntime',
        'capi'
    )
    if os.path.exists(ort_path):
        os.add_dll_directory(ort_path)
