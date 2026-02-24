# AI 技术趋势监控系统

> 独立设计并实现的 AI 技术资讯自动采集与分析系统。整合 GitHub / 官方博客 / Hacker News / arXiv 四类数据源，经多维度评分过滤后生成可交互 HTML 报告；内置 RAG 本地知识库支持自然语言检索，并支持 Coze 云端大模型与 Ollama 本地大模型双路径智能分析。

**技术栈**：Python · Ollama · ChromaDB · RAG · Coze API · cozepy · arXiv RSS · HTML/JS

---

## 项目亮点

| 亮点 | 说明 |
|------|------|
| **完整工程化** | 模块化分层架构（fetchers / processors / storage / exporters / rag），单一入口 `action.py` 管理四种运行模式 |
| **多维评分算法** | 自研 4 维评分体系（来源权威性 30% · 内容类型 25% · 社区热度 25% · 时效性 20%），Breaking Change 自动识别并额外加权 |
| **云端+本地双模型** | Coze 智能体平台（联网搜索 + 结构化 Prompt）与 Ollama 本地模型（qwen2.5:3b）灵活切换，兼顾质量与成本 |
| **全本地 RAG** | Embedding + 向量检索 + 生成推理均在本机完成，基于 URL MD5 增量去重入库，数据不出本机 |
| **零依赖报告** | 静态 HTML 内嵌数据，双击浏览器即开，Breaking Change 顶部高亮，支持分类筛选与实时搜索 |

---

## 核心功能

### Mode 1 · 采集更新

从 4 类数据源自动采集 AI 技术动态，经完整处理流水线后生成可视化报告并更新知识库：

```
采集[1/4] → 去重 → 分类 → 过滤 → 评分 → 存储 → HTML 报告 + 向量库
```

| 数据源 | 采集内容 |
|--------|---------|
| **GitHub Releases** | LangChain / LlamaIndex / Dify / CrewAI / Ollama / MCP 等主流框架版本发布 |
| **RSS 官方博客** | OpenAI / Anthropic / Hugging Face / LangChain 官方技术博客 |
| **Hacker News** | AI 相关热帖（社区评分 ≥ 50 过滤 + 关键词匹配双重筛选） |
| **arXiv RSS** | cs.AI / cs.LG / cs.CL 最新学术论文（三类 feed 均衡采样） |

**评分维度**（0~100 分，Breaking Change 额外 +15）：

| 维度 | 权重 | 逻辑 |
|------|------|------|
| 来源权威性 | 30% | 官方 RSS > GitHub Release > arXiv > HN |
| 内容类型 | 25% | LLM 动态 > 框架更新 > 学术论文 |
| 社区热度 | 25% | HN 评分 / GitHub Stars 归一化到 0~25 |
| 时效性 | 20% | 24h 内满分，随时间衰减到最低 2 分 |

---

### Mode 2 · Coze 云端分析

调用 **Coze 智能体平台**（cozepy SDK 流式接口），将高分资讯发送给云端大模型进行深度分析：

- 优先取综合评分 ≥ 60 分的前 20 条数据发送
- Coze Bot 配置联网搜索插件，自动补全关键动态背景信息
- 结构化 Prompt 约束输出格式：分类标签 · Breaking Change 预警 · 开发者影响分析
- 流式打字机效果实时展示，分析结果保存至 `data/coze_report.md`

---

### Mode 3 · RAG 本地知识库问答

基于 **Ollama + ChromaDB** 构建全本地向量知识库，对历史采集数据进行自然语言问答：

- `nomic-embed-text` 向量化 → ChromaDB cosine 相似度检索 → `qwen2.5:3b` 生成回答
- 知识库随 Mode 1 采集自动增量更新，URL MD5 防重复
- 所有推理在本机完成，数据不出本地

```
你的问题：最近 Agent 方向有什么新进展？
你的问题：LangChain 最近有哪些 Breaking Change？
```

---

### Mode 4 · 本地大模型分析

调用本地 Ollama（`qwen2.5:3b`）对高分资讯进行结构化深度分析，报告自动嵌入 HTML 仪表盘：

- 支持标准模式与深度模式切换（`deep_mode: true`）
- 提示词外置于 `config/prompts/`，无需改代码即可调整分析风格

---

## 系统架构

```
┌──────────────────────────────────────────────────┐
│              action.py  （统一交互入口）            │
│  Mode 1: 采集+报告  │  Mode 2: Coze 云端分析       │
│  Mode 3: RAG 问答   │  Mode 4: 本地模型分析         │
└────────┬─────────────────────┬────────────────────┘
         │                     │
  ┌──────▼──────┐       ┌──────▼──────┐
  │  数据处理层  │       │   AI 分析层  │
  │  fetchers/  │       │  coze_client│
  │  processors/│       │  local_model│
  │  storage/   │       │  rag/       │
  └──────┬──────┘       └─────────────┘
         │
  ┌──────▼──────┐
  │   输出层     │
  │  exporters/ │ → report/index.html · trends.html
  │  data/      │ → latest.json · archive/ · chroma_db/
  └─────────────┘
```

---

## 项目结构

```
ai-trend-monitor/
├── action.py                    # 唯一入口，四种运行模式 + 交互菜单
├── requirements.txt
├── config/
│   ├── settings.yaml            # 数据源、关键词、评分阈值、模型参数
│   ├── .env.example             # 环境变量模板（GITHUB_TOKEN / COZE_API_KEY）
│   └── prompts/                 # 外置提示词（可自定义，无需改代码）
│       ├── ai_analyst.md        # 标准分析提示词
│       └── ai_analyst_deep.md   # 深度分析提示词
└── src/
    ├── fetchers/                # 数据采集层（各采集器独立，单个失败不影响整体）
    │   ├── base_fetcher.py      # Item 数据类 + 采集器基类
    │   ├── github_fetcher.py    # GitHub Releases 采集
    │   ├── rss_fetcher.py       # RSS/博客采集
    │   ├── hn_fetcher.py        # Hacker News 热帖采集
    │   └── pwc_fetcher.py       # arXiv RSS 论文采集
    ├── processors/              # 数据处理层
    │   ├── deduplicator.py      # URL 标准化 + 跨周期去重
    │   ├── classifier.py        # 关键词分类 + Breaking Change 检测
    │   ├── filter.py            # 多规则阈值过滤
    │   └── scorer.py            # 四维综合评分
    ├── storage/
    │   └── json_store.py        # 30天滚动窗口 latest.json + 月度归档
    ├── exporters/
    │   ├── html_reporter.py     # 双页静态 HTML 报告（仪表盘 + 趋势排行）
    │   └── ai_context_exporter.py  # ai_context.md 导出
    ├── rag/                     # 全本地 RAG 模块
    │   ├── embedder.py          # nomic-embed-text 向量化
    │   ├── vector_store.py      # ChromaDB 封装（cosine 相似度）
    │   └── rag_client.py        # 检索 + Prompt 构建 + 生成
    ├── local_model_client.py    # Ollama OpenAI 兼容接口客户端
    └── coze_client.py           # Coze API 客户端（cozepy 流式响应）
```

---

## 快速开始

### 环境准备

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置密钥（可选，不配置仍可运行 Mode 1/3/4）
cp config/.env.example .env
# 填入 GITHUB_TOKEN（提升 API 限速）
# 填入 COZE_API_KEY + COZE_BOT_ID（Mode 2 需要）

# 3. 安装 Ollama 并拉取模型（Mode 3/4 需要）
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### 运行

```bash
python action.py            # 交互式菜单（推荐）
python action.py --mode 1   # 采集 + HTML 报告 + 更新向量库
python action.py --mode 2   # Coze 云端大模型分析
python action.py --mode 3   # RAG 自然语言问答
python action.py --mode 4   # 本地大模型趋势分析
```

---

## 工程实践

- **增量去重**：URL 标准化（统一 https、去尾斜杠、小写）后 MD5 哈希，跨运行周期精确去重
- **冷启动保护**：首次运行自动采集最近 7 天历史数据，不依赖上次运行记录
- **容错设计**：单个采集器失败不影响整体流程，异常写入 `data/run.log` 而不打断控制台输出
- **数据归档**：`latest.json` 维护 30 天滚动窗口；`archive/YYYY-MM.json` 按月归档，避免单文件膨胀
- **提示词工程**：系统 Prompt 外置 Markdown 文件，支持标准/深度双模式，无需改代码调整模型行为
- **零依赖报告**：HTML 数据内嵌 JSON，纯前端渲染，可离线查看或直接发送给他人

---

## 已实现功能

- [x] 多源数据采集流水线（GitHub / RSS / HN / arXiv）
- [x] 四维度评分 + Breaking Change 自动识别
- [x] 静态 HTML 双页可视化报告（仪表盘 + 趋势排行）
- [x] 全本地 RAG 知识库问答（Ollama + ChromaDB）
- [x] 本地大模型深度分析（Ollama qwen2.5:3b）
- [x] Coze 智能体云端分析（cozepy 流式接口）
