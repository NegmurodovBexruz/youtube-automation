"""
Hisobot yaratish — terminal va chiroyli HTML dashboard
Chart.js yordamida vizual grafiklar bilan.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from models.video import Video

logger = logging.getLogger(__name__)


def _fmt_num(n: int) -> str:
    return f"{n:,}" if n else "0"


def _truncate(s: str, length: int = 40) -> str:
    return (s[:length] + "…") if len(s) > length else s


class ReportGenerator:
    def __init__(
        self,
        videos: List[Video],
        analytics: Dict[str, Any],
        output_dir: str = "output",
    ):
        self.videos = videos
        self.analytics = analytics
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────
    # Terminal xulosa
    # ──────────────────────────────────────────────────────

    def print_summary(self):
        s = self.analytics.get("summary", {})
        v = self.analytics.get("views", {})
        types = self.analytics.get("video_types", {})
        dur = self.analytics.get("duration", {})
        top_comments = self.analytics.get("top_comments", [])

        print("\n" + "═" * 62)
        print("  📊  YOUTUBE AUTOMATION — TAHLIL NATIJALARI")
        print("═" * 62)
        print(f"\n  🎬 Jami tahlil qilingan        : {s.get('total_videos_analyzed', 0)}")
        print(f"  👁️  O'rtacha ko'rishlar         : {_fmt_num(v.get('average', 0))}")
        print(f"  🏆 Eng ko'p ko'rilgan           : {_truncate(v.get('most_viewed_title', 'N/A'), 45)}")
        print(f"  ❤️  Eng ko'p liked              : {_truncate(s.get('most_liked_video', 'N/A'), 45)}")
        print(f"  📺 Shorts / Standard            : {types.get('ratio', 'N/A')}")
        print(f"  📢 Eng faol kanal               : {s.get('most_active_channel', 'N/A')}")
        print(f"  ⏱️  O'rtacha davomiylik          : {dur.get('average_formatted', 'N/A')}")

        if top_comments:
            print("\n  💬 Eng ko'p like olgan kommentlar:")
            for i, c in enumerate(top_comments[:3], 1):
                print(f"     {i}. [{_fmt_num(c['likes'])} ❤️] @{c['author']}: {_truncate(c['text'], 55)}")

        print("\n" + "═" * 62)

    # ──────────────────────────────────────────────────────
    # HTML dashboard
    # ──────────────────────────────────────────────────────

    def generate_html_report(self, filename: str = "report.html") -> str:
        path = self.output_dir / filename
        html = self._build_html()
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML hisobot yaratildi: {path}")
        return str(path)

    def _views_chart_data(self) -> str:
        labels = [_truncate(v.video_title, 25) for v in self.videos]
        data = [v.view_count for v in self.videos]
        return json.dumps({"labels": labels, "data": data})

    def _likes_chart_data(self) -> str:
        labels = [_truncate(v.video_title, 25) for v in self.videos]
        data = [v.like_count for v in self.videos]
        return json.dumps({"labels": labels, "data": data})

    def _type_pie_data(self) -> str:
        t = self.analytics.get("video_types", {})
        return json.dumps({"shorts": t.get("shorts", 0), "standard": t.get("standard", 0)})

    def _duration_chart_data(self) -> str:
        labels = [_truncate(v.video_title, 25) for v in self.videos]
        data = [v.duration_seconds for v in self.videos]
        return json.dumps({"labels": labels, "data": data})

    def _video_cards_html(self) -> str:
        html = ""
        for i, v in enumerate(self.videos, 1):
            badge_cls = "shorts" if v.is_shorts else "standard"
            badge_txt = "⚡ Shorts" if v.is_shorts else "▶ Standard"
            desc = (v.description or "")[:180].replace("<", "&lt;").replace(">", "&gt;")
            comments_html = self._mini_comments(v)
            html += f"""
        <div class="vcard" data-type="{v.video_type}">
          <div class="vcard-rank">#{i}</div>
          <span class="badge {badge_cls}">{badge_txt}</span>
          <div class="vcard-thumb">
            <img src="{v.thumbnail_url}" alt="{v.video_title[:30]}" loading="lazy"
                 onerror="this.src='https://placehold.co/480x270/13131f/555?text=No+Preview'">
            <div class="vcard-duration">{v.duration or '--'}</div>
          </div>
          <div class="vcard-body">
            <a class="vcard-title" href="{v.video_url}" target="_blank" rel="noopener">{v.video_title[:80]}</a>
            <div class="vcard-channel">
              <span>📺 {v.channel_name or 'N/A'}</span>
              <span class="muted">👥 {v.channel_subscribers or 'N/A'}</span>
            </div>
            <div class="vcard-stats">
              <div class="vs"><span class="vs-val">{_fmt_num(v.view_count)}</span><span class="vs-lbl">Ko'rishlar</span></div>
              <div class="vs"><span class="vs-val">{_fmt_num(v.like_count)}</span><span class="vs-lbl">Likelar</span></div>
              <div class="vs"><span class="vs-val">{v.upload_date or 'N/A'}</span><span class="vs-lbl">Sana</span></div>
            </div>
            <p class="vcard-desc">{desc}{'…' if len(v.description or '') > 180 else ''}</p>
            {comments_html}
          </div>
        </div>"""
        return html

    def _mini_comments(self, video: Video) -> str:
        if not video.top_comments:
            return ""
        items = ""
        for c in video.top_comments[:3]:
            txt = (c.text or "")[:100].replace("<", "&lt;")
            items += f'<div class="mc-item"><span class="mc-author">@{c.author}</span> <span class="mc-text">{txt}</span> <span class="mc-likes">❤️ {_fmt_num(c.likes)}</span></div>'
        return f'<div class="mc-list"><div class="mc-head">💬 Kommentlar</div>{items}</div>'

    def _top_comments_html(self) -> str:
        top = self.analytics.get("top_comments", [])
        if not top:
            return '<p class="muted">Kommentlar topilmadi</p>'
        medals = ["🥇", "🥈", "🥉"]
        html = ""
        for i, c in enumerate(top):
            html += f"""
        <div class="tc-card">
          <div class="tc-medal">{medals[i] if i < 3 else '💬'}</div>
          <div class="tc-body">
            <div class="tc-meta">
              <strong>@{c['author']}</strong>
              <span class="tc-likes">❤️ {_fmt_num(c['likes'])}</span>
              <span class="muted">· {c.get('date', '')}</span>
            </div>
            <p class="tc-text">{(c['text'] or '')[:250]}</p>
            <div class="tc-source">📺 {_truncate(c['video_title'], 50)}</div>
          </div>
        </div>"""
        return html

    def _channels_table_html(self) -> str:
        ch = self.analytics.get("channels", {})
        rows = ""
        for i, item in enumerate(ch.get("top_channels", []), 1):
            rows += f"<tr><td class='td-rank'>{i}</td><td>{item['channel']}</td><td class='td-count'>{item['video_count']}</td></tr>"
        return rows

    def _build_html(self) -> str:
        v = self.analytics.get("views", {})
        lk = self.analytics.get("likes", {})
        t = self.analytics.get("video_types", {})
        c = self.analytics.get("channels", {})
        d = self.analytics.get("duration", {})

        return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YouTube Analytics Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
:root{{--bg:#0c0c12;--surface:#14141e;--surface2:#1c1c2a;--border:#252535;--accent:#e63950;--accent2:#f9a825;--blue:#4a7eff;--green:#28c98f;--text:#ddddf0;--muted:#77778a;--radius:14px;--shadow:0 8px 32px rgba(0,0,0,.5)}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;min-height:100vh}}
.container{{max-width:1400px;margin:0 auto;padding:32px 24px}}
.header{{display:flex;align-items:center;gap:16px;margin-bottom:40px;padding-bottom:24px;border-bottom:1px solid var(--border)}}
.header-logo{{width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0}}
.header h1{{font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,var(--accent) 30%,var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header-sub{{color:var(--muted);font-size:.85rem;margin-top:2px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:40px}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px 18px;position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s}}
.kpi:hover{{transform:translateY(-3px);box-shadow:var(--shadow)}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--kpi-color,var(--accent))}}
.kpi-icon{{font-size:1.6rem;margin-bottom:10px}}
.kpi-val{{font-size:1.5rem;font-weight:800;color:var(--kpi-color,var(--accent2))}}
.kpi-lbl{{font-size:.75rem;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.05em}}
.section{{margin-bottom:52px}}
.section-title{{font-size:1.05rem;font-weight:700;color:var(--accent2);margin-bottom:20px;display:flex;align-items:center;gap:8px;padding-bottom:10px;border-bottom:1px solid var(--border)}}
.charts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px;margin-bottom:40px}}
.chart-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px}}
.chart-card h3{{font-size:.85rem;color:var(--muted);margin-bottom:16px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}}
.chart-wrap{{position:relative;height:220px}}
.filter-bar{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.filter-btn{{padding:6px 16px;border-radius:20px;border:1px solid var(--border);background:var(--surface2);color:var(--muted);font-size:.82rem;cursor:pointer;transition:all .2s}}
.filter-btn:hover,.filter-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
.vcards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:24px}}
.vcard{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:transform .2s,box-shadow .2s;position:relative}}
.vcard:hover{{transform:translateY(-5px);box-shadow:var(--shadow)}}
.vcard-rank{{position:absolute;top:10px;left:10px;z-index:2;background:rgba(0,0,0,.75);color:var(--accent2);font-weight:800;font-size:.85rem;padding:3px 9px;border-radius:20px}}
.badge{{position:absolute;top:10px;right:10px;z-index:2;font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:20px}}
.badge.shorts{{background:rgba(230,57,80,.85);color:#fff}}
.badge.standard{{background:rgba(74,126,255,.85);color:#fff}}
.vcard-thumb{{position:relative}}
.vcard-thumb img{{width:100%;height:200px;object-fit:cover;display:block}}
.vcard-duration{{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.8);color:#fff;font-size:.75rem;font-weight:600;padding:2px 7px;border-radius:4px}}
.vcard-body{{padding:16px}}
.vcard-title{{display:block;color:var(--text);text-decoration:none;font-weight:700;font-size:.92rem;line-height:1.45;margin-bottom:8px}}
.vcard-title:hover{{color:var(--accent2)}}
.vcard-channel{{display:flex;gap:12px;font-size:.78rem;color:var(--muted);margin-bottom:10px;flex-wrap:wrap}}
.vcard-stats{{display:flex;gap:8px;margin-bottom:10px}}
.vs{{flex:1;background:var(--surface2);border-radius:8px;padding:8px 6px;text-align:center}}
.vs-val{{display:block;font-size:.85rem;font-weight:700;color:var(--accent2)}}
.vs-lbl{{display:block;font-size:.65rem;color:var(--muted);margin-top:2px}}
.vcard-desc{{font-size:.76rem;color:var(--muted);line-height:1.55}}
.mc-list{{margin-top:10px;border-top:1px solid var(--border);padding-top:10px}}
.mc-head{{font-size:.72rem;color:var(--muted);font-weight:600;margin-bottom:6px;text-transform:uppercase}}
.mc-item{{background:var(--surface2);border-radius:8px;padding:7px 10px;margin-bottom:5px;font-size:.75rem}}
.mc-author{{color:var(--accent2);font-weight:600}}
.mc-text{{color:var(--text);line-height:1.4}}
.mc-likes{{color:var(--accent);font-size:.7rem}}
.tc-card{{display:flex;gap:16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px;margin-bottom:12px;transition:transform .15s}}
.tc-card:hover{{transform:translateX(4px)}}
.tc-medal{{font-size:1.8rem;flex-shrink:0}}
.tc-body{{flex:1}}
.tc-meta{{display:flex;align-items:center;gap:12px;margin-bottom:6px;font-size:.83rem;flex-wrap:wrap}}
.tc-likes{{color:var(--accent);font-weight:700}}
.tc-text{{line-height:1.6;font-size:.88rem;margin-bottom:6px}}
.tc-source{{font-size:.75rem;color:var(--muted)}}
.ch-table{{width:100%;border-collapse:collapse}}
.ch-table thead th{{padding:10px 14px;text-align:left;font-size:.72rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid var(--border)}}
.ch-table tbody tr{{transition:background .15s}}
.ch-table tbody tr:hover td{{background:var(--surface2)}}
.ch-table td{{padding:11px 14px;font-size:.88rem;border-bottom:1px solid var(--border)}}
.td-rank{{color:var(--accent2);font-weight:700;width:40px}}
.td-count{{font-weight:700;color:var(--accent);background:rgba(230,57,80,.1);border-radius:6px;text-align:center;width:80px}}
.muted{{color:var(--muted)}}
@media(max-width:640px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.vcards-grid{{grid-template-columns:1fr}}.charts-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <div class="header-logo">📊</div>
  <div>
    <h1>YouTube Analytics Dashboard</h1>
    <div class="header-sub">Avtomatik yig'ilgan · {len(self.videos)} ta video tahlil qilindi</div>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi" style="--kpi-color:var(--accent)"><div class="kpi-icon">🎬</div><div class="kpi-val">{len(self.videos)}</div><div class="kpi-lbl">Jami video</div></div>
  <div class="kpi" style="--kpi-color:var(--blue)"><div class="kpi-icon">👁️</div><div class="kpi-val">{_fmt_num(v.get('average', 0))}</div><div class="kpi-lbl">O'rtacha ko'rishlar</div></div>
  <div class="kpi" style="--kpi-color:var(--accent2)"><div class="kpi-icon">❤️</div><div class="kpi-val">{_fmt_num(lk.get('average', 0))}</div><div class="kpi-lbl">O'rtacha likelar</div></div>
  <div class="kpi" style="--kpi-color:var(--green)"><div class="kpi-icon">⏱️</div><div class="kpi-val">{d.get('average_formatted', 'N/A')}</div><div class="kpi-lbl">O'rtacha davomiylik</div></div>
  <div class="kpi" style="--kpi-color:var(--accent)"><div class="kpi-icon">⚡</div><div class="kpi-val">{t.get('ratio', 'N/A')}</div><div class="kpi-lbl">Shorts / Standard</div></div>
  <div class="kpi" style="--kpi-color:var(--blue)"><div class="kpi-icon">📢</div><div class="kpi-val" style="font-size:1rem">{c.get('most_active_channel', 'N/A')}</div><div class="kpi-lbl">Eng faol kanal</div></div>
</div>

<div class="section">
  <div class="section-title">📈 Grafiklar</div>
  <div class="charts-grid">
    <div class="chart-card"><h3>👁️ Ko'rishlar soni</h3><div class="chart-wrap"><canvas id="viewsChart"></canvas></div></div>
    <div class="chart-card"><h3>❤️ Like soni</h3><div class="chart-wrap"><canvas id="likesChart"></canvas></div></div>
    <div class="chart-card"><h3>⚡ Shorts vs Standard</h3><div class="chart-wrap"><canvas id="typeChart"></canvas></div></div>
    <div class="chart-card"><h3>⏱️ Davomiylik (soniya)</h3><div class="chart-wrap"><canvas id="durChart"></canvas></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">🎬 Videolar</div>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filterCards('all',this)">Barchasi</button>
    <button class="filter-btn" onclick="filterCards('standard',this)">Standard</button>
    <button class="filter-btn" onclick="filterCards('shorts',this)">Shorts</button>
  </div>
  <div class="vcards-grid" id="cardsGrid">{self._video_cards_html()}</div>
</div>

<div class="section">
  <div class="section-title">💬 Eng Ko'p Like Olgan Kommentlar</div>
  {self._top_comments_html()}
</div>

<div class="section">
  <div class="section-title">📺 Kanallar Reytingi</div>
  <table class="ch-table">
    <thead><tr><th>#</th><th>Kanal nomi</th><th>Video soni</th></tr></thead>
    <tbody>{self._channels_table_html()}</tbody>
  </table>
</div>

</div>
<script>
Chart.defaults.color='#77778a';
Chart.defaults.borderColor='#252535';
Chart.defaults.font.family="'Segoe UI',system-ui,sans-serif";
const AC='#e63950',AC2='#f9a825',BL='#4a7eff',GR='#28c98f';
function grad(ctx,c){{const g=ctx.createLinearGradient(0,0,0,220);g.addColorStop(0,c+'cc');g.addColorStop(1,c+'22');return g;}}
function barChart(id,raw,color){{
  const ctx=document.getElementById(id).getContext('2d');
  new Chart(ctx,{{type:'bar',data:{{labels:raw.labels,datasets:[{{data:raw.data,backgroundColor:grad(ctx,color),borderColor:color,borderWidth:1,borderRadius:6}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
  scales:{{x:{{ticks:{{maxRotation:45,font:{{size:9}}}}}},y:{{ticks:{{callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v}}}}}}}}}});
}}
barChart('viewsChart',{self._views_chart_data()},BL);
barChart('likesChart',{self._likes_chart_data()},AC);
barChart('durChart',{self._duration_chart_data()},GR);
(function(){{
  const p={self._type_pie_data()};
  const ctx=document.getElementById('typeChart').getContext('2d');
  new Chart(ctx,{{type:'doughnut',data:{{labels:['Shorts','Standard'],datasets:[{{data:[p.shorts,p.standard],backgroundColor:[AC,BL],borderColor:'#14141e',borderWidth:3,hoverOffset:8}}]}},
  options:{{responsive:true,maintainAspectRatio:false,cutout:'65%',plugins:{{legend:{{position:'bottom',labels:{{padding:16,usePointStyle:true}}}}}}}}}});
}})();
function filterCards(type,btn){{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.vcard').forEach(c=>{{c.style.display=(type==='all'||c.dataset.type===type)?'':'none'}});
}}
</script>
</body>
</html>"""
