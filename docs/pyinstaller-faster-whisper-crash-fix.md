# PyInstaller 打包后 faster-whisper 崩溃问题排查与修复

## 问题现象

使用 PyInstaller 打包 `pet.py` 后，运行 `pet.exe` 时静默退出，无任何 Python 异常信息：

```
[DEBUG] Loading faster-whisper offline model...
Windows fatal exception: access violation

Current thread 0x00005b90 (most recent call first):
  File "faster_whisper\transcribe.py", line 689 in __init__
  File "skills\voice_input.py", line 43 in get_model
  File "pet.py", line 1140 in <module>
```

进程直接被 Windows 杀死，Python 的 `try/except` 无法捕获 C 层的 access violation。

---

## 排查过程

### 1. 初步怀疑：UPX 压缩损坏 DLL

`pet.spec` 中 `COLLECT` 使用了 `upx=True`，UPX 压缩原生 DLL（ctranslate2.dll、onnxruntime DLL）可能损坏。

**修复**：`upx_exclude=['*.dll', '*.pyd', '*.so']` → 无效，问题依旧。

### 2. 怀疑：compute_type 兼容性

`int8` 量化需要 CPU 支持特定指令集（AVX2），部分 CPU 可能不兼容。

**修复**：降级尝试 `auto` → `int8` → `int8_float16` → 无效。

### 3. 怀疑：onnxruntime 冲突

`pet.spec` 显式 `collect_all('onnxruntime')` 可能加载了与 ctranslate2 内置 onnxruntime 冲突的 DLL。

**修复**：移除显式 onnxruntime 收集 → 无效。

### 4. 怀疑：Intel OpenMP 冲突

`libiomp5md.dll` 可能被多个库重复加载。

**修复**：设置 `KMP_DUPLICATE_LIB_OK=TRUE`、`OMP_NUM_THREADS=4` → 无效。

### 5. 源码对比测试

源码环境下所有组合均正常：
- ✅ `compute_type="auto"` — 正常
- ✅ `compute_type="int8"` — 正常
- ✅ scipy + ctranslate2 — 正常
- ✅ pygame + ctranslate2 — 正常

**结论**：问题仅出现在 PyInstaller 打包环境中。

### 6. 最小化隔离测试

创建 `test_ct2.py`，仅包含 ctranslate2 + 模型加载：

| 测试组合 | 结果 |
|----------|------|
| 仅 ctranslate2 | ✅ 正常 |
| ctranslate2 + scipy | ✅ 正常 |
| ctranslate2 + PyQt5 | ❌ 崩溃 |
| ctranslate2 先加载，再 import PyQt5 | ❌ 崩溃 |

### 7. 定位根因

**PyQt5 的 Qt DLL 是罪魁祸首。** 

即使 Python 层面 `import ctranslate2` 先于 `import PyQt5`，只要 PyQt5 的 DLL 存在于 `_internal/` 目录中，Windows 的 DLL 加载器就会在 ctranslate2 初始化时加载冲突的运行时库（MSVCP140、VCRUNTIME140 的 Qt 私有副本等），导致 ctranslate2 的 Intel OpenMP（libiomp5md）初始化时发生内存访问冲突。

`pet.py` 第 1 行的 `import onnxruntime`（残留的无用导入）加剧了此问题，它提前初始化了 ONNX Runtime 的线程池，使得后续 ctranslate2 的 OpenMP 初始化冲突概率增大。

---

## 最终解决方案

### 核心策略：`ctypes` 预加载（LOAD_WITH_ALTERED_SEARCH_PATH）

PyInstaller 按固定顺序运行 runtime hooks：`runtime_onnx.py` → `pyi_rth_pyqt5.py`。

在 `runtime_onnx.py` 中，利用这个时间窗口，用 `ctypes.CDLL(path, winmode=0x00000008)` 在 PyQt5 hook 污染 DLL 搜索路径**之前**预加载 ctranslate2 的核心 DLL。

`winmode=0x00000008` 即 `LOAD_WITH_ALTERED_SEARCH_PATH`，告诉 Windows：**该 DLL 的依赖优先从 DLL 自身目录查找**，而非全局 `_internal` 目录。

### 修改清单

#### 1. `pet.py` — 移除无用 import

```python
# 第 1 行：删除 import onnxruntime（残留无用导入，会提前初始化 ONNX Runtime 线程池）
```

#### 2. `hooks/runtime_onnx.py` — 核心修复：预加载 DLL

```python
import os, sys, ctypes

if getattr(sys, 'frozen', False):
    os.environ.setdefault("CT2_FORCE_CPU", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "4")

    ct2_dir = os.path.join(sys._MEIPASS, 'ctranslate2')
    if os.path.exists(ct2_dir):
        os.add_dll_directory(ct2_dir)

        # LOAD_WITH_ALTERED_SEARCH_PATH (0x8): resolve deps from ct2_dir, not _internal
        for dll_name in ('libiomp5md.dll', 'ctranslate2.dll'):
            dll = os.path.join(ct2_dir, dll_name)
            if os.path.exists(dll):
                try:
                    ctypes.CDLL(dll, winmode=0x00000008)
                except Exception:
                    pass
```

#### 3. `pet.spec` — 精简配置

- 移除显式 `collect_all('onnxruntime')`
- `upx_exclude=['*.dll', '*.pyd', '*.so']`
- `debug=False`（生产构建）

#### 4. `skills/voice_input.py` — 保持不变

进程内正常加载模型，无需子进程。


---

## 构建命令

由于 C 盘空间不足，构建输出到 D 盘：

```powershell
pyinstaller pet.spec --distpath D:\pet_dist --workpath D:\pet_build
```

产物目录：`D:\pet_dist\pet\`，部署时整体复制 `pet` 文件夹。

---

## 经验教训

1. **Access violation 无法被 Python try/except 捕获** — C 扩展层的崩溃会直接杀死进程。

2. **PyInstaller runtime hook 有执行顺序** — 自定义 hook（`runtime_onnx.py`）在官方 hook（`pyi_rth_pyqt5.py`）之前运行，这个时间窗口可以用于预加载 DLL。

3. **`LOAD_WITH_ALTERED_SEARCH_PATH` 是解决 PyInstaller DLL 冲突的利器** — 让 DLL 从自身目录解析依赖，而非全局 `_internal`。

4. **最小化二分法是定位打包问题的有效手段** — 从最简依赖逐步增加直到重现问题。
