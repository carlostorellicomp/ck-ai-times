# -*- coding: utf-8 -*-
"""
THE CK AI TIMES — Gerador Editorial Bilíngue 100% Factual (Zero Invenções)
Gera index.html (GitHub Pages) + ultima-edicao.html com:
- Tradução literal PT-BR + Modo Bilíngue (PT + EN para treinar inglês)
- Parágrafos completos na Capa (zero espaço vazio) + Leitor de Matéria Completa em Modal
- Ranking Mundial Top 50 Modelos de Linguagem (Artificial Analysis)
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

    # Garante índice único para o leitor modal
    for i, it in enumerate(items):
        it['_idx'] = i

    # Seleciona os destaques reais de capa dando preferência a matérias com texto completo rico
    priority_sources = [
        'The Rundown AI', 'NVIDIA Industrial & AI', 'OpenAI News', 'Anthropic News (Claude)',
        'Google AI / DeepMind', 'n8n (Automação & Orquestração)', 'TLDR AI',
        'One Useful Thing (Ethan Mollick)', 'Microsoft Copilot & Azure AI'
    ]
    front_picks = []
    used_urls = set()
    for psrc in priority_sources:
        # Prioriza item da fonte que tenha parágrafos completos
        candidates = [it for it in items if it.get('source') == psrc and it.get('url') not in used_urls]
        candidates.sort(key=lambda x: len(x.get('full_paragraphs_pt') or []), reverse=True)
        if candidates:
            front_picks.append(candidates[0])
            used_urls.add(candidates[0].get('url'))
        if len(front_picks) >= 7:
            break
    if len(front_picks) < 7:
        for it in items:
            if it.get('url') not in used_urls:
                front_picks.append(it)
                used_urls.add(it.get('url'))
            if len(front_picks) >= 7:
                break

    lead = front_picks[0] if front_picks else {'_idx': 0, 'source': 'CK AI Times', 'title': '', 'title_pt': '', 'summary': '', 'summary_pt': '', 'url': '#', 'date': d_str, 'full_paragraphs': [], 'full_paragraphs_pt': []}
    sub_lead = front_picks[1] if len(front_picks) > 1 else None
    side_picks = front_picks[2:7]

    def render_lead_paragraphs(item, max_p=3):
        pts = item.get('full_paragraphs_pt') or []
        ens = item.get('full_paragraphs') or []
        if not pts:
            return f'''
            <p class="lang-pt lead-para">{esc(item.get('summary_pt') or item.get('summary'))}</p>
            <p class="lang-en lead-para en-sub">{esc(item.get('summary'))}</p>'''
        blocks = []
        for idx in range(min(max_p, len(pts))):
            en_txt = ens[idx] if idx < len(ens) else ''
            blocks.append(f'''
            <p class="lang-pt lead-para">{esc(pts[idx])}</p>
            <p class="lang-en lead-para en-sub">{esc(en_txt)}</p>''')
        return ''.join(blocks)

    sub_lead_html = ''
    if sub_lead:
        has_full_sub = len(sub_lead.get('full_paragraphs_pt') or []) >= 2
        btn_sub_read = f'<button class="btn-reader" onclick="openReader({sub_lead["_idx"]})">📖 Ler matéria completa aqui</button>' if has_full_sub else ''
        sub_lead_html = f'''
        <div class="sub-lead-box">
          <div class="lead-kicker" style="color:var(--accent);">● SEGUNDO DESTAQUE DO DIA · {esc(sub_lead.get('source'))} ({esc(sub_lead.get('date'))})</div>
          <h3>
            <a href="{esc(sub_lead.get('url'))}" target="_blank" rel="noopener noreferrer">
              <span class="lang-pt">{esc(sub_lead.get('title_pt') or sub_lead.get('title'))}</span>
              <span class="lang-en en-title">{esc(sub_lead.get('title'))}</span>
            </a>
          </h3>
          {render_lead_paragraphs(sub_lead, max_p=2)}
          <div class="lead-actions">
            {btn_sub_read}
            <a class="cta-ghost" href="{esc(sub_lead.get('url'))}" target="_blank" rel="noopener noreferrer">Abrir fonte original ↗</a>
          </div>
        </div>'''

    side_html = []
    for s in side_picks:
        has_full = len(s.get('full_paragraphs_pt') or []) >= 2
        read_btn = f'<button class="mini-reader-btn" onclick="openReader({s["_idx"]})">📖 Ler resumo completo</button>' if has_full else ''
        side_html.append(f'''
        <article class="signal-card">
          <div class="signal-tag">{esc(s.get('source'))} · {esc(s.get('date'))}</div>
          <h3>
            <a href="{esc(s.get('url'))}" target="_blank" rel="noopener noreferrer">
              <span class="lang-pt">{esc(s.get('title_pt') or s.get('title'))}</span>
              <span class="lang-en en-title">{esc(s.get('title'))}</span>
            </a>
          </h3>
          <p class="lang-pt">{esc(s.get('summary_pt') or s.get('summary') or 'Clique para ler a matéria original.')}</p>
          <p class="lang-en en-sub">{esc(s.get('summary') or '')}</p>
          <div class="mini-actions">
            {read_btn}
            <a class="src-go" href="{esc(s.get('url'))}" target="_blank" rel="noopener noreferrer">Fonte original ↗</a>
          </div>
        </article>''')

    # Ranking Top 50 + Top 20 Open-Source
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

    # Cards dos 4 cadernos
    items_html = []
    for it in items:
        sec = it.get('section', 'newsletters')
        search_blob = (it.get('title', '') + ' ' + it.get('title_pt', '') + ' ' + it.get('source', '') + ' ' + it.get('summary_pt', '')).lower()
        has_full = len(it.get('full_paragraphs_pt') or []) >= 2
        btn_full = f'<button class="mini-reader-btn" onclick="openReader({it["_idx"]})">📖 Ler matéria ({len(it.get("full_paragraphs_pt") or [])} parág.)</button>' if has_full else ''
        items_html.append(f'''
        <article class="news-row" data-sec="{esc(sec)}" data-search="{esc(search_blob)}">
          <div>
            <div class="news-meta">
              <span class="src-pill">{esc(it.get('source'))}</span>
              <span class="news-date">{esc(it.get('date'))}</span>
            </div>
            <h4>
              <a href="{esc(it.get('url'))}" target="_blank" rel="noopener noreferrer">
                <span class="lang-pt">{esc(it.get('title_pt') or it.get('title'))}</span>
                <span class="lang-en en-title">{esc(it.get('title'))}</span>
              </a>
            </h4>
            <p class="lang-pt">{esc(it.get('summary_pt') or it.get('summary') or 'Abrir matéria original na fonte.')}</p>
            <p class="lang-en en-sub">{esc(it.get('summary') or '')}</p>
          </div>
          <div class="mini-actions">
            {btn_full}
            <a class="src-go" href="{esc(it.get('url'))}" target="_blank" rel="noopener noreferrer">Fonte original ↗</a>
          </div>
        </article>''')

    # Prepara payload leve em JS para o Leitor Modal
    reader_payload = [
        {
            'source': it.get('source', ''),
            'date': it.get('date', ''),
            'url': it.get('url', '#'),
            'title_pt': it.get('title_pt') or it.get('title', ''),
            'title_en': it.get('title', ''),
            'paras_pt': it.get('full_paragraphs_pt') or [it.get('summary_pt') or it.get('summary') or ''],
            'paras_en': it.get('full_paragraphs') or [it.get('summary') or '']
        }
        for it in items
    ]
    reader_json = json.dumps(reader_payload, ensure_ascii=False).replace('</', '<\\/')

    ok_sources = sum(1 for v in raw.get('sources_status', {}).values() if v.startswith('OK'))
    total_sources = len(raw.get('sources_status', {}))
    top3_strip = ' · '.join(
        f"<strong>#{i}</strong> {esc(m['name'])} ({m['intelligence_index']:.1f})"
        for i, m in enumerate(top50[:3], 1)
    )
    has_lead_full = len(lead.get('full_paragraphs_pt') or []) >= 2
    lead_read_btn = f'<button class="btn-reader primary" onclick="openReader({lead["_idx"]})">📖 Ler matéria completa traduzida aqui</button>' if has_lead_full else ''

    doc = f'''<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The CK AI Times · Edição Diária PT-BR &amp; Ranking Top 50 LLMs | CK Intelligence</title>
  <meta name="description" content="Radar diário 100% factual de Inteligência Artificial em Português e Bilíngue (PT+EN) + Ranking Mundial Top 50 Modelos de Linguagem ao vivo." />
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

    /* Modos de Idioma (PT / Bilíngue PT+EN / EN) */
    body.mode-pt .lang-en {{ display: none !important; }}
    body.mode-en .lang-pt {{ display: none !important; }}
    body.mode-bilingual .lang-en {{
      display: block !important;
      margin-top: 4px;
      padding-left: 10px;
      border-left: 2px solid rgba(56,189,248,0.4);
      opacity: 0.78;
      font-style: italic;
    }}
    body.mode-bilingual .en-title {{ font-size: 0.84em; font-weight: 500; color: var(--muted); }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg); color: var(--text);
      font-family: 'Inter', system-ui, sans-serif;
      line-height: 1.58; padding: 16px 12px 64px 12px;
      transition: background 0.25s, color 0.25s;
    }}
    a {{ color: inherit; text-decoration: none; }}
    a:hover {{ color: var(--accent); text-decoration: underline; }}

    .newspaper {{
      max-width: 1260px; margin: 0 auto;
      background: var(--paper); border: 1px solid var(--border);
      border-radius: 14px; padding: 24px 32px 42px 32px;
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
    .lang-switcher {{ display: inline-flex; gap: 4px; background: var(--card); border: 1px solid var(--border); padding: 3px; border-radius: 999px; }}
    .lang-btn {{
      background: transparent; color: var(--muted); border: none;
      padding: 5px 11px; border-radius: 999px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
    }}
    .lang-btn.active {{ background: var(--blue); color: #fff; }}
    .theme-btn {{
      background: var(--card); color: var(--text); border: 1px solid var(--border);
      padding: 6px 12px; border-radius: 999px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
    }}

    .masthead {{ text-align: center; padding: 18px 0 14px 0; border-bottom: 3px double var(--rule); }}
    .masthead h1 {{ font-family: 'Playfair Display', Georgia, serif; font-size: clamp(32px, 5.2vw, 62px); font-weight: 900; letter-spacing: -0.02em; line-height: 1; }}
    .masthead-sub {{ margin-top: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 0.2em; color: var(--accent); }}
    .dateline {{
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
      padding: 10px 0; border-bottom: 1px solid var(--rule);
      font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted);
    }}

    .quick-nav {{ display: flex; gap: 8px; flex-wrap: wrap; padding: 14px 0; border-bottom: 1px solid var(--border); }}
    .quick-nav a {{ font-family: 'JetBrains Mono', monospace; font-size: 11.5px; font-weight: 700; padding: 6px 13px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); }}
    .quick-nav a.highlight {{ background: var(--blue); color: #fff; border-color: var(--accent); }}

    /* Capa Editorial Rica (Zero espaço vazio) */
    .front-page {{
      display: grid; grid-template-columns: 1.2fr 1fr; gap: 28px;
      padding: 24px 0; border-bottom: 2px solid var(--rule); align-items: start;
    }}
    @media (max-width: 900px) {{ .front-page {{ grid-template-columns: 1fr; }} }}

    .lead-kicker {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: var(--emerald); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px; }}
    .lead-box h2 {{ font-family: 'Playfair Display', Georgia, serif; font-size: clamp(24px, 2.8vw, 36px); font-weight: 800; line-height: 1.15; margin-bottom: 14px; }}
    .lead-para {{ font-size: 15px; line-height: 1.65; color: var(--text); margin-bottom: 11px; opacity: 0.92; }}
    .lead-actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .btn-reader {{
      background: var(--card); color: var(--accent); border: 1px solid rgba(56,189,248,0.45);
      padding: 9px 15px; border-radius: 9px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 11.5px; font-weight: 700;
    }}
    .btn-reader.primary {{ background: var(--blue); color: #fff; border-color: var(--accent); }}
    .cta-ghost {{
      display: inline-flex; align-items: center; gap: 6px;
      background: transparent; color: var(--muted); border: 1px solid var(--border);
      padding: 9px 14px; border-radius: 9px;
      font-family: 'JetBrains Mono', monospace; font-size: 11.5px; font-weight: 700;
    }}

    .sub-lead-box {{
      margin-top: 24px; padding-top: 22px; border-top: 1px solid var(--rule);
    }}
    .sub-lead-box h3 {{
      font-family: 'Playfair Display', Georgia, serif; font-size: 22px; font-weight: 800; line-height: 1.2; margin-bottom: 10px;
    }}

    .signals-col {{ display: flex; flex-direction: column; gap: 14px; border-left: 1px solid var(--border); padding-left: 24px; }}
    @media (max-width: 900px) {{ .signals-col {{ border-left: none; padding-left: 0; border-top: 1px solid var(--border); padding-top: 18px; }} }}
    .section-kicker {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.16em; color: var(--accent); margin-bottom: 4px; }}
    .signal-card {{ padding-bottom: 14px; border-bottom: 1px solid var(--border); }}
    .signal-card:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .signal-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; color: var(--amber); margin-bottom: 4px; }}
    .signal-card h3 {{ font-family: 'Space Grotesk', sans-serif; font-size: 16px; font-weight: 700; line-height: 1.28; margin-bottom: 5px; }}
    .signal-card p {{ font-size: 13px; color: var(--muted); }}

    .mini-actions {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .mini-reader-btn {{
      background: rgba(10,108,255,0.14); color: var(--accent); border: 1px solid rgba(56,189,248,0.35);
      padding: 4px 10px; border-radius: 6px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;
    }}
    .mini-reader-btn:hover {{ background: var(--blue); color: #fff; }}
    .src-go {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: var(--muted); }}

    /* Top 50 Leaderboard */
    .leaderboard-sec {{ padding: 28px 0; border-bottom: 2px solid var(--rule); }}
    .lb-header {{ display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }}
    .lb-header h2 {{ font-family: 'Space Grotesk', sans-serif; font-size: clamp(22px, 2.5vw, 30px); font-weight: 700; }}
    .top3-strip {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; }}
    .controls-bar {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }}
    .tabs {{ display: flex; gap: 7px; flex-wrap: wrap; }}
    .tab-btn {{ background: var(--card); color: var(--muted); border: 1px solid var(--border); padding: 7px 12px; border-radius: 8px; cursor: pointer; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; }}
    .tab-btn.active {{ background: var(--blue); color: #fff; border-color: var(--accent); }}
    .search-input {{ background: var(--card); color: var(--text); border: 1px solid var(--border); padding: 8px 14px; border-radius: 8px; font-size: 13px; min-width: 240px; outline: none; }}
    .search-input:focus {{ border-color: var(--accent); }}

    .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--card); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ text-align: left; padding: 11px 14px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border); background: rgba(10,108,255,0.06); }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    .col-pos {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent); width: 54px; }}
    .model-link {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 14px; display: block; }}
    .creator-sub {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: var(--muted); }}
    .score-wrap {{ display: flex; align-items: center; gap: 10px; min-width: 145px; }}
    .score-wrap strong {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; width: 46px; }}
    .score-bar {{ flex: 1; height: 7px; border-radius: 99px; background: rgba(148,163,184,0.2); overflow: hidden; }}
    .score-fill {{ height: 100%; border-radius: 99px; background: linear-gradient(90deg, #0A6CFF, #38BDF8, #10B981); }}
    .pill-open {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; color: #10B981; background: rgba(16,185,129,0.14); padding: 3px 8px; border-radius: 6px; white-space: nowrap; }}
    .pill-cloud {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; color: #38BDF8; background: rgba(56,189,248,0.12); padding: 3px 8px; border-radius: 6px; white-space: nowrap; }}
    .mono-cell {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); white-space: nowrap; }}

    /* News Grid */
    .news-sec {{ padding-top: 26px; }}
    .news-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    @media (max-width: 1000px) {{ .news-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 650px) {{ .news-grid {{ grid-template-columns: 1fr; }} }}
    .news-row {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 10px; }}
    .news-meta {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 6px; }}
    .src-pill {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; color: var(--accent); text-transform: uppercase; }}
    .news-date {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }}
    .news-row h4 {{ font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 700; line-height: 1.3; margin-bottom: 6px; }}
    .news-row p {{ font-size: 13px; color: var(--muted); }}

    /* Modal Leitor de Matéria Completa */
    .reader-modal {{
      position: fixed; inset: 0; z-index: 100;
      background: rgba(4, 7, 14, 0.88); backdrop-filter: blur(10px);
      display: none; align-items: center; justify-content: center; padding: 18px;
    }}
    .reader-modal.open {{ display: flex; }}
    .reader-box {{
      width: 100%; max-width: 820px; max-height: 88vh; overflow-y: auto;
      background: var(--paper); border: 1px solid var(--accent);
      border-radius: 16px; padding: 28px 32px; position: relative;
      box-shadow: 0 30px 90px rgba(0,0,0,0.85);
    }}
    .reader-close {{
      position: sticky; top: 0; float: right;
      background: var(--card); color: var(--text); border: 1px solid var(--border);
      padding: 6px 12px; border-radius: 8px; cursor: pointer;
      font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700;
    }}
    .reader-box h2 {{ font-family: 'Playfair Display', Georgia, serif; font-size: 28px; line-height: 1.2; margin: 10px 0 16px 0; clear: both; }}
    .reader-para {{ font-size: 15.5px; line-height: 1.72; margin-bottom: 14px; color: var(--text); }}
    .reader-en {{ font-size: 13.5px; line-height: 1.6; color: var(--muted); margin: -6px 0 16px 0; padding-left: 12px; border-left: 2px solid rgba(56,189,248,0.4); font-style: italic; }}
  </style>
</head>
<body class="mode-pt">
  <div class="newspaper">
    <div class="top-utility">
      <span class="verified-pill">🛡️ 100% FONTES OFICIAIS · TRADUÇÃO LITERAL · ZERO INVENÇÕES</span>
      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <div class="lang-switcher" title="Alternar idioma para ler em Português ou treinar seu Inglês">
          <button class="lang-btn active" data-lang="mode-pt" onclick="setLang('mode-pt')">🇧🇷 Português</button>
          <button class="lang-btn" data-lang="mode-bilingual" onclick="setLang('mode-bilingual')">🔀 PT + EN (Treinar Inglês)</button>
          <button class="lang-btn" data-lang="mode-en" onclick="setLang('mode-en')">🇺🇸 Inglês</button>
        </div>
        <button class="theme-btn" onclick="document.body.classList.toggle('paper-mode')">☀️ Papel NYT / 🌙 Dark</button>
      </div>
    </div>

    <header class="masthead">
      <h1>The CK AI Times</h1>
      <div class="masthead-sub">Radar Diário de Inteligência Artificial, Modelos de Linguagem &amp; Indústria · CK Intelligence</div>
    </header>

    <div class="dateline">
      <span>DATA: {esc(d_str)} · FONTES ONLINE: {ok_sources}/{total_sources}</span>
      <span>ATUALIZADO NA NUVEM: {esc(raw.get('generated_at', ''))}</span>
      <span>{raw.get('total_items', 0)} MATÉRIAS TRADUZIDAS · TOP {len(top50)} MODELOS</span>
    </div>

    <nav class="quick-nav">
      <a href="#capa">📰 Capa &amp; Resumos PT-BR</a>
      <a href="#ranking-top50" class="highlight">🏆 Ranking Top 50 Modelos (Neon, GPT, Claude, Open-Source)</a>
      <a href="#cadernos">📚 Todos os 4 Cadernos ({raw.get('total_items', 0)} matérias)</a>
    </nav>

    <!-- CAPA RICA COM PARÁGRAFOS REAIS TRADUZIDOS -->
    <section id="capa" class="front-page">
      <div class="lead-box">
        <div class="lead-kicker">● MANCHETE PRINCIPAL · {esc(lead.get('source'))} ({esc(lead.get('date'))})</div>
        <h2>
          <a href="{esc(lead.get('url'))}" target="_blank" rel="noopener noreferrer">
            <span class="lang-pt">{esc(lead.get('title_pt') or lead.get('title'))}</span>
            <span class="lang-en en-title">{esc(lead.get('title'))}</span>
          </a>
        </h2>
        {render_lead_paragraphs(lead, max_p=3)}
        <div class="lead-actions">
          {lead_read_btn}
          <a class="cta-ghost" href="{esc(lead.get('url'))}" target="_blank" rel="noopener noreferrer">Abrir fonte original ↗</a>
        </div>

        {sub_lead_html}
      </div>

      <div class="signals-col">
        <div class="section-kicker">📡 PRINCIPAIS NOTÍCIAS DE HOJE (TRADUZIDAS PARA PT-BR)</div>
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
        <input type="text" id="rankSearch" class="search-input" placeholder="Buscar modelo (ex: Neon, Carbon, Hydrogen, Qwen)..." oninput="applyRankFilters()" />
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
      <div class="section-kicker">📚 TODOS OS 4 CADERNOS DA EDIÇÃO DE HOJE (TRADUZIDOS + LINKS OFICIAIS)</div>
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

  <!-- MODAL LEITOR DE MATÉRIA COMPLETA -->
  <div id="readerModal" class="reader-modal" onclick="if(event.target===this) closeReader()">
    <div class="reader-box">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:12px;">
        <div class="lang-switcher" title="Alternar idioma durante a leitura">
          <button class="lang-btn active" data-lang="mode-pt" onclick="setLang('mode-pt')">🇧🇷 PT</button>
          <button class="lang-btn" data-lang="mode-bilingual" onclick="setLang('mode-bilingual')">🔀 PT + EN</button>
          <button class="lang-btn" data-lang="mode-en" onclick="setLang('mode-en')">🇺🇸 EN</button>
        </div>
        <button class="reader-close" style="position:static; float:none;" onclick="closeReader()">✕ Fechar (ESC)</button>
      </div>
      <div id="rMeta" class="lead-kicker"></div>
      <h2 id="rTitle"></h2>
      <div id="rBody"></div>
      <div style="margin-top:20px; padding-top:14px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <a id="rLink" href="#" target="_blank" rel="noopener noreferrer" class="btn-reader primary">Abrir matéria completa no site original ↗</a>
        <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--muted);">Tradução literal automática · Zero invenções</span>
      </div>
    </div>
  </div>

  <script>
    const READER_ITEMS = {reader_json};
    let activeLang = 'mode-pt';
    let activeRankList = 'overall';
    let activeRankCreator = 'all';
    let activeNewsSec = 'all';

    function setLang(mode) {{
      activeLang = mode;
      document.body.classList.remove('mode-pt', 'mode-bilingual', 'mode-en');
      document.body.classList.add(mode);
      document.querySelectorAll('.lang-btn[data-lang]').forEach(b => {{
        b.classList.toggle('active', b.getAttribute('data-lang') === mode);
      }});
    }}

    function openReader(idx) {{
      const it = READER_ITEMS[idx];
      if (!it) return;
      document.getElementById('rMeta').textContent = `${{it.source}} · ${{it.date}}`;
      document.getElementById('rTitle').innerHTML =
        `<span class="lang-pt">${{escHtml(it.title_pt)}}</span><span class="lang-en en-title">${{escHtml(it.title_en)}}</span>`;
      const pts = it.paras_pt || [];
      const ens = it.paras_en || [];
      const maxLen = Math.max(pts.length, ens.length);
      let html = '';
      for (let i = 0; i < maxLen; i++) {{
        if (pts[i]) html += `<p class="reader-para lang-pt">${{escHtml(pts[i])}}</p>`;
        if (ens[i]) html += `<p class="reader-en lang-en">${{escHtml(ens[i])}}</p>`;
      }}
      document.getElementById('rBody').innerHTML = html;
      document.getElementById('rLink').href = it.url;
      document.getElementById('readerModal').classList.add('open');
    }}

    function closeReader() {{
      document.getElementById('readerModal').classList.remove('open');
    }}

    function escHtml(str) {{
      return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeReader();
    }});

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
    print(f"[CK AI TIMES] index.html bilíngue PT/EN gerado com sucesso ({len(items)} matérias + Top {len(top50)} LLMs)!")

if __name__ == '__main__':
    build_newspaper()
