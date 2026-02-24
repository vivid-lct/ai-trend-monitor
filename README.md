# AI 技术趋势跟踪助手

> 自动采集、过滤、评分 AI 领域最新动态，生成静态 HTML 报告；内置本地 RAG 知识库，支持自然语言问答。

---

## 快速开始

### 1. 安装依赖

推荐使用 conda 环境：

```bash
conda activate try_AI
pip install -r requirements.txt
```

### 2. 配置 GitHub Token（推荐）

编辑根目录下的 `.env` 文件：

```
GITHUB_TOKEN=你的token
```

获取地址：https://github.com/settings/tokens（无需勾选任何权限）

> 不配置也能运行，但 GitHub 采集器会因 rate limit 失败（60次/小时限制）。

### 3. 运行

```bash
python action.py
```

或直接指定模式：

```bash
python action.py --mode 1   # 采集更新（采集 + HTML报告 + ai_context + 向量库）
python action.py --mode 2   # Coze云端分析（调用Coze API高质量趋势分析）
python action.py --mode 3   # RAG本地问答（自然语言提问，向量检索+本地大模型回答）
python action.py --mode 4   # 本地轻量分析（Ollama本地大模型离线兜底）
```

---

## 四种运行模式

| 模式 | 命令 | 说明 | 状态 |
|------|------|------|------|
| **[1] 采集更新** | `--mode 1` | 采集最新 AI 动态，生成 HTML 报告 + 自动导出 ai_context + 向量库入库 | ✅ 可用 |
| **[2] Coze云端分析** | `--mode 2` | 调用 Coze API 云端强模型，完成高质量趋势摘要与深度分析报告 | 🔧 开发中 |
| **[3] RAG本地问答** | `--mode 3` | 自然语言提问，基于历史数据向量检索 + 本地大模型生成回答 | ✅ 可用 |
| **[4] 本地轻量分析** | `--mode 4` | Ollama 本地大模型离线兜底分析（无需联网） | ✅ 可用 |

---

## 查看报告

运行 Mode 1 后，直接双击打开：

```
report/index.html
```

报告功能：
- Breaking Change 顶部高亮展示
- 按评分排序的内容列表（评分 < 30 灰显）
- 分类标签筛选（LLM / Framework / RAG / Agent / Paper 等）
- 标题关键词搜索

---

## 数据源

| 数据源 | 内容 | 需要配置 |
|--------|------|---------|
| GitHub Releases | LangChain/LangGraph/LlamaIndex/Dify/CrewAI/AutoGen/Ollama/MCP | `GITHUB_TOKEN`（推荐） |
| RSS 博客 | OpenAI / Anthropic / LangChain / LlamaIndex / Hugging Face 官方博客 | 无 |
| Hacker News | AI 相关热帖（≥50分） | 无 |
| arXiv RSS | cs.AI + cs.LG + cs.CL 最新论文 | 无 |

---

## 目录结构

```
AI趋势监控/
├── README.md                    ← 本文件
├── action.py                    ← ★ 唯一入口
├── .env                         ← API Key 配置（不提交 git）
├── .gitignore
├── requirements.txt
├── config/
│   ├── settings.yaml            ← 主配置（数据源、关键词、阈值、模型参数）
│   ├── .env.example             ← 环境变量模板
│   └── prompts/                 ← 提示词文件（外置，可自定义）
│       ├── ai_analyst.md        ← 标准分析提示词（Mode 4 默认）
│       ├── ai_analyst_deep.md   ← 深度分析提示词（deep_mode: true 时启用）
│       └── summarizer.md        ← 简洁摘要提示词（备选）
├── src/
│   ├── fetchers/                ← 数据采集模块
│   │   ├── base_fetcher.py      ← Item 数据类 + 基类
│   │   ├── github_fetcher.py    ← GitHub Release 采集
│   │   ├── rss_fetcher.py       ← RSS / 官方博客采集
│   │   ├── hn_fetcher.py        ← Hacker News 采集
│   │   └── pwc_fetcher.py       ← arXiv 论文采集
│   ├── processors/              ← 数据处理模块
│   │   ├── deduplicator.py      ← URL 去重
│   │   ├── classifier.py        ← 关键词分类 + Breaking Change 检测
│   │   ├── filter.py            ← 阈值过滤
│   │   └── scorer.py            ← 综合评分
│   ├── storage/
│   │   └── json_store.py        ← JSON 存储（latest + 月度归档）
│   ├── exporters/
│   │   ├── html_reporter.py     ← 单页 HTML 报告
│   │   └── ai_context_exporter.py ← AI 上下文 Markdown 导出（Mode 1 自动执行）
│   ├── rag/                     ← ★ RAG 知识问答模块（Mode 3）
│   │   ├── embedder.py          ← Ollama nomic-embed-text 向量化
│   │   ├── vector_store.py      ← ChromaDB 封装（建库/入库/检索）
│   │   └── rag_client.py        ← 检索 + Prompt 构建 + Ollama 生成回答
│   ├── coze_client.py           ← Coze API 客户端（Mode 2，开发中）
│   └── local_model_client.py    ← 本地模型客户端（Mode 4，支持 Ollama）
├── data/                        ← 运行时数据（自动创建，不提交 git）
│   ├── latest.json              ← 30天滚动窗口数据
│   ├── last_run.json            ← 上次运行时间
│   ├── ai_context.md            ← AI 分析上下文（Mode 1 自动生成）
│   ├── local_model_report.md    ← 本地模型分析报告（Mode 4 生成）
│   ├── chroma_db/               ← RAG 向量库（Mode 1 自动维护，不提交 git）
│   ├── run.log                  ← 运行日志
│   └── archive/
│       └── YYYY-MM.json         ← 月度归档（追加式，每月一个文件）
└── report/
    ├── index.html               ← ★ 主报告（单页 Tab 布局：趋势列表 + 模型分析）
    └── trends.html              ← 独立趋势排行页
```

---

## 存储策略

| 文件 | 策略 | 说明 |
|------|------|------|
| `data/latest.json` | **滚动合并** | 30天窗口 + URL去重，大小稳定（50~200条） |
| `data/archive/YYYY-MM.json` | **追加式** | 每次新条目追加到当月文件，月底自动新建 |
| `data/ai_context.md` | **覆盖式** | Mode 1 自动导出（所有30天数据），供 AI 工具读取 |
| `data/local_model_report.md` | **覆盖式** | Mode 4 本地模型分析结果，自动集成到 HTML 报告 |

---

## 配置说明

### 修改监控的 GitHub 仓库

编辑 `config/settings.yaml` 的 `sources.github.repos` 节点：

```yaml
sources:
  github:
    repos:
      - owner: langchain-ai
        repo: langchain
        name: LangChain
```

### 修改 RSS 数据源

编辑 `config/settings.yaml` 的 `sources.rss.feeds` 节点：

```yaml
sources:
  rss:
    feeds:
      - url: https://openai.com/blog/rss.xml
        name: OpenAI Blog
        category: llm
```

### 修改关键词分类

编辑 `config/settings.yaml` 的 `keywords` 节点，支持的分类：
`framework` / `llm` / `rag` / `agent` / `workflow` / `breaking_change`

### 修改过滤阈值

```yaml
thresholds:
  hacker_news_min: 50      # HN 最低分数
  cold_start_days: 7       # 冷启动采集天数
```

---

## Mode 2：Coze 云端分析（开发中）

调用 Coze API 云端强模型，完成高质量 AI 趋势摘要与深度分析报告。需配置 `.env`：

```
COZE_API_KEY=your_key
COZE_BOT_ID=your_bot_id
```

> 此功能待 Coze API 配置完成后开放。

---

## Mode 3：RAG 本地问答

基于 Ollama + ChromaDB 构建本地向量知识库，支持对历史 AI 趋势数据进行自然语言问答。

**前提**：
1. 已运行 Mode 1 至少一次（自动建库）
2. 拉取 embedding 模型：

```bash
ollama pull nomic-embed-text
```

**运行**：

```bash
python action.py --mode 3
```

进入交互式问答，示例：
```
你的问题：最近 Agent 方向有什么新进展？
你的问题：LangChain 最新版本有哪些变化？
你的问题：q   ← 退出
```

向量库持久化在 `data/chroma_db/`，每次 Mode 1 采集后自动增量更新，无需手动维护。

---

## Mode 4：本地轻量分析

```bash
python action.py --mode 4
```

前提：安装并运行 [Ollama](https://ollama.com)，下载模型：

```bash
ollama pull qwen2.5:3b
```

分析结果自动保存至 `data/local_model_report.md`。适用于离线或网络不稳定场景。

**深度分析模式**（更详细，耗时更长）：修改 `config/settings.yaml`：

```yaml
local_model:
  deep_mode: true   # 启用后自动使用 ai_analyst_deep.md 提示词
  max_tokens: 3072
```

---

## 评分规则

每条内容的综合评分（0~100）由四个维度决定：

| 维度 | 权重 | 说明 |
|------|------|------|
| 来源权重 | 30 | RSS官博=30, GitHub=25, arXiv=22, HN=18 |
| 内容类型 | 25 | LLM=25, Framework=22, Paper=20, RAG/Agent=18 |
| 社区热度 | 25 | HN分数/Stars归一化 |
| 时效性 | 20 | 24h内=20, 48h内=15, 7天内=10 |

Breaking Change 额外加 15 分。评分 < 30 的内容在 HTML 报告中灰显。

---

## 常见问题

**Q：GitHub 采集器报 403 错误？**  
A：未配置 Token 时每小时只有 60 次请求限制。在 `.env` 中填写 `GITHUB_TOKEN` 即可解决。

**Q：arXiv 论文采集器（pwc_fetcher）为什么不是 Papers With Code？**  
A：Papers With Code API 在国内网络返回 HTML 而非 JSON，已改用 arXiv RSS（cs.AI/cs.LG/cs.CL）替代，内容更丰富且国内可直接访问。

**Q：首次运行很慢？**  
A：首次运行会触发冷启动，采集最近 7 天历史数据，预计耗时 1~3 分钟，属正常现象。

**Q：如何只看某类内容？**  
A：打开 `report/index.html`，点击顶部的分类按钮（LLM / Framework / Paper 等）进行筛选。
