# -*- coding: utf-8 -*-
"""
THE CK AI TIMES — Coletor 100% Factual (Zero Invenções · Zero Dependências Externas)
Roda tanto localmente no Windows quanto na nuvem via GitHub Actions.
Fontes: 20 feeds reais de notícias/tech + Ranking Mundial Top 50 LLMs (Artificial Analysis).
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
import os
import html
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dados')
os.makedirs(DATA_DIR, exist_ok=True)

BRT = timezone(timedelta(hours=-3))
NOW_BRT = datetime.now(BRT)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 CKAITimes/2.0'
}

def clean_text(text, max_len=240):
    if not text:
        return ''
    text = html.unescape(str(text))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_len:
        return text[:max_len - 1].rsplit(' ', 1)[0] + '…'
    return text

def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_rss(name, section, url, limit=5):
    items = []
    raw = fetch_url(url)
    raw = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9a-fA-F]+;)', '&amp;', raw)
    root = ET.fromstring(raw.encode('utf-8'))
    entries = root.findall('.//item')
    is_atom = False
    if not entries:
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('.//a:entry', ns)
        is_atom = True

    for e in entries[:limit]:
        if not is_atom:
            title = clean_text(e.findtext('title') or '', 170)
            link = (e.findtext('link') or '').strip()
            pub = (e.findtext('pubDate') or e.findtext('{http://purl.org/dc/elements/1.1/}date') or '').strip()
            desc = clean_text(e.findtext('description') or '', 220)
        else:
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            title = clean_text(e.findtext('a:title', default='', namespaces=ns), 170)
            link_el = e.find('a:link', ns)
            link = link_el.attrib.get('href', '') if link_el is not None else ''
            pub = (e.findtext('a:updated', default='', namespaces=ns) or e.findtext('a:published', default='', namespaces=ns)).strip()
            desc = clean_text(e.findtext('a:summary', default='', namespaces=ns) or e.findtext('a:content', default='', namespaces=ns), 220)
        if title and link:
            items.append({
                'source': name,
                'section': section,
                'title': title,
                'url': link,
                'date': pub[:25],
                'summary': desc
            })
    return items

def parse_huggingface_models(limit=6):
    raw = fetch_url('https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=' + str(limit))
    data = json.loads(raw)
    items = []
    for m in data[:limit]:
        mid = m.get('id', '')
        tag = m.get('pipeline_tag', 'open-source')
        likes = m.get('likes', 0)
        dl = m.get('downloads', 0)
        items.append({
            'source': 'Hugging Face Models',
            'section': 'tempo_real',
            'title': f"{mid} ({tag})",
            'url': f"https://huggingface.co/{mid}",
            'date': 'Trending',
            'summary': f"Em alta no Hugging Face · {likes:,} likes · {dl:,} downloads/mês."
        })
    return items

def parse_huggingface_spaces(limit=4):
    raw = fetch_url('https://huggingface.co/api/spaces?sort=trendingScore&direction=-1&limit=' + str(limit))
    data = json.loads(raw)
    items = []
    for s in data[:limit]:
        sid = s.get('id', '')
        likes = s.get('likes', 0)
        sdk = s.get('sdk', 'app')
        items.append({
            'source': 'Hugging Face Spaces',
            'section': 'tempo_real',
            'title': f"Space: {sid}",
            'url': f"https://huggingface.co/spaces/{sid}",
            'date': 'Trending',
            'summary': f"Demo interativa em alta ({sdk}) · {likes:,} likes."
        })
    return items

def parse_github_trending(lang, limit=5):
    raw = fetch_url(f'https://github.com/trending/{lang}?since=daily')
    items = []
    articles = re.findall(r'<article class="Box-row">(.*?)</article>', raw, re.DOTALL)
    for art in articles[:limit]:
        m_repo = re.search(r'<h2[^>]*>.*?href="(/[^"]+)"', art, re.DOTALL)
        m_desc = re.search(r'<p class="col-9[^"]*">(.*?)</p>', art, re.DOTALL)
        m_stars = re.search(r'([\d,]+)\s+stars today', art)
        if m_repo:
            repo_path = m_repo.group(1).strip()
            repo_name = repo_path.lstrip('/')
            desc = clean_text(m_desc.group(1) if m_desc else '', 200)
            stars = m_stars.group(1) if m_stars else '—'
            items.append({
                'source': f'GitHub Trending ({lang.capitalize()})',
                'section': 'tempo_real',
                'title': f"{repo_name} (+{stars} ⭐ hoje)",
                'url': f"https://github.com{repo_path}",
                'date': 'Trending',
                'summary': desc or 'Repositório open-source em alta hoje.'
            })
    return items

def parse_hackernews_ai(limit=5):
    raw = fetch_url('https://hn.algolia.com/api/v1/search_by_date?query=AI+LLM+agent&tags=story&numericFilters=points>50&hitsPerPage=' + str(limit))
    data = json.loads(raw)
    items = []
    for h in data.get('hits', [])[:limit]:
        title = clean_text(h.get('title', ''), 160)
        url = h.get('url') or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        pts = h.get('points', 0)
        comments = h.get('num_comments', 0)
        items.append({
            'source': 'Hacker News (Engenharia IA)',
            'section': 'labs',
            'title': title,
            'url': url,
            'date': (h.get('created_at') or '')[:10],
            'summary': f"{pts} pontos · {comments} comentários na comunidade técnica."
        })
    return items

def parse_the_batch(limit=4):
    raw = fetch_url('https://www.deeplearning.ai/the-batch/')
    items = []
    matches = re.findall(r'href="(/the-batch/[^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>', raw, re.DOTALL)
    seen = set()
    for path, title_html in matches:
        title = clean_text(title_html, 150)
        if title and path not in seen and len(title) > 12 and title.lower() != 'popular articles':
            seen.add(path)
            items.append({
                'source': 'The Batch (Andrew Ng)',
                'section': 'newsletters',
                'title': title,
                'url': 'https://www.deeplearning.ai' + path,
                'date': 'Semanal',
                'summary': 'Curadoria técnica da DeepLearning.AI (Andrew Ng).'
            })
            if len(items) >= limit:
                break
    return items

def parse_ultralytics(limit=4):
    raw = fetch_url('https://www.ultralytics.com/blog')
    items = []
    matches = re.findall(r'href="(/blog/([a-z0-9-]+))"', raw)
    seen = set()
    for path, slug in matches:
        if path not in seen and len(slug) > 8 and slug not in ('category', 'author', 'page'):
            seen.add(path)
            title = slug.replace('-', ' ').title()
            items.append({
                'source': 'Ultralytics (YOLO / Visão Industrial)',
                'section': 'industria',
                'title': title,
                'url': 'https://www.ultralytics.com' + path,
                'date': 'Recente',
                'summary': 'Blog oficial Ultralytics (YOLO, visão computacional e edge AI).'
            })
            if len(items) >= limit:
                break
    return items

def parse_anthropic(limit=4):
    raw = fetch_url('https://www.anthropic.com/news')
    items = []
    matches = re.findall(r'href="(/news/[^"]+)"[^>]*>(.*?)</a>', raw, re.DOTALL)
    seen = set()
    for path, inner in matches:
        title = clean_text(inner, 150)
        if title and path not in seen and len(title) > 15:
            seen.add(path)
            items.append({
                'source': 'Anthropic News (Claude)',
                'section': 'labs',
                'title': title,
                'url': 'https://www.anthropic.com' + path,
                'date': 'Oficial',
                'summary': 'Comunicado oficial publicado em anthropic.com/news.'
            })
            if len(items) >= limit:
                break
    return items

def fetch_artificial_analysis_rankings():
    """
    Coleta 100% REAL (zero invenções) do Artificial Analysis Leaderboard:
    - Top 50 Mundial (por Intelligence Index)
    - Top 20 Open-Source / Open-Weights (para rodar local/on-premise)
    """
    raw = fetch_url('https://artificialanalysis.ai/leaderboards/models', timeout=20)
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.DOTALL)
    ff = ''
    for c in chunks:
        try:
            ff += json.loads('"' + c + '"')
        except Exception:
            pass

    decoder = json.JSONDecoder()
    models = []
    seen_ids = set()
    pos = 0
    while True:
        idx = ff.find('"modelCreatorName":', pos)
        if idx == -1:
            break
        start = ff.rfind('{"id":', max(0, idx - 800), idx)
        if start != -1:
            try:
                obj, _ = decoder.raw_decode(ff, start)
                mid = obj.get('id')
                score = obj.get('intelligenceIndex')
                if mid and mid not in seen_ids and isinstance(score, (int, float)) and not obj.get('deprecated'):
                    seen_ids.add(mid)
                    slug = (obj.get('release') or {}).get('slug', '')
                    models.append({
                        'name': obj.get('shortName') or obj.get('name'),
                        'creator': obj.get('modelCreatorName'),
                        'intelligence_index': round(float(score), 2),
                        'is_open_weights': bool(obj.get('isOpenWeights')),
                        'is_reasoning': bool(obj.get('isReasoning')),
                        'context_window': obj.get('contextWindowTokens'),
                        'price_in': obj.get('price1mInputTokens'),
                        'price_out': obj.get('price1mOutputTokens'),
                        'url': f'https://artificialanalysis.ai/models/{slug}' if slug else 'https://artificialanalysis.ai/leaderboards/models'
                    })
            except Exception:
                pass
        pos = idx + 20

    models.sort(key=lambda x: x['intelligence_index'], reverse=True)
    top50 = models[:50]
    top20_open = [m for m in models if m['is_open_weights']][:20]
    return {
        'source_name': 'Artificial Analysis — Intelligence Index (Oficial)',
        'source_url': 'https://artificialanalysis.ai/leaderboards/models',
        'total_evaluated': len(models),
        'top50_overall': top50,
        'top20_open_source': top20_open
    }

def collect_all():
    tasks = [
        ('TLDR AI', lambda: parse_rss('TLDR AI', 'newsletters', 'https://tldr.tech/api/rss/ai', 5)),
        ('The Rundown AI', lambda: parse_rss('The Rundown AI', 'newsletters', 'https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml', 4)),
        ('One Useful Thing (Ethan Mollick)', lambda: parse_rss('One Useful Thing (Ethan Mollick)', 'newsletters', 'https://www.oneusefulthing.org/feed', 3)),
        ('The Batch (Andrew Ng)', lambda: parse_the_batch(4)),
        ('Mercado IA Brasil', lambda: parse_rss('Radar IA Brasil (Empresas & Indústria)', 'newsletters', 'https://news.google.com/rss/search?q=inteligencia+artificial+empresas+industria+OR+%22AI+Drop%22&hl=pt-BR&gl=BR&ceid=BR:pt-419', 5)),
        ('OpenAI News', lambda: parse_rss('OpenAI News', 'labs', 'https://openai.com/news/rss.xml', 4)),
        ('Anthropic News (Claude)', lambda: parse_anthropic(4)),
        ('Google AI Blog', lambda: parse_rss('Google AI / DeepMind', 'labs', 'https://blog.google/technology/ai/rss/', 4)),
        ('Microsoft Copilot & Azure AI', lambda: parse_rss('Microsoft Copilot & Azure AI', 'labs', 'https://news.google.com/rss/search?q=%22Copilot+Studio%22+OR+%22Azure+AI%22+enterprise&hl=en-US&gl=US&ceid=US:en', 4)),
        ('Hacker News AI', lambda: parse_hackernews_ai(5)),
        ('Hugging Face Models', lambda: parse_huggingface_models(6)),
        ('Hugging Face Spaces', lambda: parse_huggingface_spaces(4)),
        ('GitHub Trending Python', lambda: parse_github_trending('python', 5)),
        ('GitHub Trending TypeScript', lambda: parse_github_trending('typescript', 4)),
        ('LocalLLaMA & Open Source', lambda: parse_rss('LocalLLaMA / Open-Source', 'tempo_real', 'https://news.google.com/rss/search?q=site:reddit.com/r/LocalLLaMA+OR+%22open+source+LLM%22&hl=en-US&gl=US&ceid=US:en', 4)),
        ('NVIDIA Blog', lambda: parse_rss('NVIDIA Industrial & AI', 'industria', 'https://blogs.nvidia.com/feed/', 4)),
        ('NVIDIA Developer Blog', lambda: parse_rss('NVIDIA Developer (Jetson/Omniverse)', 'industria', 'https://developer.nvidia.com/blog/feed/', 4)),
        ('Ultralytics Blog', lambda: parse_ultralytics(4)),
        ('n8n Blog', lambda: parse_rss('n8n (Automação & Orquestração)', 'industria', 'https://blog.n8n.io/rss/', 4)),
        ('LangChain / LangGraph', lambda: parse_rss('LangChain / LangGraph', 'industria', 'https://news.google.com/rss/search?q=LangGraph+OR+LangChain+agents&hl=en-US&gl=US&ceid=US:en', 4)),
    ]

    results = []
    status_report = {}

    with ThreadPoolExecutor(max_workers=10) as ex:
        fut_map = {ex.submit(fn): name for name, fn in tasks}
        for fut in as_completed(fut_map):
            name = fut_map[fut]
            try:
                items = fut.result()
                results.extend(items)
                status_report[name] = f"OK ({len(items)} itens)"
            except Exception as e:
                status_report[name] = f"ERRO: {str(e)[:80]}"

    # Coleta do Ranking Mundial Top 50 (Artificial Analysis)
    rankings = {'source_name': 'Artificial Analysis', 'source_url': 'https://artificialanalysis.ai/leaderboards/models', 'total_evaluated': 0, 'top50_overall': [], 'top20_open_source': []}
    try:
        rankings = fetch_artificial_analysis_rankings()
        status_report['Ranking Top 50 LLMs (Artificial Analysis)'] = f"OK ({len(rankings['top50_overall'])} Top50 / {len(rankings['top20_open_source'])} Open)"
    except Exception as e:
        status_report['Ranking Top 50 LLMs (Artificial Analysis)'] = f"ERRO: {str(e)[:80]}"

    today_str = NOW_BRT.strftime('%Y-%m-%d')
    payload = {
        'generated_at': NOW_BRT.strftime('%d/%m/%Y às %H:%M (BRT)'),
        'date': today_str,
        'total_items': len(results),
        'sources_status': status_report,
        'rankings': rankings,
        'items': results
    }

    out_json = os.path.join(DATA_DIR, f'raw_{today_str}.json')
    latest_json = os.path.join(DATA_DIR, 'latest.json')
    for p in (out_json, latest_json):
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[CK AI TIMES] Coleta concluída: {len(results)} notícias + Top {len(rankings['top50_overall'])} LLMs salvos em {latest_json}")
    for k, v in sorted(status_report.items()):
        print(f"  - {k}: {v}")

if __name__ == '__main__':
    collect_all()
