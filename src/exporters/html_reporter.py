"""
html_reporter.py - 静态 HTML 报告生成器（重设计版）
生成两个页面：
  report/index.html   — 数据仪表盘（概览、图表、Top10、模型报告）
  report/trends.html  — AI 趋势排行（完整列表、分类筛选、搜索）
双击浏览器直接打开，无需服务器
"""
import json
from collections import Counter
from pathlib import Path
from typing import List, Optional

from src.fetchers.base_fetcher import Item

CAT_LABEL = {
    "llm": "大模型", "framework": "框架", "rag": "RAG",
    "agent": "Agent", "paper": "论文", "workflow": "工作流", "other": "其他",
}
CAT_COLOR = {
    "llm": "#60a5fa", "framework": "#34d399", "rag": "#a78bfa",
    "agent": "#fbbf24", "paper": "#818cf8", "workflow": "#f472b6", "other": "#94a3b8",
}
SRC_LABEL = {"rss": "RSS 博客", "github": "GitHub", "hn": "Hacker News", "pwc": "arXiv"}
SRC_COLOR = {"rss": "#60a5fa", "github": "#94a3b8", "hn": "#fb923c", "pwc": "#34d399"}


class HTMLReporter:
    """静态 HTML 报告生成器（仪表盘 + 趋势排行）"""

    def __init__(self, output_path: str = "report/index.html", data_dir: str = "data"):
        self.output_path = Path(output_path)
        self.data_dir = Path(data_dir)
        self.trends_path = self.output_path.parent / "trends.html"

    def generate(self, items: List[Item], generated_at: str = "", new_count: int = 0) -> str:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        s = self._stats(items, new_count)
        model = self._model_report()
        items_json = json.dumps(
            [self._to_dict(i) for i in items], ensure_ascii=False, default=str
        )
        self.output_path.write_text(self._dashboard(s, model, generated_at, items_json), encoding="utf-8")
        self.trends_path.write_text(self._trends(items_json, generated_at, s), encoding="utf-8")
        return str(self.output_path)

    # ── 内部辅助 ──────────────────────────────────────────────────────────

    def _to_dict(self, item: Item) -> dict:
        return {
            "title": item.title, "url": item.url,
            "source": item.source, "source_type": item.source_type,
            "category": item.category,
            "published_at": item.published_at.strftime("%Y-%m-%d %H:%M"),
            "content": item.content, "score": item.score,
            "is_breaking": item.is_breaking_change, "tags": item.tags,
        }

    def _stats(self, items: List[Item], new_count: int) -> dict:
        dates = [i.published_at for i in items]
        top = sorted(items, key=lambda x: x.score, reverse=True)
        buckets = [0] * 5
        for i in items:
            buckets[min(4, int(i.score / 20))] += 1
        by_cat = dict(Counter(i.category for i in items))
        by_src = dict(Counter(i.source_type for i in items))
        return {
            "total": len(items), "new": new_count,
            "breaking": sum(1 for i in items if i.is_breaking_change),
            "date_from": min(dates).strftime("%Y-%m-%d") if dates else "-",
            "date_to": max(dates).strftime("%Y-%m-%d") if dates else "-",
            "by_cat": by_cat, "by_src": by_src, "buckets": buckets,
            "top10": top[:10],
            "breaking_items": [i for i in top if i.is_breaking_change],
        }

    def _model_report(self) -> Optional[dict]:
        p = self.data_dir / "local_model_report.md"
        if not p.exists():
            return None
        try:
            lines = p.read_text(encoding="utf-8").strip().split("\n")
            meta = next((l.lstrip("> ").strip() for l in lines[:5] if l.startswith(">")), "")
            body = "\n".join(lines[3:]).strip()
            return {"meta": meta, "body": body}
        except Exception:
            return None

    # ─── 仪表盘 index.html ─────────────────────────────────────────────────

    @staticmethod
    def _md_to_html(text: str) -> str:
        import re, html as _hl
        out, in_ul = [], False
        for raw in text.split('\n'):
            safe = _hl.escape(raw)
            safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
            safe = re.sub(r'\*(.+?)\*', r'<em>\1</em>', safe)
            safe = re.sub(r'`(.+?)`', r'<code class="ic">\1</code>', safe)
            stripped = raw.strip()
            if stripped.startswith('### ') or stripped.startswith('## ') or stripped.startswith('# '):
                if in_ul: out.append('</ul>'); in_ul = False
                level = 'mh3' if stripped.startswith('### ') else ('mh2' if stripped.startswith('## ') else 'mh1')
                out.append(f'<p class="{level}">{safe.lstrip().lstrip("#").lstrip()}</p>')
            elif re.match(r'^[-*]\s', stripped):
                if not in_ul: out.append('<ul class="mul">'); in_ul = True
                li_text = re.sub(r'^[-*]\s+', '', safe.lstrip())
                out.append(f'<li>{li_text}</li>')
            elif not stripped:
                if in_ul: out.append('</ul>'); in_ul = False
            else:
                if in_ul: out.append('</ul>'); in_ul = False
                out.append(f'<p class="mp">{safe}</p>')
        if in_ul: out.append('</ul>')
        return '\n'.join(out)

    def _dashboard(self, s: dict, model: Optional[dict], generated_at: str, items_json: str) -> str:
        cat_labels = list(CAT_LABEL.values())
        cat_data   = [s["by_cat"].get(k, 0) for k in CAT_LABEL]
        cat_colors = list(CAT_COLOR.values())
        src_labels = [SRC_LABEL.get(k, k) for k in s["by_src"]]
        src_data   = list(s["by_src"].values())
        src_colors = [SRC_COLOR.get(k, "#94a3b8") for k in s["by_src"]]
        bc_html = ""
        if s["breaking_items"]:
            rows = "".join(
                f'<a class="bc-row" href="{i.url}" target="_blank">'
                f'<span>⚡ {i.title[:90]}</span>'
                f'<span class="bc-src">{i.source}</span></a>'
                for i in s["breaking_items"]
            )
            bc_html = (f'<div class="card" style="border-left:3px solid var(--red);margin-bottom:18px">'
                       f'<div class="st" style="color:var(--red);margin-bottom:10px">⚠ Breaking Changes（{s["breaking"]}）</div>'
                       f'{rows}</div>')
        src_str = " · ".join(SRC_LABEL.get(k, k) for k in s["by_src"])
        new_val = s["new"] if s["new"] else "—"
        if model:
            model_html = (f'<div class="model-meta">{model["meta"]}</div>'
                          f'<div class="model-content">{self._md_to_html(model["body"])}</div>')
        else:
            model_html = '<p class="model-empty">暂无报告 — 运行 <code>python action.py --mode 4</code> 生成</p>'
        cat_list_html = "".join(
            f'<div class="cd"><span class="cddot" style="background:{CAT_COLOR.get(k, "#94a3b8")}"></span>'
            f'<span class="cdl">{CAT_LABEL.get(k, k)}</span><span class="cdv">{s["by_cat"].get(k, 0)}</span></div>'
            for k in CAT_LABEL if s["by_cat"].get(k, 0) > 0
        )
        src_list_html = "".join(
            f'<div class="cd"><span class="cddot" style="background:{SRC_COLOR.get(k, "#94a3b8")}"></span>'
            f'<span class="cdl">{SRC_LABEL.get(k, k)}</span><span class="cdv">{cnt}</span></div>'
            for k, cnt in sorted(s["by_src"].items(), key=lambda x: -x[1])
        )
        _parts = ['<button class="fb act" data-cat="all" onclick="fc(\'all\',this)">全部 <em>'
                  + str(s["total"]) + '</em></button>']
        for _k in CAT_LABEL:
            if s["by_cat"].get(_k, 0) > 0:
                _cc, _lbl, _cnt = CAT_COLOR.get(_k, "#888"), CAT_LABEL.get(_k, _k), s["by_cat"][_k]
                _parts.append(
                    f'<button class="fb" data-cat="{_k}" onclick="fc(\'{_k}\',this)" style="--c:{_cc}">'
                    f'{_lbl} <em>{_cnt}</em></button>'
                )
        cat_btns = "".join(_parts)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 趋势监控</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{--bg:#0f172a;--s1:#1e293b;--s2:#334155;--bd:rgba(148,163,184,.12);
  --acc:#38bdf8;--grn:#4ade80;--amb:#fbbf24;--red:#f87171;
  --tx:#f1f5f9;--muted:#94a3b8;--r:10px}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}}
a{{color:inherit;text-decoration:none}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:14px 28px;gap:12px;
  border-bottom:1px solid var(--bd);border-top:2px solid var(--acc);
  position:sticky;top:0;z-index:100;
  background:rgba(15,23,42,.92);backdrop-filter:blur(12px)}}
.brand{{font-size:.97rem;font-weight:700;display:flex;align-items:center;gap:8px;flex-shrink:0}}
.brand span{{background:linear-gradient(90deg,#38bdf8,#818cf8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.nav-r{{font-size:.72rem;color:var(--muted);text-align:right}}
main{{max-width:1180px;margin:0 auto;padding:22px 18px}}
.sg{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}}
@media(max-width:680px){{.sg{{grid-template-columns:repeat(2,1fr)}}}}
.sc{{background:linear-gradient(135deg,#1e293b 0%,#1a2744 100%);border:1px solid var(--bd);border-radius:var(--r);padding:16px}}
.sc .l{{font-size:.67rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px}}
.sc .v{{font-size:1.8rem;font-weight:700;line-height:1}}
.sc .s{{font-size:.69rem;color:var(--muted);margin-top:4px}}
.cg{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}}
@media(max-width:680px){{.cg{{grid-template-columns:1fr}}}}
.card{{background:var(--s1);border:1px solid var(--bd);border-radius:var(--r);padding:18px;margin-bottom:14px}}
.st{{font-size:.8rem;font-weight:600;margin-bottom:11px}}
.cw{{height:180px;position:relative}}
.bc-row{{display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:8px 0;border-bottom:1px solid var(--bd);font-size:.82rem}}
.bc-row:last-child{{border-bottom:none}}
.bc-row:hover>span:first-child{{color:var(--red)}}
.bc-src{{font-size:.69rem;color:var(--muted);flex-shrink:0}}
.tabs{{background:var(--s1);border:1px solid var(--bd);border-radius:var(--r);overflow:hidden}}
.tbar{{display:flex;align-items:center;border-bottom:1px solid var(--bd);
  background:rgba(51,65,85,.45);padding:0 16px;gap:2px}}
.tb{{padding:11px 15px;border:none;background:transparent;color:var(--muted);
  cursor:pointer;font-size:.82rem;font-family:'Inter',sans-serif;font-weight:500;
  border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .2s;white-space:nowrap}}
.tb:hover{{color:var(--tx)}}
.tb.act{{color:var(--acc);border-bottom-color:var(--acc)}}
.ext{{margin-left:auto;font-size:.73rem;color:var(--muted);padding:11px 4px;transition:color .2s}}
.ext:hover{{color:var(--acc)}}
.tp{{display:none;padding:14px}}.tp.act{{display:block}}
.ctrl{{display:flex;align-items:center;gap:8px;margin-bottom:9px;flex-wrap:wrap}}
.srch{{flex:1;min-width:120px;background:var(--s2);border:1px solid var(--bd);color:var(--tx);
  padding:6px 12px;border-radius:7px;font-size:.81rem;font-family:'Inter',sans-serif;
  outline:none;transition:border-color .2s}}.srch:focus{{border-color:var(--acc)}}
.srt{{cursor:pointer;padding:4px 9px;border-radius:5px;font-size:.76rem;
  color:var(--muted);transition:all .2s}}.srt:hover{{background:var(--s2)}}
.srt.act{{color:var(--acc);font-weight:600}}
.fbr{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:9px}}
.fb{{padding:3px 11px;border:1px solid var(--bd);border-radius:14px;background:transparent;
  color:var(--muted);cursor:pointer;font-size:.75rem;font-family:'Inter',sans-serif;transition:all .2s}}
.fb em{{font-style:normal;opacity:.6;font-size:.69rem;margin-left:2px}}
.fb:hover{{border-color:var(--c,var(--acc));color:var(--c,var(--acc))}}
.fb.act{{background:var(--c,var(--acc));border-color:transparent;color:#fff;font-weight:600}}
.item{{background:var(--bg);border:1px solid var(--bd);border-radius:7px;
  padding:12px 14px;margin-bottom:6px;transition:border-color .2s,transform .15s}}
.item:hover{{border-color:rgba(56,189,248,.28);transform:translateY(-1px)}}
.item.bci{{border-left:3px solid var(--red)}}.item.dim{{opacity:.4}}
.ih{{display:flex;align-items:flex-start;gap:9px}}
.irk{{width:22px;text-align:center;font-size:.69rem;color:var(--muted);flex-shrink:0;padding-top:2px}}
.isd{{width:31px;height:31px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.69rem;font-weight:700;color:#fff;flex-shrink:0}}
.ib{{flex:1;min-width:0}}
.it{{font-size:.87rem;font-weight:600;line-height:1.4;margin-bottom:4px;display:block;transition:color .2s}}
.it:hover{{color:var(--acc)}}
.im{{display:flex;gap:5px;flex-wrap:wrap;align-items:center;font-size:.7rem;color:var(--muted)}}
.ct{{padding:2px 7px;border-radius:8px;font-size:.67rem;font-weight:500}}
.bct{{background:rgba(248,113,113,.15);color:var(--red);padding:2px 7px;border-radius:8px;font-size:.67rem}}
.ic{{font-size:.79rem;color:#94a3b8;margin-top:6px;line-height:1.6;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
#empty{{text-align:center;padding:36px;color:var(--muted);display:none}}
.model-meta{{font-size:.75rem;color:var(--muted);margin-bottom:9px}}
.model-content{{background:var(--s2);border-radius:7px;padding:14px}}
.model-empty{{font-size:.82rem;color:var(--muted)}}
.mh1,.mh2,.mh3{{font-weight:700;color:var(--acc);margin:12px 0 5px}}
.mh1{{font-size:.95rem}}.mh2{{font-size:.9rem}}.mh3{{font-size:.84rem}}
.mp{{font-size:.82rem;line-height:1.75;color:#cbd5e1;margin:4px 0}}
.mul{{padding-left:16px;margin:5px 0}}.mul li{{font-size:.82rem;line-height:1.7;color:#cbd5e1;margin:3px 0}}
code.ic{{background:rgba(56,189,248,.12);color:var(--acc);padding:1px 5px;border-radius:3px;font-size:.79rem}}
.cdlist{{display:flex;flex-direction:column;gap:4px;margin-top:10px;padding-top:10px;border-top:1px solid var(--bd)}}
.cd{{display:flex;align-items:center;gap:8px;font-size:.78rem}}
.cddot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
.cdl{{flex:1;color:var(--muted)}}.cdv{{font-weight:600;color:var(--tx);min-width:22px;text-align:right}}
footer{{text-align:center;padding:18px;font-size:.7rem;color:var(--muted);
  border-top:1px solid var(--bd);margin-top:14px}}
</style></head>
<body>
<nav>
  <div class="brand">🔭 <span>AI 趋势监控</span></div>
  <div class="nav-r">数据仪表盘 · 更新于 {generated_at}<br>{s["date_from"]} → {s["date_to"]}</div>
</nav>
<main>
<div class="sg">
  <div class="sc"><div class="l">数据总量</div><div class="v" style="color:var(--acc)">{s["total"]}</div><div class="s">过去30天累计</div></div>
  <div class="sc"><div class="l">本次新增</div><div class="v" style="color:var(--grn)">{new_val}</div><div class="s">本次运行采集</div></div>
  <div class="sc"><div class="l">Breaking Change</div><div class="v" style="color:{'var(--red)' if s['breaking'] else 'var(--muted)'}">{s["breaking"]}</div><div class="s">需立即关注</div></div>
  <div class="sc"><div class="l">数据来源</div><div class="v" style="color:var(--amb)">{len(s["by_src"])}</div><div class="s">{src_str}</div></div>
</div>
<div class="cg">
  <div class="card"><div class="st">分类分布</div><div class="cw"><canvas id="catChart"></canvas></div><div class="cdlist">{cat_list_html}</div></div>
  <div class="card"><div class="st">来源分布</div><div class="cw"><canvas id="srcChart"></canvas></div><div class="cdlist">{src_list_html}</div></div>
</div>
{bc_html}<div class="tabs">
  <div class="tbar">
    <button class="tb act" onclick="showTab('list',this)">📊 趋势列表 ({s["total"]})</button>
    <button class="tb" onclick="showTab('model',this)">🤖 模型分析</button>
    <a class="ext" href="trends.html">独立排行页 ↗</a>
  </div>
  <div id="tab-list" class="tp act">
    <div class="ctrl">
      <input class="srch" type="text" placeholder="搜索标题..." oninput="doSearch(this.value)">
      <span class="srt act" id="ss" onclick="srt('score')">评分↓</span>
      <span class="srt" id="st2" onclick="srt('time')">时间↓</span>
    </div>
    <div class="fbr">{cat_btns}</div>
    <div id="list"></div>
    <div id="empty">没有找到匹配内容</div>
  </div>
  <div id="tab-model" class="tp">{model_html}</div>
</div>
</main>
<footer>AI 趋势监控 · 数据来源：GitHub · RSS · Hacker News · arXiv</footer>
<script>
const CC={{{",".join(f'"{k}":"{v}"' for k,v in CAT_COLOR.items())}}};
const CL={{{",".join(f'"{k}":"{v}"' for k,v in CAT_LABEL.items())}}};
const DATA={items_json};
let cat='all',q='',sortBy='score';
function sc(s){{return s>=70?'#4ade80':s>=50?'#fbbf24':'#94a3b8'}}
function render(){{
  let d=[...DATA];
  if(cat!=='all')d=d.filter(x=>x.category===cat);
  if(q)d=d.filter(x=>x.title.toLowerCase().includes(q));
  if(sortBy==='time')d.sort((a,b)=>b.published_at.localeCompare(a.published_at));
  document.getElementById('empty').style.display=d.length?'none':'block';
  document.getElementById('list').innerHTML=d.map((x,i)=>`
    <div class="item${{x.is_breaking?' bci':''}}${{x.score<30?' dim':''}}">
      <div class="ih">
        <span class="irk">#${{i+1}}</span>
        <span class="isd" style="background:${{sc(x.score)}}">${{Math.round(x.score)}}</span>
        <div class="ib">
          <a class="it" href="${{x.url}}" target="_blank">${{x.title}}</a>
          <div class="im">
            <span>${{x.source}}</span><span>·</span><span>${{x.published_at}}</span>
            <span class="ct" style="background:${{CC[x.category]}}22;color:${{CC[x.category]}}">${{CL[x.category]||x.category}}</span>
            ${{x.is_breaking?'<span class="bct">⚡ Breaking</span>':''}}
          </div>
          ${{x.content?`<div class="ic">${{x.content.slice(0,200)}}</div>`:''}}
        </div>
      </div>
    </div>`).join('');
}}
function fc(c,el){{
  cat=c;q='';
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('act'));
  el.classList.add('act');render();
}}
function doSearch(v){{q=v.toLowerCase();render()}}
function srt(by){{
  sortBy=by;
  document.getElementById('ss').className='srt'+(by==='score'?' act':'');
  document.getElementById('st2').className='srt'+(by==='time'?' act':'');
  render();
}}
function showTab(id,el){{
  document.querySelectorAll('.tp').forEach(p=>p.classList.remove('act'));
  document.querySelectorAll('.tb').forEach(b=>b.classList.remove('act'));
  document.getElementById('tab-'+id).classList.add('act');
  el.classList.add('act');
}}
render();
Chart.defaults.color='#94a3b8';Chart.defaults.borderColor='rgba(148,163,184,.07)';
new Chart(document.getElementById('catChart'),{{type:'doughnut',
  data:{{labels:{json.dumps(cat_labels,ensure_ascii=False)},datasets:[{{data:{cat_data},
  backgroundColor:{json.dumps(cat_colors)},borderWidth:2,borderColor:'#1e293b',hoverOffset:5}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
  plugins:{{legend:{{position:'right',labels:{{boxWidth:11,padding:9,font:{{size:11}}}}}}}}}}
}});
new Chart(document.getElementById('srcChart'),{{type:'bar',
  data:{{labels:{json.dumps(src_labels,ensure_ascii=False)},datasets:[{{data:{src_data},
  backgroundColor:{json.dumps(src_colors)},borderRadius:5,borderWidth:0}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
  plugins:{{legend:{{display:false}}}},
  scales:{{x:{{grid:{{color:'rgba(148,163,184,.06)'}}}},y:{{grid:{{display:false}}}}}}}}
}});
</script>
</body></html>"""

    # ─── 趋势排行 trends.html ──────────────────────────────────────────────

    def _trends(self, items_json: str, generated_at: str, s: dict) -> str:
        cat_btns = (
            '<button class="f-btn active" data-cat="all" onclick="filterCat(\'all\',this)">全部'
            f' <span class="f-cnt">{s["total"]}</span></button>'
        ) + "".join(
            f'<button class="f-btn" data-cat="{k}" onclick="filterCat(\'{k}\',this)"'
            f' style="--cc:{CAT_COLOR.get(k,"#888")}">'
            f'{CAT_LABEL.get(k,k)} <span class="f-cnt">{s["by_cat"].get(k,0)}</span></button>'
            for k in CAT_LABEL if s["by_cat"].get(k, 0) > 0
        )
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 趋势排行 · AI 趋势监控</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0f172a;--s1:#1e293b;--s2:#334155;--bd:rgba(148,163,184,.12);
  --acc:#38bdf8;--grn:#4ade80;--amb:#fbbf24;--red:#f87171;--tx:#f1f5f9;--muted:#94a3b8;--r:10px}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--tx)}}
a{{color:inherit;text-decoration:none}}
nav{{display:flex;align-items:center;justify-content:space-between;padding:14px 32px;
  border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:100;
  background:rgba(15,23,42,.92);backdrop-filter:blur(12px);gap:16px;flex-wrap:wrap}}
.back{{font-size:.84rem;color:var(--muted);transition:color .2s;white-space:nowrap}}
.back:hover{{color:var(--tx)}}
.nav-title{{font-size:.98rem;font-weight:600}}
.nav-r{{display:flex;align-items:center;gap:10px}}
.cnt-lbl{{font-size:.78rem;color:var(--muted);white-space:nowrap}}
.search{{background:var(--s2);border:1px solid var(--bd);color:var(--tx);
  padding:7px 13px;border-radius:8px;font-size:.84rem;width:200px;
  font-family:'Inter',sans-serif;outline:none;transition:border-color .2s}}
.search:focus{{border-color:var(--acc)}}
.filter-bar{{padding:14px 32px;border-bottom:1px solid var(--bd);display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.f-btn{{padding:5px 13px;border:1px solid var(--bd);border-radius:20px;background:transparent;
  color:var(--muted);cursor:pointer;font-size:.8rem;font-family:'Inter',sans-serif;
  transition:all .2s;display:flex;align-items:center;gap:5px}}
.f-btn:hover{{border-color:var(--cc,var(--acc));color:var(--cc,var(--acc))}}
.f-btn.active{{background:var(--cc,var(--acc));border-color:transparent;color:#fff;font-weight:600}}
.f-cnt{{opacity:.65;font-size:.72rem}}
.sort-bar{{padding:8px 32px;display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--muted);border-bottom:1px solid var(--bd)}}
.s-btn{{cursor:pointer;padding:3px 9px;border-radius:6px;transition:background .2s}}
.s-btn:hover{{background:var(--s2)}}
.s-btn.active{{color:var(--acc);font-weight:600}}
#list{{padding:16px 24px 48px;max-width:900px;margin:0 auto}}
.item{{background:var(--s1);border:1px solid var(--bd);border-radius:var(--r);
  padding:16px 18px;margin-bottom:8px;transition:border-color .2s,transform .15s;cursor:default}}
.item:hover{{border-color:rgba(56,189,248,.28);transform:translateY(-1px)}}
.item.bc{{border-left:3px solid var(--red)}}
.item.dim{{opacity:.4}}
.item-head{{display:flex;align-items:flex-start;gap:10px}}
.rank{{width:26px;text-align:center;font-size:.75rem;color:var(--muted);flex-shrink:0;padding-top:2px}}
.sdot{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.72rem;font-weight:700;color:#fff;flex-shrink:0}}
.ibody{{flex:1;min-width:0}}
.ititle{{font-size:.92rem;font-weight:600;line-height:1.4;margin-bottom:5px;
  display:block;transition:color .2s}}
.ititle:hover{{color:var(--acc)}}
.imeta{{display:flex;gap:7px;flex-wrap:wrap;align-items:center;font-size:.74rem;color:var(--muted)}}
.ctag{{padding:2px 9px;border-radius:10px;font-weight:500;font-size:.7rem}}
.bctag{{background:rgba(239,68,68,.15);color:var(--red);padding:2px 8px;border-radius:10px;font-size:.7rem}}
.icontent{{font-size:.82rem;color:#a1a1aa;margin-top:8px;line-height:1.6;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
#empty{{text-align:center;padding:64px;color:var(--muted);display:none}}
</style>
</head>
<body>
<nav>
  <a class="back" href="index.html">← 返回仪表盘</a>
  <span class="nav-title">🔥 AI 趋势排行</span>
  <div class="nav-r">
    <span class="cnt-lbl" id="cnt">{s["total"]} 条</span>
    <input class="search" type="text" placeholder="搜索标题..." oninput="doSearch(this.value)">
  </div>
</nav>
<div class="filter-bar">{cat_btns}</div>
<div class="sort-bar">
  排序：
  <span class="s-btn active" id="ss" onclick="setSort('score')">评分↓</span>
  <span class="s-btn" id="st" onclick="setSort('time')">时间↓</span>
  <span style="margin-left:auto;font-size:.75rem">更新于 {generated_at}</span>
</div>
<div id="list"></div>
<div id="empty">没有找到匹配的内容</div>
<script>
const CAT_COLOR={{{",".join(f'"{k}":"{v}"' for k,v in CAT_COLOR.items())}}};
const CAT_LABEL={{{",".join(f'"{k}":"{v}"' for k,v in CAT_LABEL.items())}}};
const DATA={items_json};
let cat='all',q='',sortBy='score';
function sc(s){{return s>=70?'#4ade80':s>=50?'#fbbf24':'#94a3b8'}}
function render(){{
  let d=[...DATA];
  if(cat!=='all')d=d.filter(x=>x.category===cat);
  if(q)d=d.filter(x=>x.title.toLowerCase().includes(q));
  if(sortBy==='time')d.sort((a,b)=>b.published_at.localeCompare(a.published_at));
  document.getElementById('cnt').textContent=d.length+' 条';
  document.getElementById('empty').style.display=d.length?'none':'block';
  document.getElementById('list').innerHTML=d.map((x,i)=>`
    <div class="item${{x.is_breaking?' bc':''}}${{x.score<30?' dim':''}}">
      <div class="item-head">
        <span class="rank">#${{i+1}}</span>
        <span class="sdot" style="background:${{sc(x.score)}}">${{Math.round(x.score)}}</span>
        <div class="ibody">
          <a class="ititle" href="${{x.url}}" target="_blank">${{x.title}}</a>
          <div class="imeta">
            <span>${{x.source}}</span><span>·</span><span>${{x.published_at}}</span>
            <span class="ctag" style="background:${{CAT_COLOR[x.category]}}22;color:${{CAT_COLOR[x.category]}}">${{CAT_LABEL[x.category]||x.category}}</span>
            ${{x.is_breaking?'<span class="bctag">⚡ Breaking</span>':''}}
          </div>
          ${{x.content?`<div class="icontent">${{x.content.slice(0,200)}}</div>`:''}}
        </div>
      </div>
    </div>`).join('');
}}
function filterCat(c,el){{
  cat=c;q='';
  document.querySelectorAll('.f-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  render();
}}
function doSearch(v){{q=v.toLowerCase();render()}}
function setSort(by){{
  sortBy=by;
  document.getElementById('ss').className='s-btn'+(by==='score'?' active':'');
  document.getElementById('st').className='s-btn'+(by==='time'?' active':'');
  render();
}}
render();
</script>
</body></html>"""
