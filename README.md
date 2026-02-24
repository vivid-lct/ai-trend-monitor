# AI 技术趋势监控系统

> 一个面向 AI 应用开发场景的自动化信息采集与分析系统，集成多源数据采集、智能评分过滤、本地大模型分析与 RAG 知识库问答四大核心能力。

**技术栈**：Python · Ollama · ChromaDB · RAG · REST API · HTML/JS

---

## 项目背景

AI 领域信息更新极快，开发者难以持续追踪 LLM 新版本、框架 Breaking Change、前沿论文等关键动态。本项目通过自动化手段，每日从 GitHub、官方博客、Hacker News、arXiv 等多个权威渠道采集 AI 技术资讯，经过去重、分类、评分处理后，生成可视化报告，并支持通过自然语言对历史数据进行问答检索。

---

## 核心功能

### 1. 多源数据采集与处理流水线

从 4 类数据源自动采集 AI 技术动态，经过完整的处理流水线输出高质量数据：

```
采集 → 去重 → 分类 → 过滤 → 评分 → 存储 → 报告/向量库
```

| 数据源 | 采集内容 |
|--------|---------|
| GitHub Releases | LangChain / LlamaIndex / Dify / CrewAI / Ollama / MCP 等主流框架版本发布 |
| RSS 官方博客 | OpenAI / Anthropic / Hugging Face / LangChain 官方技术博客 |
| Hacker News | AI 相关热帖（社区评分 ≥ 50 分筛选） |
| arXiv RSS | cs.AI / cs.LG / cs.CL 最新学术论文 |

### 2. 多维度智能评分系统

每条资讯由四个维度综合评分（0~100 分），自动过滤低质量内容：

| 维度 | 权重 | 评分逻辑 |
|------|------|---------|
| 来源权威性 | 30% | 官方博客 > GitHub Release > arXiv > HN |
| 内容类型 | 25% | LLM 动态 > 框架更新 > 学术论文 > Agent/RAG |
| 社区热度 | 25% | HN 评分 / GitHub Stars 归一化处理 |
| 时效性 | 20% | 24h 内满分，随时间衰减 |

Breaking Change 类内容额外加 15 分并在报告顶部高亮展示。

### 3. RAG 本地知识库问答（Mode 3）

基于 **Ollama + ChromaDB** 构建本地向量知识库，支持对历史采集数据进行自然语言问答：

- 使用 `nomic-embed-text` 模型将资讯内容向量化并持久化存储
- 用户提问 → 向量相似度检索 → 构建上下文 Prompt → `qwen2.5:3b` 生成回答
- 知识库随每次采集（Mode 1）自动增量更新，无需手动维护
- 所有推理在本地完成，数据不出本机

**问答示例**：
```
你的问题：最近 Agent 方向有什么新进展？
你的问题：LangChain 最新版本有哪些 Breaking Change？
```

### 4. 本地大模型深度分析（Mode 4）

调用本地部署的 Ollama（`qwen2.5:3b`）对当期高分资讯进行结构化深度分析，生成趋势分析报告，自动嵌入 HTML 仪表盘展示。支持标准模式与深度模式切换，提示词外置于 `config/prompts/` 可自定义。

### 5. 静态 HTML 可视化报告

无需服务器，数据内嵌 JSON，纯前端渲染，双击即可在浏览器打开：

- Breaking Change 顶部红色高亮
- 按评分排序，低分内容自动灰显
- 分类标签筛选（LLM / Framework / RAG / Agent / Paper）
- 标题关键词实时搜索

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                   action.py（统一入口）            │
│  Mode 1: 采集更新  │  Mode 3: RAG问答             │
│  Mode 2: Coze分析  │  Mode 4: 本地模型分析         │
└──────────┬──────────────────────┬────────────────┘
           │                      │
    ┌──────▼──────┐        ┌──────▼──────┐
    │  数据处理层  │        │   AI 分析层  │
    │  fetchers/  │        │  rag/       │
    │  processors/│        │  local_model│
    │  storage/   │        │  _client.py │
    └──────┬──────┘        └─────────────┘
           │
    ┌──────▼──────┐
    │   输出层     │
    │  exporters/ │  →  report/index.html
    │  rag/       │  →  data/chroma_db/
    └─────────────┘
```

---

## 项目结构

```
ai-trend-monitor/
├── action.py                    # 唯一入口，四种运行模式
├── requirements.txt
├── config/
│   ├── settings.yaml            # 数据源、关键词、评分阈值、模型参数
│   ├── .env.example             # 环境变量模板
│   └── prompts/                 # 外置提示词（可自定义）
│       ├── ai_analyst.md
│       └── ai_analyst_deep.md
└── src/
    ├── fetchers/                # 数据采集层
    │   ├── github_fetcher.py
    │   ├── rss_fetcher.py
    │   ├── hn_fetcher.py
    │   └── pwc_fetcher.py
    ├── processors/              # 数据处理层
    │   ├── deduplicator.py      # URL 去重
    │   ├── classifier.py        # 关键词分类 + Breaking Change 检测
    │   ├── filter.py            # 阈值过滤
    │   └── scorer.py            # 多维度评分
    ├── storage/
    │   └── json_store.py        # 滚动窗口存储 + 月度归档
    ├── exporters/
    │   ├── html_reporter.py     # 静态 HTML 报告生成
    │   └── ai_context_exporter.py
    ├── rag/                     # RAG 知识库模块
    │   ├── embedder.py          # Ollama 向量化
    │   ├── vector_store.py      # ChromaDB 封装
    │   └── rag_client.py        # 检索 + 生成
    ├── local_model_client.py    # Ollama 本地模型客户端
    └── coze_client.py           # Coze API 客户端（开发中）
```

---

## 运行方式

### 环境准备

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置 API Key（可选，不配置也能运行）
cp config/.env.example .env
# 编辑 .env，填入 GITHUB_TOKEN

# 3. 安装 Ollama 并下载模型（Mode 3/4 需要）
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### 运行命令

```bash
python action.py --mode 1   # 采集数据，生成 HTML 报告，更新向量库
python action.py --mode 3   # RAG 自然语言问答
python action.py --mode 4   # 本地大模型趋势分析
python action.py            # 交互式菜单选择
```

---

## 技术要点

- **增量去重**：基于 URL MD5 哈希，跨运行周期去重，避免重复入库
- **冷启动**：首次运行自动采集最近 7 天历史数据
- **数据持久化**：`latest.json` 维护 30 天滚动窗口，`archive/YYYY-MM.json` 月度归档
- **RAG 全本地**：Embedding + 向量检索 + 生成推理均在本机完成，无需调用外部 API
- **提示词外置**：`config/prompts/` 目录下的 Markdown 文件即为提示词，无需改代码即可调整模型行为
- **无服务器报告**：HTML 报告数据内嵌，可直接发送文件离线查看

---

## 开发计划

- [x] 多源数据采集流水线
- [x] 多维度评分与过滤系统
- [x] 静态 HTML 可视化报告
- [x] RAG 本地知识库问答（Ollama + ChromaDB）
- [x] 本地大模型深度分析（Ollama qwen2.5:3b）
- [ ] Coze API 云端分析集成（开发中）
