# -*- coding: utf-8 -*-
"""
THE CK AI TIMES — Gerador Editorial 100% Factual (Zero Invenções)
Gera index.html (para publicação online no GitHub Pages) + ultima-edicao.html.
Inclui: Capa Factual das Principais Fontes + Ranking Mundial Top 50 Modelos de IA (Artificial Analysis) + 4 Cadernos Filtráveis.
"""
import json
import os
import html as html_lib
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dados')
BRT = timezone(timedelta(hours=-3))

def esc(s):
    return html_lib.escape(str(s or ''), quote=True)

def fmt_ctx(tokens):
    if not tokens:
        return '—'
    if tokens >= 1000000:
        return f"{tokens/1000000:.1f}M".replace('.0M', 'M')
    if tokens >= 1000:
        return f"{int(tokens/1000)}K"
    return str(tokens)

def fmt_price(pin, pout):
    if pin is None and pout is None:
        return '—'
    pi = f"${pin:.2f}" if isinstance(pin, (int, float)) else '—'
    po = f"${pout:.2f}" if isinstance(pout, (int, float)) else '—'
    return f"{pi} / {po}"

def build_newspaper():
    latest_path = os.path.join(DATA_DIR, 'latest.json')
    with open(latest_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    d_str = raw.get('date') or datetime.now(BRT).strftime('%Y-%m-%d')
    items = raw.get('items', [])
    rankings = raw.get('rankings', {})
    top50 = rankings.get('top50_overall', [])
    top20_open = rankings.get('top20_open_source', [])

    # Seleciona os destaques reais de capa diretamente das fontes prioritárias (ZERO invenção)
    priority_sources = [
        'The Rundown AI', 'TLDR AI', 'OpenAI News', 'Anthropic News (Claude)',
        'Google AI / DeepMind', 'NVIDIA Industrial & AI', 'n8n (Automação & Orquestração)',
        'Microsoft Copilot & Azure AI', 'One Useful Thing (Ethan Mollick)'
    ]
    front_picks = []
    used_urls = set()
    for psrc in priority_sources:
        for it in items:
            if it.get('source') == psrc and it.get('url') not in used_urls:
                front_picks.append(it)
                used_urls.add(it.get('url'))
                break
        if len(front_picks) >= 6:
            break
    if not front_picks and items:
        front_picks = items[:6]

    lead = front_picks[0] if front_picks else {
        'source': 'CK AI Times', 'title': 'Aguardando primeira coleta', 'summary': '', 'url': '#', 'date': d_str
    }
    side_picks = front_picks[1:6]

    side_html = []
    for s in side_picks:
        side_html.append(f'''
        <article class="signal-card">
          <div class="signal-tag">{esc(s.get('source'))} · {esc(s.get('date'))}</div>
          <h3><a href="{esc(s.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(s.get('title'))}</a></h3>
          <p>{esc(s.get('summary') or 'Clique para ler o conteúdo original direto na fonte.')}</p>
        </article>''')

    # Monta linhas da tabela Top 50 (Geral) e Top 20 Open-Source
    max_score = top50[0]['intelligence_index'] if top50 else 100
    def make_rank_rows(model_list, list_key):
        rows = []
        for idx, m in enumerate(model_list, 1):
            pct = min(100, int((m['intelligence_index'] / max_score) * 100)) if max_score else 0
            badge_type = '<span class="pill-open">🔓 Open-Source</span>' if m['is_open_weights'] else '<span class="pill-cloud">☁️ Nuvem</span>'
            creator = m.get('creator', '—')
            rows.append(f'''
            <tr class="rank-row" data-list="{list_key}" data-creator="{esc(creator.lower())}" data-name="{esc((m.get('name','') + ' ' + creator).lower())}">
              <td class="col-pos">#{idx:02d}</td>
              <td class="col-model">
                <a href="{esc(m.get('url'))}" target="_blank" rel="noopener noreferrer" class="model-link">{esc(m.get('name'))}</a>
                <span class="creator-sub">{esc(creator)}</span>
              </td>
              <td class="col-score">
                <div class="score-wrap">
                  <strong>{m['intelligence_index']:.2f}</strong>
                  <div class="score-bar"><div class="score-fill" style="width:{pct}%;"></div></div>
                </div>
              </td>
              <td>{badge_type}</td>
              <td class="mono-cell">{fmt_ctx(m.get('context_window'))}</td>
              <td class="mono-cell">{fmt_price(m.get('price_in'), m.get('price_out'))}</td>
            </tr>''')
        return ''.join(rows)

    rank_rows_all = make_rank_rows(top50, 'overall') + make_rank_rows(top20_open, 'opensource')

    # Monta todos os 4 cadernos de notícias reais
    items_html = []
    for it in items:
        sec = it.get('section', 'newsletters')
        search_blob = (it.get('title', '') + ' ' + it.get('source', '') + ' ' + it.get('summary', '')).lower()
        items_html.append(f'''
        <article class="news-row" data-sec="{esc(sec)}" data-search="{esc(search_blob)}">
          <div>
            <div class="news-meta">
              <span class="src-pill">{esc(it.get('source'))}</span>
              <span class="news-date">{esc(it.get('date'))}</span>
            </div>
            <h4><a href="{esc(it.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(it.get('title'))}</a></h4>
            <p>{esc(it.get('summary') or 'Abrir matéria original na fonte.')}</p>
          </div>
          <a class="src-go" href="{esc(it.get('url'))}" target="_blank" rel="noopener noreferrer">Abrir fonte original ↗</a>
        </article>''')

    ok_sources = sum(1 for v in raw.get('sources_status', {}).values() if v.startswith('OK'))
    total_sources = len(raw.get('sources_status', {}))

    # Top 3 resumo rápido para o cabeçalho do ranking
    top3_strip = ' · '.join(
        f"<strong>#{i}</strong> {esc(m['name'])} ({m['intelligence_index']:.1f})"
        for i, m in enumerate(top50[:3], 1)
    )

    doc = f'''<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The CK AI Times · Edição Diária &amp; Ranking Top 50 LLMs | CK Intelligence</title>
  <meta name="description" content="Radar diário 100% factual de Inteligência Artificial (20 fontes reais + Ranking Mundial Top 50 Modelos de Linguagem ao vivo)." />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&family=Playfair+Display:wght@700;800;900&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg: #050810;
      --paper: #0B111E;
      --card: #0F172A;
      --border: rgba(255,255,255,0.11);
      --rule: rgba(255,255,255,0.22);
      --text: #F8FAFC;
      --muted: #94A3B8;
      --accent: #38BDF8;
      --blue: #0A6CFF;
      --emerald: #10B981;
      --amber: #F59E0B;
    }}
    body.paper-mode {{
      --bg: #F3EFE6;
      --paper: #FCFBF7;
      --card: #FFFFFF;
      --border: rgba(15,23,42,0.14);
      --rule: #1E293B;
      --text: #0F172A;
      --muted: #475569;
      --accent: #0A6CFF;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg); color: var(--text);
      font-family: 'Inter', system-ui, sans-serif;
      line-height: 1.55; padding: 16px 12px 64px 12px;
      transition: background 0.25s, color 0.25s;
    }}
    a {{ color: inherit; text-decoration: none; }}
    a:hover {{ color: var(--accent); text-decoration: underline; }}

    .newspaper {{
      max-width: 1260px; margin: 0 auto;
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px 32px 42px 32px;
      box-shadow: 0 28px 80px -24px rgba(0,0,0,0.6);
    }}
    @media (max-width: 720px) {{ .newspaper {{ padding: 16px; }} }}

    .top-utility {{
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
      font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted);
      padding-bottom: 12px; border-bottom: 1px solid var(--border);
    }}
    .verified-pill {{
      color: var(--emerald); background: rgba(16,185,129,0.12);
      border: 1px solid rgba(16,185,129,0.35); padding: 4px 10px; border-radius: 999px; font-weight: 700;
    }}
    .theme-btn {{
      background: var(--card); color: var(--text); border: 1px solid var(--border);
      padding: 6px 12px; border-radius: 999px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
    }}

    .masthead {{
      text-align: center; padding: 18px 0 14px 0;
      border-bottom: 3px double var(--rule);
    }}
    .masthead h1 {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: clamp(32px, 5.2vw, 62px); font-weight: 900;
      letter-spacing: -0.02em; line-height: 1;
    }}
    .masthead-sub {{
      margin-top: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px;
      text-transform: uppercase; letter-spacing: 0.2em; color: var(--accent);
    }}
    .dateline {{
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
      padding: 10px 0; border-bottom: 1px solid var(--rule);
      font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted);
    }}

    .quick-nav {{
      display: flex; gap: 8px; flex-wrap: wrap; padding: 14px 0; border-bottom: 1px solid var(--border);
    }}
    .quick-nav a {{
      font-family: 'JetBrains Mono', monospace; font-size: 11.5px; font-weight: 700;
      padding: 6px 13px; border-radius: 8px; background: var(--card); border: 1px solid var(--border);
    }}
    .quick-nav a.highlight {{ background: var(--blue); color: #fff; border-color: var(--accent); }}

    /* Front Page */
    .front-page {{
      display: grid; grid-template-columns: 1.15fr 1fr; gap: 26px;
      padding: 24px 0; border-bottom: 2px solid var(--rule);
    }}
    @media (max-width: 900px) {{ .front-page {{ grid-template-columns: 1fr; }} }}

    .lead-kicker {{
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
      color: var(--emerald); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;
    }}
    .lead-box h2 {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: clamp(24px, 3vw, 38px); font-weight: 800; line-height: 1.15; margin-bottom: 12px;
    }}
    .lead-deck {{ font-size: 15.5px; color: var(--muted); margin-bottom: 16px; }}
    .lead-box .cta-src {{
      display: inline-flex; align-items: center; gap: 6px;
      background: var(--blue); color: #fff; padding: 10px 16px; border-radius: 9px;
      font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700;
    }}

    .signals-col {{
      display: flex; flex-direction: column; gap: 11px;
      border-left: 1px solid var(--border); padding-left: 24px;
    }}
    @media (max-width: 900px) {{ .signals-col {{ border-left: none; padding-left: 0; border-top: 1px solid var(--border); padding-top: 18px; }} }}
    .section-kicker {{
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.16em; color: var(--accent); margin-bottom: 6px;
    }}
    .signal-card {{ padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
    .signal-card:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .signal-tag {{
      font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; color: var(--amber); margin-bottom: 3px;
    }}
    .signal-card h3 {{ font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 700; line-height: 1.28; margin-bottom: 3px; }}
    .signal-card p {{ font-size: 12.5px; color: var(--muted); }}

    /* Top 50 Leaderboard Section */
    .leaderboard-sec {{
      padding: 28px 0; border-bottom: 2px solid var(--rule);
    }}
    .lb-header {{
      display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;
    }}
    .lb-header h2 {{
      font-family: 'Space Grotesk', sans-serif; font-size: clamp(22px, 2.5vw, 30px); font-weight: 700;
    }}
    .top3-strip {{
      font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted);
      background: var(--card); border: 1px solid var(--border); border-radius: 10px;
      padding: 10px 14px; margin-bottom: 14px;
    }}
    .controls-bar {{
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;
    }}
    .tabs {{ display: flex; gap: 7px; flex-wrap: wrap; }}
    .tab-btn {{
      background: var(--card); color: var(--muted); border: 1px solid var(--border);
      padding: 7px 12px; border-radius: 8px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
    }}
    .tab-btn.active {{ background: var(--blue); color: #fff; border-color: var(--accent); }}
    .search-input {{
      background: var(--card); color: var(--text); border: 1px solid var(--border);
      padding: 8px 14px; border-radius: 8px; font-size: 13px; min-width: 240px; outline: none;
    }}
    .search-input:focus {{ border-color: var(--accent); }}

    .table-wrap {{
      overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--card);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{
      text-align: left; padding: 11px 14px;
      font-family: 'JetBrains Mono', monospace; font-size: 10.5px; text-transform: uppercase;
      color: var(--muted); border-bottom: 1px solid var(--border); background: rgba(10,108,255,0.06);
    }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    .col-pos {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent); width: 54px; }}
    .model-link {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 14px; display: block; }}
    .creator-sub {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--muted); }}
    .score-wrap {{ display: flex; align-items: center; gap: 10px; min-width: 145px; }}
    .score-wrap strong {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; width: 46px; }}
    .score-bar {{ flex: 1; height: 7px; border-radius: 99px; background: rgba(148,163,184,0.2); overflow: hidden; }}
    .score-fill {{ height: 100%; border-radius: 99px; background: linear-gradient(90deg, #0A6CFF, #38BDF8, #10B981); }}
    .pill-open {{
      font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;
      color: #10B981; background: rgba(16,185,129,0.14); padding: 3px 8px; border-radius: 6px; white-space: nowrap;
    }}
    .pill-cloud {{
      font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;
      color: #38BDF8; background: rgba(56,189,248,0.12); padding: 3px 8px; border-radius: 6px; white-space: nowrap;
    }}
    .mono-cell {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); white-space: nowrap; }}

    /* News Grid */
    .news-sec {{ padding-top: 26px; }}
    .news-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    @media (max-width: 1000px) {{ .news-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 650px) {{ .news-grid {{ grid-template-columns: 1fr; }} }}
    .news-row {{
      background: var(--card); border: 1px solid var(--border); border-radius: 10px;
      padding: 14px 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 10px;
    }}
    .news-meta {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 6px; }}
    .src-pill {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; color: var(--accent); text-transform: uppercase; }}
    .news-date {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }}
    .news-row h4 {{ font-family: 'Space Grotesk', sans-serif; font-size: 14.5px; font-weight: 700; line-height: 1.3; margin-bottom: 6px; }}
    .news-row p {{ font-size: 12.5px; color: var(--muted); }}
    .src-go {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: var(--accent); }}
  </style>
</head>
<body>
  <div class="newspaper">
    <div class="top-utility">
      <span class="verified-pill">🛡️ 100% FONTES OFICIAIS VERIFICADAS · ZERO INVENÇÕES</span>
      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <span>Fontes online: <strong>{ok_sources}/{total_sources}</strong> · Atualizado automaticamente na nuvem</span>
        <button class="theme-btn" onclick="document.body.classList.toggle('paper-mode')">☀️ Papel NYT / 🌙 Dark CK</button>
      </div>
    </div>

    <header class="masthead">
      <h1>The CK AI Times</h1>
      <div class="masthead-sub">Radar Diário de Inteligência Artificial, Modelos de Linguagem &amp; Indústria · CK Intelligence</div>
    </header>

    <div class="dateline">
      <span>DATA DA EDIÇÃO: {esc(d_str)}</span>
      <span>ÚLTIMA COLETA AUTOMÁTICA: {esc(raw.get('generated_at', ''))}</span>
      <span>{raw.get('total_items', 0)} NOTÍCIAS REAIS · TOP {len(top50)} MODELOS RANQUEADOS</span>
    </div>

    <nav class="quick-nav">
      <a href="#capa">📰 Manchetes de Hoje</a>
      <a href="#ranking-top50" class="highlight">🏆 Ranking Top 50 Modelos (Neon, GPT, Claude, Open-Source)</a>
      <a href="#cadernos">📚 Todos os 4 Cadernos ({raw.get('total_items', 0)} links)</a>
    </nav>

    <!-- CAPA FACTUAL -->
    <section id="capa" class="front-page">
      <div class="lead-box">
        <div class="lead-kicker">● DESTAQUE DIRETO DA FONTE · {esc(lead.get('source'))} ({esc(lead.get('date'))})</div>
        <h2><a href="{esc(lead.get('url'))}" target="_blank" rel="noopener noreferrer">{esc(lead.get('title'))}</a></h2>
        <p class="lead-deck">{esc(lead.get('summary') or 'Matéria original capturada diretamente do feed oficial sem alteração editorial.')}</p>
        <a class="cta-src" href="{esc(lead.get('url'))}" target="_blank" rel="noopener noreferrer">
          Ler matéria original na íntegra ↗
        </a>
      </div>

      <div class="signals-col">
        <div class="section-kicker">📡 PRINCIPAIS LANÇAMENTOS &amp; MOVIMENTOS DE HOJE (LINKS DIRETOS)</div>
        {''.join(side_html)}
      </div>
    </section>

    <!-- RANKING MUNDIAL TOP 50 MODELOS DE IA -->
    <section id="ranking-top50" class="leaderboard-sec">
      <div class="lb-header">
        <div>
          <div class="section-kicker">📊 DADOS OFICIAIS AO VIVO · FONTE: ARTIFICIAL ANALYSIS INTELLIGENCE INDEX</div>
          <h2>🏆 Ranking Mundial Top 50 Modelos de Linguagem (LLMs)</h2>
        </div>
        <a href="{esc(rankings.get('source_url', 'https://artificialanalysis.ai/leaderboards/models'))}" target="_blank" rel="noopener noreferrer" style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:var(--accent); font-weight:700;">
          Verificar fonte oficial Artificial Analysis ↗
        </a>
      </div>

      <div class="top3-strip">
        🥇 Pódio Atual ({rankings.get('total_evaluated', 0)} modelos avaliados): {top3_strip}
      </div>

      <div class="controls-bar">
        <div class="tabs">
          <button class="tab-btn active" onclick="filterRank('overall', 'all', this)">🏆 Top 50 Geral</button>
          <button class="tab-btn" onclick="filterRank('opensource', 'all', this)">🔓 Top 20 Open-Source (Local)</button>
          <button class="tab-btn" onclick="filterRank('overall', 'google', this)">🔵 Google (Gemini)</button>
          <button class="tab-btn" onclick="filterRank('overall', 'anthropic', this)">🟠 Anthropic (Claude)</button>
          <button class="tab-btn" onclick="filterRank('overall', 'openai', this)">🟢 OpenAI (GPT)</button>
        </div>
        <input type="text" id="rankSearch" class="search-input" placeholder="Buscar modelo (ex: Neon, Argon, Hydrogen, Qwen)..." oninput="applyRankFilters()" />
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pos</th>
              <th>Modelo &amp; Laboratório</th>
              <th>Intelligence Index</th>
              <th>Tipo</th>
              <th>Contexto</th>
              <th>Preço / 1M (In / Out)</th>
            </tr>
          </thead>
          <tbody id="rankBody">
            {rank_rows_all}
          </tbody>
        </table>
      </div>
    </section>

    <!-- OS 4 CADERNOS DE NOTÍCIAS -->
    <section id="cadernos" class="news-sec">
      <div class="section-kicker">📚 TODOS OS 4 CADERNOS DA EDIÇÃO DE HOJE (100% LINKS OFICIAIS)</div>
      <div class="controls-bar" style="margin-top:10px;">
        <div class="tabs">
          <button class="tab-btn active" onclick="filterNews('all', this)">Todos ({len(items)})</button>
          <button class="tab-btn" onclick="filterNews('newsletters', this)">📰 Newsletters &amp; BR</button>
          <button class="tab-btn" onclick="filterNews('labs', this)">🚀 Big Techs &amp; Labs</button>
          <button class="tab-btn" onclick="filterNews('tempo_real', this)">🛠️ Hugging Face &amp; GitHub</button>
          <button class="tab-btn" onclick="filterNews('industria', this)">🏭 Indústria, YOLO &amp; n8n</button>
        </div>
        <input type="text" id="newsSearch" class="search-input" placeholder="Filtrar notícias (ex: Neon, IPO, YOLO, n8n)..." oninput="applyNewsFilters()" />
      </div>
      <div class="news-grid" id="newsGrid">
        {''.join(items_html)}
      </div>
    </section>
  </div>

  <script>
    let activeRankList = 'overall';
    let activeRankCreator = 'all';
    let activeNewsSec = 'all';

    function filterRank(listKey, creator, btn) {{
      activeRankList = listKey;
      activeRankCreator = creator;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyRankFilters();
    }}

    function applyRankFilters() {{
      const q = (document.getElementById('rankSearch').value || '').toLowerCase().trim();
      document.querySelectorAll('.rank-row').forEach(row => {{
        const matchList = row.getAttribute('data-list') === activeRankList;
        const matchCreator = activeRankCreator === 'all' || row.getAttribute('data-creator').includes(activeRankCreator);
        const matchQ = !q || row.getAttribute('data-name').includes(q);
        row.style.display = (matchList && matchCreator && matchQ) ? '' : 'none';
      }});
    }}

    function filterNews(sec, btn) {{
      activeNewsSec = sec;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyNewsFilters();
    }}

    function applyNewsFilters() {{
      const q = (document.getElementById('newsSearch').value || '').toLowerCase().trim();
      document.querySelectorAll('.news-row').forEach(row => {{
        const matchSec = activeNewsSec === 'all' || row.getAttribute('data-sec') === activeNewsSec;
        const matchQ = !q || row.getAttribute('data-search').includes(q);
        row.style.display = (matchSec && matchQ) ? 'flex' : 'none';
      }});
    }}

    applyRankFilters();
  </script>
</body>
</html>'''

    index_out = os.path.join(BASE_DIR, 'index.html')
    latest_out = os.path.join(BASE_DIR, 'ultima-edicao.html')
    for p in (index_out, latest_out):
        with open(p, 'w', encoding='utf-8') as f:
            f.write(doc)
    print(f"[CK AI TIMES] index.html e ultima-edicao.html gerados com sucesso ({len(items)} notícias + Top {len(top50)} LLMs)!")

if __name__ == '__main__':
    build_newspaper()
