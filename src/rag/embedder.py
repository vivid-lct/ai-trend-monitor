"""
embedder.py - 调用 Ollama /api/embeddings 生成文本向量
模型：nomic-embed-text（需提前 ollama pull nomic-embed-text）
"""
import requests
import logging

logger = logging.getLogger(__name__)

EMBED_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://localhost:11434"


def get_embedding(text: str,
                  model: str = EMBED_MODEL,
                  base_url: str = DEFAULT_BASE_URL) -> list:
    """
    将文本向量化，返回 float 列表。
    失败时返回空列表（调用方需检查）。
    """
    try:
        resp = requests.post(
            f"{base_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("embedding", [])
    except Exception as e:
        logger.warning(f"[Embedder] 向量化失败: {e}")
        return []


def is_embed_model_available(base_url: str = DEFAULT_BASE_URL) -> bool:
    """检查 nomic-embed-text 模型是否已拉取"""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(EMBED_MODEL in m for m in models)
    except Exception:
        return False
