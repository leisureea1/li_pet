import os
import sys
import numpy as np

# Limit CPU threads to prevent UI freezing
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

if getattr(np, 'long', None) is None: np.long = int
if getattr(np, 'ulong', None) is None: np.ulong = int
if getattr(np, 'longlong', None) is None: np.longlong = int
if getattr(np, 'ulonglong', None) is None: np.ulonglong = int
if getattr(np, 'bool', None) is None: np.bool = bool
if getattr(np, 'float', None) is None: np.float = float

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "False"

from skills.screen_ocr.screenshot import capture_screen
from paddleocr import PaddleOCR

TOOL_SCHEMA = {
    "name": "ocr",
    "description": "截图识别屏幕文字，可以读取错误提示，网页内容等",
    "category": "tool",
    "version": "1.0",
    "parameters":
        {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "指定图片路径，不填则截图识别"
                               }

            }
        }


}
ocr_engine = PaddleOCR(
    lang="ch",
    text_detection_model_name='PP-OCRv4_mobile_det',
    text_recognition_model_name='PP-OCRv4_mobile_rec',
    use_angle_cls=False,
    det_db_thresh=0.3,
    det_db_box_thresh=0.5,
    det_db_unclip_ratio=1.5
)

def recognize(image_path):
    results = ocr_engine.predict(
        image_path
    )
    texts = []

    for res in results:
        data = res.json
        if "rec_texts" in data["res"]:
            texts.append(data["res"]["rec_texts"])

    return texts
def execute(
        image_path=None,
        **kwargs
):
    try:
        # 没有图片或者图片不存在则截图
        if not image_path or not os.path.exists(image_path):
            image_path = capture_screen()
        texts = recognize(image_path)
        print("[debug]",texts)
        return {
            "success": True,
            "data": {
                "image": image_path,
                "texts": texts,
            },
            "message": "ocr识别完成"
        }
    except Exception as e:
        print(f"[DEBUG OCR Error] 飞桨执行报错了: {e}")
        return {
            "success": False,
            "error": str(e),
        }