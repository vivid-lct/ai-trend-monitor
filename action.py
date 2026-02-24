"""
action.py - AI技术趋势跟踪助手 唯一入口
用法：
  python action.py          # 交互式菜单
  python action.py --mode 1 # 采集更新：采集 + HTML报告 + ai_context导出 + 向量库入库
  python action.py --mode 2 # Coze云端分析：调用Coze API完成高质量趋势摘要与深度分析
  python action.py --mode 3 # RAG本地问答：自然语言提问，基于历史数据检索+本地大模型生成
  python action.py --mode 4 # 本地轻量分析：Ollama本地大模型离线兜底分析
"""
import argparse
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 日志配置：同时输出到控制台和文件
Path("data").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            "data/run.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# 配置加载
# ─────────────────────────────────────────

def load_config() -> dict:
    """加载 settings.yaml + .env，返回合并后的配置字典"""
    load_dotenv()
    cfg_path = Path("config/settings.yaml")
    if not cfg_path.exists():
        print("[错误] 未找到 config/settings.yaml，请确认工作目录正确")
        sys.exit(1)
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["github_token"] = os.getenv("GITHUB_TOKEN", "")
    config.setdefault("coze", {})
    config["coze"]["api_key"] = os.getenv("COZE_API_KEY", "")
    config["coze"]["bot_id"] = os.getenv("COZE_BOT_ID", config["coze"].get("bot_id", ""))
    return config


# ─────────────────────────────────────────
# 采集 + 处理流水线（三种模式共用）
# ─────────────────────────────────────────

def run_pipeline(config: dict, since: Optional[datetime]) -> list:
    """
    采集 → 去重 → 分类 → 过滤 → 评分 → 排序
    :param since: 增量起始时间；None 表示冷启动（采集最近 N 天）
    :return: 已处理、排序的 Item 列表
    """
    from src.fetchers.github_fetcher import GitHubFetcher
    from src.fetchers.rss_fetcher import RSSFetcher
    from src.fetchers.hn_fetcher import HNFetcher
    from src.fetchers.pwc_fetcher import PWCFetcher
    from src.processors.deduplicator import Deduplicator
    from src.processors.classifier import Classifier
    from src.processors.filter import ThresholdFilter
    from src.processors.scorer import Scorer
    from src.storage.json_store import JsonStore

    store = JsonStore(config["output"]["data_dir"])
    existing_urls = store.get_existing_urls()

    # 冷启动：since=None 时采集最近 N 天
    if since is None:
        days = config.get("thresholds", {}).get("cold_start_days", 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. 采集（单个采集器失败不影响整体）
    all_items = []
    fetcher_classes = [GitHubFetcher, RSSFetcher, HNFetcher, PWCFetcher]
    for FetcherClass in fetcher_classes:
        fetcher = FetcherClass(config)
        if not fetcher.is_enabled():
            continue
        try:
            items = fetcher.fetch(since=since)
            print(f"[FETCH] {FetcherClass.__name__}: {len(items)} 条")
            all_items.extend(items)
        except Exception as e:
            logger.warning(f"{FetcherClass.__name__} 采集失败: {e}")

    before_dedup = len(all_items)

    # 2. 去重
    all_items = Deduplicator(existing_urls).deduplicate(all_items)

    # 3. 分类 + Breaking Change 检测
    all_items = Classifier(config.get("keywords", {})).classify(all_items)

    # 4. 阈值过滤
    all_items = ThresholdFilter(config.get("thresholds", {})).filter(all_items)

    # 5. 评分
    all_items = Scorer().score(all_items)

    # 6. 按评分降序排序
    all_items.sort(key=lambda x: x.score, reverse=True)

    bc_count = sum(1 for i in all_items if i.is_breaking_change)
    print(f"[PROCESS] 原始 {before_dedup} 条 → 去重+过滤后 {len(all_items)} 条")
    if bc_count:
        print(f"[BREAKING] 发现 {bc_count} 条 Breaking Change")
    print(f"[DONE] 共 {len(all_items)} 条有效内容")

    return all_items


# ─────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────

def _load_items_from_store(store) -> list:
    """从 latest.json 加载历史条目，转换为 Item 对象列表（用于无新内容时展示）"""
    from src.fetchers.base_fetcher import Item
    raw = store.load_latest()
    items = []
    for d in raw:
        try:
            pub = datetime.fromisoformat(d["published_at"])
            items.append(Item(
                title=d.get("title", ""),
                url=d.get("url", ""),
                source=d.get("source", ""),
                source_type=d.get("source_type", ""),
                category=d.get("category", "other"),
                published_at=pub,
                content=d.get("content", ""),
                score=d.get("score", 0.0),
                is_breaking_change=d.get("is_breaking_change", False),
                tags=d.get("tags", []),
                raw_score=d.get("raw_score", 0),
                extra=d.get("extra", {}),
            ))
        except Exception:
            continue
    return items


def _index_items_to_rag(items: list, data_dir: str) -> None:
    """将新条目增量写入 ChromaDB 向量库（Mode 1 自动调用）"""
    try:
        from src.rag.vector_store import VectorStore
        chroma_dir = str(Path(data_dir) / "chroma_db")
        vs = VectorStore(persist_dir=chroma_dir)
        added = vs.add_items(items)
        print(f"[RAG] 向量库已更新，新增 {added} 条记录（共 {vs.count()} 条）")
    except ImportError:
        pass  # chromadb 未安装时静默跳过
    except Exception as e:
        logger.warning(f"RAG 入库失败（不影响主流程）: {e}")


# ─────────────────────────────────────────
# 四种运行模式
# ─────────────────────────────────────────

def run_mode_1(config: dict):
    """Mode 1：采集更新 — 采集 + HTML报告 + ai_context导出 + 向量库增量入库"""
    from src.storage.json_store import JsonStore
    from src.exporters.html_reporter import HTMLReporter
    from src.exporters.ai_context_exporter import AIContextExporter

    store = JsonStore(config["output"]["data_dir"])
    is_cold = store.is_cold_start()
    since = None if is_cold else store.get_last_run_time()

    if is_cold:
        days = config.get("thresholds", {}).get("cold_start_days", 7)
        print(f"\n[首次运行] 未检测到历史数据，将采集最近 {days} 天内容作为基线...")
        print("预计耗时 1~3 分钟，请稍候...\n")

    new_items = run_pipeline(config, since)
    store.update_last_run_time()
    new_count = len(new_items)

    if new_items:
        store.save(new_items)
        print(f"\n[存储] 已保存 {new_count} 条新内容")
    else:
        print("\n[提示] 本次无新内容，HTML 报告将展示历史数据")

    display_items = _load_items_from_store(store)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_dir = config["output"]["data_dir"]

    # 自动导出 ai_context.md（无感知，合并原 Mode 2 功能）
    ai_context_file = config["output"].get("ai_context_filename", "ai_context.md")
    AIContextExporter(f"{data_dir}/{ai_context_file}").export(display_items, now_str)
    print(f"[导出] ai_context.md 已更新")

    # 自动追加向量库（新条目增量入库）
    if new_items:
        _index_items_to_rag(new_items, data_dir)

    report_path = HTMLReporter(
        f"{config['output']['report_dir']}/{config['output']['report_filename']}",
        data_dir=data_dir,
    ).generate(display_items, now_str, new_count=new_count)

    print(f"\n✅ 完成！请打开报告查看：{report_path}")
    print(f"   （直接双击文件，或在浏览器中打开）")


def run_mode_2(config: dict):
    """Mode 2：Coze云端分析 — 调用Coze API完成高质量趋势摘要与深度分析报告"""
    from src.coze_client import CozeClient
    from src.storage.json_store import JsonStore

    # 读取 Coze 配置
    api_key = os.getenv("COZE_API_KEY", "")
    bot_id  = os.getenv("COZE_BOT_ID", "")

    if not api_key or not bot_id:
        print("\n⚠ 未配置 COZE_API_KEY 或 COZE_BOT_ID，请在 .env 文件中填写：")
        print("  COZE_API_KEY=your_key")
        print("  COZE_BOT_ID=your_bot_id")
        return

    # 读取本地数据
    from src.fetchers.base_fetcher import Item
    from dateutil.parser import parse as parse_dt

    data_dir = config["output"]["data_dir"]
    store = JsonStore(data_dir=data_dir)
    raw_items = store.load_latest()

    if not raw_items:
        print("\n⚠ 本地数据为空，请先运行 Mode 1 采集数据。")
        return

    items = []
    for d in raw_items:
        try:
            items.append(Item(
                title=d.get("title", ""),
                url=d.get("url", ""),
                source=d.get("source", ""),
                source_type=d.get("source_type", ""),
                category=d.get("category", "other"),
                published_at=parse_dt(d["published_at"]),
                content=d.get("content", ""),
                score=float(d.get("score", 0)),
                is_breaking_change=d.get("is_breaking_change", False),
                tags=d.get("tags", []),
                raw_score=d.get("raw_score", 0),
                extra=d.get("extra", {}),
            ))
        except Exception:
            continue

    print(f"\n[Mode 2] 共 {len(items)} 条数据，正在调用 Coze 云端分析...")

    client = CozeClient(api_key=api_key, bot_id=bot_id)
    result = client.send(items)

    if result["status"] == "ok":
        # 保存报告
        report_path = Path(data_dir) / "coze_report.md"
        from datetime import datetime as _dt
        header = f"# Coze AI 趋势分析报告\n\n> 生成时间：{_dt.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
        report_path.write_text(header + result["reply"], encoding="utf-8")
        token_info = f"（消耗 {result.get('token_count', 0)} tokens）"
        print(f"\n✅ 分析完成 {token_info}")
        print(f"报告已保存至：{report_path}")
    else:
        print(f"\n❌ 调用失败：{result.get('error', '未知错误')}")


def run_mode_3(config: dict):
    """Mode 3：RAG本地问答 — 自然语言提问，基于历史数据向量检索+本地大模型生成回答"""
    import requests as _req
    from src.rag.vector_store import VectorStore
    from src.rag.rag_client import RAGClient

    data_dir = config["output"]["data_dir"]
    chroma_dir = str(Path(data_dir) / "chroma_db")

    # 检查向量库是否已建立
    vs = VectorStore(persist_dir=chroma_dir)
    count = vs.count()
    if count == 0:
        print("\n⚠ 向量库为空，请先运行 Mode 1 采集数据（会自动建库）")
        return
    print(f"\n[RAG] 向量库已就绪，共 {count} 条记录")

    # 检查 Ollama 是否可用
    lm_cfg = config.get("local_model", {})
    ollama_base = lm_cfg.get("api_base", "http://localhost:11434")
    try:
        if _req.get(f"{ollama_base}/api/tags", timeout=3).status_code != 200:
            raise ConnectionError
    except Exception:
        print("\n⚠ Ollama 服务未运行，请先启动 Ollama")
        return

    rag = RAGClient(
        vector_store=vs,
        ollama_base_url=lm_cfg.get("api_base", "http://localhost:11434"),
        model=lm_cfg.get("model", "qwen2.5:3b"),
    )

    print("\n[RAG] 进入知识问答模式（输入 'q' 或 'exit' 退出）")
    print("-" * 52)
    while True:
        try:
            question = input("\n你的问题：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("q", "exit", "quit", ""):
            break
        print("\n[RAG] 检索中...")
        answer = rag.ask(question)
        print(f"\n回答：\n{answer}")
        print("-" * 52)
    print("\n[RAG] 已退出问答模式")


def run_mode_4(config: dict):
    """Mode 4：本地轻量分析 — Ollama本地大模型离线兜底分析"""
    from src.local_model_client import LocalModelClient
    from src.storage.json_store import JsonStore
    from src.exporters.html_reporter import HTMLReporter

    lm_cfg = config.get("local_model", {})
    deep = lm_cfg.get("deep_mode", False)
    prompt_file = "ai_analyst_deep.md" if deep else lm_cfg.get("prompt_file", "ai_analyst.md")
    if deep:
        print("🔬 深度分析模式已启用（使用详细提示词，耗时较长）")
    client = LocalModelClient(
        base_url=lm_cfg.get("api_base", "http://localhost:11434"),
        model=lm_cfg.get("model", "qwen2.5:3b"),
        max_tokens=lm_cfg.get("max_tokens", 2048),
        top_n=lm_cfg.get("top_n_items", 20),
        prompt_file=prompt_file,
    )

    if not client.is_available():
        print("\n⚠ Ollama 服务未运行，请先启动 Ollama（系统托盘应有图标）")
        return

    store = JsonStore(config["output"]["data_dir"])
    items = _load_items_from_store(store)
    if not items:
        print("\n⚠ 暂无历史数据，请先运行 Mode 1 采集数据")
        return

    print(f"\n[本地模型] 使用模型：{client.model}")
    print(f"[本地模型] 分析最高分前 {client.top_n} 条数据，请稍候...")
    print("（qwen2.5:3b 约需 30~60 秒）\n")

    result = client.analyze(items)

    if result["status"] == "error":
        print(result["report"])
        return

    report = result["report"]
    print("\n" + "=" * 60)
    print(f"  本地大模型分析报告（{result['model']}，共 {result['item_count']} 条数据）")
    print("=" * 60)
    print(report)

    output_path = Path(config["output"]["data_dir"]) / "local_model_report.md"
    output_path.write_text(
        f"# AI 趋势本地模型分析报告\n"
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}  "
        f"模型：{result['model']}  分析条目：{result['item_count']} 条\n\n"
        + report,
        encoding="utf-8"
    )
    print(f"\n✅ 报告已保存：{output_path}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_path = HTMLReporter(
        f"{config['output']['report_dir']}/{config['output']['report_filename']}",
        data_dir=config['output']['data_dir'],
    ).generate(items, now_str)
    print(f"✅ HTML 报告已更新：{html_path}")


def show_menu() -> str:
    print("\n" + "=" * 58)
    print("  AI 技术趋势跟踪助手")
    print("=" * 58)
    print("  [1] 采集更新       — 采集 + HTML报告 + ai_context + 向量库")
    print("  [2] Coze云端分析   — Coze API 高质量趋势摘要（开发中）")
    print("  [3] RAG本地问答    — 自然语言提问，向量检索+本地大模型回答")
    print("  [4] 本地轻量分析   — Ollama 本地大模型离线兜底分析")
    print("  [0] 退出")
    print("-" * 58)
    return input("请输入选项：").strip()


def main():
    parser = argparse.ArgumentParser(description="AI技术趋势跟踪助手")
    parser.add_argument(
        "--mode", type=str, choices=["1", "2", "3", "4"],
        help="直接指定运行模式（1/2/3/4），跳过交互菜单"
    )
    args = parser.parse_args()
    mode = args.mode

    if mode is None:
        mode = show_menu()

    config = load_config()

    if mode == "1":
        run_mode_1(config)
    elif mode == "2":
        run_mode_2(config)
    elif mode == "3":
        run_mode_3(config)
    elif mode == "4":
        run_mode_4(config)
    elif mode == "0":
        print("退出。")
        sys.exit(0)
    else:
        print(f"无效选项：{mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
