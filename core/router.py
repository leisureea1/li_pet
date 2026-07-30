import os
import json
import math
import requests
import zipfile
import tempfile
import numpy as np
from pathlib import Path

class SemanticRouter:
    def __init__(self, data_dir):
        # 优先使用项目内置的 models 目录（支持 PyInstaller 打包环境）
        import sys
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        builtin_models_dir = os.path.join(base_dir, "models")
        self.model_name = "bge-small-zh-v1.5"
        
        if os.path.exists(builtin_models_dir):
            self.models_dir = builtin_models_dir
        else:
            # 回退到 AppData 目录
            self.models_dir = os.path.join(data_dir, "models")
            
        self.model_path = os.path.join(self.models_dir, self.model_name)
        
        self.tokenizer = None
        self.session = None
        self.ready = False
        
        # 定义各类锚点文本
        self.anchors = {
            "weather": [
                "今天天气怎么样", "北京气温多少", "会下雨吗", "需要带伞吗", "穿什么衣服合适", "今天冷不冷", "外面热吗"
            ],
            "search": [
                "帮我搜一下", "什么是量子力学", "查一下最近的新闻", "2026年油价调整", "周杰伦是谁", "能搜索下吗", "网上搜一下"
            ],
            "chat": [
                "你好呀", "你在干嘛", "摸摸头", "最近有点累", "我今天吃火锅了", "累累", "想你了", "哈哈"
            ],
            "app_usage":[
                "我今天用了多久电脑", "帮我看看今天各个软件使用时间", "当前打开的是什么软件", "查一下屏幕使用时间", "今天电脑玩了多久"
            ],
            "ocr":[
                "帮我看看屏幕上写了什么", "截图识别一下屏幕", "帮我看看这个报错信息",
                "读取一下屏幕内容", "屏幕上有什么文字"
            ]
        }
        self.anchor_embeddings = {}
        
    def init_model(self):
        if self.ready:
            return True
            
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as e:
            print(f"[SemanticRouter] Missing onnxruntime or tokenizers. Cannot use router. Error: {e}")
            return False

        if not os.path.exists(os.path.join(self.model_path, "model_quantized.onnx")) or not os.path.exists(os.path.join(self.model_path, "tokenizer.json")):
            print("[SemanticRouter] Model not found, downloading...")
            self.download_model()
            
        try:
            self.tokenizer = Tokenizer.from_file(os.path.join(self.model_path, "tokenizer.json"))
            self.tokenizer.enable_truncation(max_length=512)
            self.session = ort.InferenceSession(os.path.join(self.model_path, "model_quantized.onnx"), providers=['CPUExecutionProvider'])
            
            # 预计算所有锚点的 Embedding
            for category, texts in self.anchors.items():
                self.anchor_embeddings[category] = [self.get_embedding(text) for text in texts]
                
            self.ready = True
            print("[SemanticRouter] Initialized successfully.")
            return True
        except Exception as e:
            print(f"[SemanticRouter] Initialization failed: {e}")
            return False

    def download_model(self):
        os.makedirs(self.model_path, exist_ok=True)
        files = ["model_quantized.onnx", "tokenizer.json", "config.json"]
        base_url = f"https://hf-mirror.com/Xenova/{self.model_name}/resolve/main/onnx/"
        base_url_root = f"https://hf-mirror.com/Xenova/{self.model_name}/resolve/main/"
        
        for file in files:
            url = base_url + file if file.endswith(".onnx") else base_url_root + file
            target_path = os.path.join(self.model_path, file)
            print(f"Downloading {file} from {url}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

    def mean_pooling(self, token_embeddings, attention_mask):
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        return sum_embeddings / sum_mask

    def get_embedding(self, text):
        encoded = self.tokenizer.encode(text)
        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
        token_type_ids = np.array([encoded.type_ids], dtype=np.int64)
        
        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids
        }
        outputs = self.session.run(None, inputs)
        token_embeddings = outputs[0]
        sentence_embedding = self.mean_pooling(token_embeddings, attention_mask)
        # Normalize
        norm = np.linalg.norm(sentence_embedding, axis=1, keepdims=True)
        sentence_embedding = sentence_embedding / norm
        return sentence_embedding[0]

    def cosine_similarity(self, v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    def get_intent(self, user_input, threshold=0.55):
        if not self.ready and not self.init_model():
            return None
            
        try:
            query_emb = self.get_embedding(user_input)
            
            best_category = None
            best_score = -1
            
            for category, embeddings in self.anchor_embeddings.items():
                scores = [self.cosine_similarity(query_emb, anchor) for anchor in embeddings]
                max_score = max(scores)
                if max_score > best_score:
                    best_score = max_score
                    best_category = category
                    
            print(f"[SemanticRouter] '{user_input}' -> {best_category} (score: {best_score:.3f})")
            if best_score >= threshold:
                return best_category
            return None
        except Exception as e:
            print(f"[SemanticRouter] Error routing: {e}")
            return None
