import os
import sys
import ctypes

if getattr(sys, 'frozen', False):
    # Prevent ctranslate2 from CUDA detection
    os.environ.setdefault("CT2_FORCE_CPU", "1")
    # Prevent Intel OpenMP conflicts
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "4")

    # CRITICAL: Preload ctranslate2 native DLLs NOW, before PyQt5's runtime
    # hook (pyi_rth_pyqt5.py) adds _internal to PATH and pollutes DLL search.
    # Using LOAD_WITH_ALTERED_SEARCH_PATH (0x8) so DLL dependencies are
    # resolved from the DLL's own directory, not from _internal.
    ct2_dir = os.path.join(sys._MEIPASS, 'ctranslate2')
    if os.path.exists(ct2_dir):
        os.add_dll_directory(ct2_dir)

        iomp = os.path.join(ct2_dir, 'libiomp5md.dll')
        if os.path.exists(iomp):
            try:
                ctypes.CDLL(iomp, winmode=0x00000008)
            except Exception:
                pass

        ct2 = os.path.join(ct2_dir, 'ctranslate2.dll')
        if os.path.exists(ct2):
            try:
                ctypes.CDLL(ct2, winmode=0x00000008)
            except Exception:
                pass
