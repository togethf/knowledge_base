# -*- coding: utf-8 -*-
"""
Configuration for the Pest Comparison Tool
"""
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# GLM-4V API Configuration (Baseline VLM - supports image input)
GLM_API_KEY = "e7f32a5254ed42a39330bbf6b90cabef.dnHExsP3uXRVUVbF"
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-4.6v"

# YOLO Model Configuration
YOLO_MODEL_PATH = os.path.join(BASE_DIR, "..", "..", "pest.pt")

# YOLO Class Names Mapping (English -> Chinese -> Knowledge Base ID)
YOLO_CLASS_NAMES = {
    0: {"en": "DaoZhong", "zh": "稻纵卷叶螟", "kb_id": "pest.cnaphalocrocis_medinalis"},
    1: {"en": "ErHua", "zh": "二化螟", "kb_id": "pest.chilo_suppressalis"},
    2: {"en": "DaMingShen", "zh": "大螟", "kb_id": "pest.sesamia_inferens"},
    3: {"en": "HeiBai", "zh": "黑白蚁", "kb_id": "pest.odontotermes"},
    4: {"en": "DaoMingLing", "zh": "稻蓟马", "kb_id": "pest.stenchaetothrips_biformis"},
    5: {"en": "YuMiMing", "zh": "玉米螟", "kb_id": "pest.ostrinia_furnacalis"},
    6: {"en": "YangXue", "zh": "蚜虫", "kb_id": "pest.aphid"},
    7: {"en": "LouGu", "zh": "蝼蛄", "kb_id": "pest.gryllotalpa"},
    8: {"en": "JinGui", "zh": "金龟子", "kb_id": "pest.scarabaeidae"},
}

# Neo4j Configuration
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "Neo4j!12345")

# Upload Configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
