"""
rag_client.py - RAG 问答核心：检索 + Prompt 构建 + Ollama 生成回答
"""
import requests
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGClient:
    """
    RAG 问答客户端。
    流程：用户问题 → 向量检索 top-k → 拼 Prompt → Ollama 生成回答
    """

    def __init__(self,
                 vector_store: "VectorStore",
                 ollama_base_url: str = "http://localhost:11434",
                 model: str = "qwen2.5:3b",
                 top_k: int = 5,
                 max_tokens: int = 1024):
        self._vs = vector_store
        self._base_url = ollama_base_url
        self._model = model
        self._top_k = top_k
        self._max_tokens = max_tokens

    def ask(self, question: str) -> str:
        """
        对用户问题执行 RAG 问答，返回大模型生成的自然语言回答。
        """
        # 1. 检索相关条目
        results = self._vs.search(question, top_k=self._top_k)
        if not results:
            return "未检索到相关内容，请先运行 Mode 1 采集数据并建立向量库。"

        # 2. 构建 RAG Prompt
        context_lines = []
        for i, r in enumerate(results, 1):
            pub = r.get("published_at", "")[:10]
            context_lines.append(
                f"[{i}] [{r.get('category', '')}] {r.get('title', '')}"
                f"（来源：{r.get('source', '')}，时间：{pub}）\n"
                f"    {r.get('content', '')[:500]}"
            )
        context = "\n\n".join(context_lines)

        system_prompt = (
            "你是一个 AI 技术趋势分析助手。"
            "请严格基于以下从知识库检索到的数据回答用户问题，不要编造知识库中没有的内容。"
            "回答用中文，结构清晰，并在引用具体信息时标注来源编号（如[1]）。"
            "如果检索内容与问题无关或信息不足，请如实说明。"
        )
        user_prompt = (
            f"【知识库检索结果】\n{context}\n\n"
            f"【问题】{question}"
        )

        # 3. 调用 Ollama 生成回答
        return self._generate(system_prompt, user_prompt)

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"num_predict": self._max_tokens},
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "（模型未返回内容）").strip()
        except requests.exceptions.ConnectionError:
            return "⚠ 无法连接 Ollama 服务，请确认 Ollama 已启动。"
        except Exception as e:
            logger.error(f"[RAGClient] 生成失败: {e}")
            return f"⚠ 生成回答时出错：{e}"
