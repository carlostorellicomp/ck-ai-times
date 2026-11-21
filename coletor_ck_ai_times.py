# -*- coding: utf-8 -*-
"""
THE CK AI TIMES — Coletor 100% Factual com Texto Completo & Tradução Literal PT-BR (Zero Invenções)
Roda localmente no Windows e automaticamente na nuvem via GitHub Actions todo dia às 07:00 BRT.
"""
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import json
import re
import os
import html
import time
import threading
import email.utils
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dados')
os.makedirs(DATA_DIR, exist_ok=True)

BRT = timezone(timedelta(hours=-3))
NOW_BRT = datetime.now(BRT)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 CKAITimes/2.1'
}

def strip_noise_html(raw_html):
    if not raw_html:
        return ''
    s = re.sub(r'<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    return s

def clean_text(text, max_len=None):
    if not text:
        return ''
    text = strip_noise_html(str(text))
    text = html.unescape(text)
    text = re.sub(r'\{\{[^}]+\}\}', '', text)  # remove template placeholders like {{ first_name }}
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r',\s*,+', ',', text).strip()
    if max_len and len(text) > max_len:
        return text[:max_len - 1].rsplit(' ', 1)[0] + '…'
    return text

def extract_paragraphs_from_html(raw_html, max_paragraphs=12, min_len=55):
    s = strip_noise_html(raw_html)
    raw_ps = re.findall(r'<p[^>]*>(.*?)</p>', s, flags=re.DOTALL | re.IGNORECASE)
    paras = []
    seen = set()
    junk_patterns = (
        'read online', 'sign up', 'advertise', 'subscribe', 'cookie', 'privacy policy',
        'terms of service', 'all rights reserved', 'unsubscribe', 'copyright ©', 'share this'
    )
    for p in raw_ps:
        txt = clean_text(p)
        low = txt.lower()
        if len(txt) >= min_len and txt not in seen and not any(j in low for j in junk_patterns):
            seen.add(txt)
            paras.append(txt)
            if len(paras) >= max_paragraphs:
                break
    return paras

def fetch_url(url, timeout=14, retries=2):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            last_err = e
            if attempt + 1 < retries:
                time.sleep(0.6)
    raise last_err

TRANS_LOCK = threading.Lock()
TRANS_STATS = {'cache': 0, 'gtx': 0, 'clients5': 0, 'mymemory': 0, 'fail': 0, 'last_err': ''}
BLOCKED_PROVIDERS = set()

def is_probably_pt(text):
    if not text:
        return True
    pt_markers = (' de ', ' da ', ' do ', ' para ', ' com ', ' uma ', ' inteligência ', ' empresa', ' indústria', 'ção ', 'ões ', ' não ', ' está ', ' sobre ')
    low = ' ' + text.lower() + ' '
    return sum(1 for m in pt_markers if m in low) >= 3

def _split_chunks(text, max_len):
    """Divide texto preservando quebras de parágrafo quando possível."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        cut = remaining.rfind('\n', 0, max_len)
        if cut < max_len // 3:
            cut = remaining.rfind('. ', 0, max_len)
        if cut < max_len // 3:
            cut = remaining.rfind(' ', 0, max_len)
        if cut <= 0:
            cut = max_len
        chunks.append(remaining[:cut + 1].strip())
        remaining = remaining[cut + 1:].strip()
    return [c for c in chunks if c]

def _call_gtx(ch):
    url = 'https://translate.googleapis.com/translate_a/single?' + urllib.parse.urlencode({
        'client': 'gtx', 'sl': 'auto', 'tl': 'pt', 'dt': 't', 'q': ch
    })
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=10).read().decode('utf-8')
    data = json.loads(raw)
    return ''.join(seg[0] for seg in data[0] if seg and seg[0]).strip()

def _call_clients5(ch):
    url = 'https://clients5.google.com/translate_a/t?' + urllib.parse.urlencode({
        'client': 'dict-chrome-ex', 'sl': 'auto', 'tl': 'pt', 'q': ch
    })
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=10).read().decode('utf-8')
    data = json.loads(raw)
    if isinstance(data, list) and data:
        if isinstance(data[0], list) and data[0]:
            return str(data[0][0]).strip()
        if isinstance(data[0], str):
            return data[0].strip()
    raise ValueError('Resposta inesperada clients5')

def _call_mymemory(ch):
    parts = []
    for sub in _split_chunks(ch, 460):
        url = 'https://api.mymemory.translated.net/get?' + urllib.parse.urlencode({
            'q': sub, 'langpair': 'en|pt-BR', 'de': 'ckaitimes@ckintelligence.com.br'
        })
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=12).read().decode('utf-8')
        data = json.loads(raw)
        if int(data.get('responseStatus') or 0) != 200:
            raise urllib.error.HTTPError(url, int(data.get('responseStatus') or 429), str(data.get('responseDetails')), {}, None)
        txt = (data.get('responseData') or {}).get('translatedText') or ''
        if not txt or 'MYMEMORY WARNING' in txt.upper():
            raise urllib.error.HTTPError(url, 429, 'MyMemory quota limit', {}, None)
        parts.append(html.unescape(txt).strip())
        time.sleep(0.1)
    return ' '.join(parts).strip()

def _translate_chunk_waterfall(ch):
    providers = [('gtx', _call_gtx), ('clients5', _call_clients5), ('mymemory', _call_mymemory)]
    for name, fn in providers:
        if name in BLOCKED_PROVIDERS:
            continue
        try:
            time.sleep(0.12)
            out = fn(ch)
            if out:
                with TRANS_LOCK:
                    TRANS_STATS[name] += 1
                return out
        except urllib.error.HTTPError as e:
            with TRANS_LOCK:
                TRANS_STATS['last_err'] = f'{name}: HTTP {e.code}'
                if e.code in (403, 429):
                    BLOCKED_PROVIDERS.add(name)
        except Exception as e:
            with TRANS_LOCK:
                TRANS_STATS['last_err'] = f'{name}: {str(e)[:60]}'
    with TRANS_LOCK:
        TRANS_STATS['fail'] += 1
    return ch

def translate_literal_pt(text):
    """
    Tradução literal 1-para-1 (ZERO invenções) com fallback automático em 3 camadas
    (Google GTX -> Clients5 -> MyMemory) e circuit-breaker contra HTTP 429.
    """
    if not text or len(text.strip()) < 3 or is_probably_pt(text):
        return text
    chunks = _split_chunks(text.strip(), 1400)
    out_parts = [_translate_chunk_waterfall(ch) for ch in chunks]
    sep = '\n\n' if '\n\n' in text else ' '
    return sep.join(out_parts).strip()

def parse_pub_ts(date_str):
    """Converte data RSS/Atom/ISO em timestamp Unix UTC (0 se não reconhecível)."""
    if not date_str:
        return 0
    s = str(date_str).strip()
    if s in ('Trending', 'Recente', 'Oficial', 'Semanal'):
        return int(NOW_BRT.timestamp()) - 3600 * 18  # recente, abaixo de notícias datadas de hoje
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        pass
    try:
        s_iso = s.replace('Z', '+00:00')
        if len(s_iso) == 10:
            dt = datetime.strptime(s_iso, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(s_iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0

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
        full_paras = []
        if not is_atom:
            title = clean_text(e.findtext('title') or '', 180)
            link = (e.findtext('link') or '').strip()
            pub = (e.findtext('pubDate') or e.findtext('{http://purl.org/dc/elements/1.1/}date') or '').strip()
            raw_desc = e.findtext('description') or ''
            raw_content = e.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or ''
            if raw_content:
                full_paras = extract_paragraphs_from_html(raw_content, max_paragraphs=12, min_len=55)
            desc = clean_text(raw_desc, 420)
            if full_paras and (len(desc) < 120 or desc.lower().startswith('plus:')):
                desc = ' '.join(full_paras[:2])[:520]
        else:
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            title = clean_text(e.findtext('a:title', default='', namespaces=ns), 180)
            link_el = e.find('a:link', ns)
            link = link_el.attrib.get('href', '') if link_el is not None else ''
            pub = (e.findtext('a:updated', default='', namespaces=ns) or e.findtext('a:published', default='', namespaces=ns)).strip()
            raw_content = e.findtext('a:content', default='', namespaces=ns) or ''
            if raw_content:
                full_paras = extract_paragraphs_from_html(raw_content, max_paragraphs=12, min_len=55)
            desc = clean_text(e.findtext('a:summary', default='', namespaces=ns) or raw_content, 420)

        if title and link:
            items.append({
                'source': name,
                'section': section,
                'title': title,
                'url': link,
                'date': pub[:25],
                'published_ts': parse_pub_ts(pub),
                'summary': desc,
                'full_paragraphs': full_paras
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
            'summary': f"Modelo open-source em alta no Hugging Face para a categoria '{tag}', com {likes:,} curtidas e {dl:,} downloads no mês. Pode ser avaliado para uso local (on-premise).",
            'full_paragraphs': []
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
            'summary': f"Aplicação demonstrativa interativa em alta no Hugging Face ({sdk}), acumulando {likes:,} curtidas da comunidade de engenharia de IA.",
            'full_paragraphs': []
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
            desc = clean_text(m_desc.group(1) if m_desc else '', 360)
            stars = m_stars.group(1) if m_stars else '—'
            items.append({
                'source': f'GitHub Trending ({lang.capitalize()})',
                'section': 'tempo_real',
                'title': f"{repo_name} (+{stars} ⭐ hoje)",
                'url': f"https://github.com{repo_path}",
                'date': 'Trending',
                'summary': desc or 'Repositório open-source em alta hoje no GitHub.',
                'full_paragraphs': []
            })
    return items

def parse_hackernews_ai(limit=5):
    raw = fetch_url('https://hn.algolia.com/api/v1/search_by_date?query=AI+LLM+agent&tags=story&numericFilters=points>50&hitsPerPage=' + str(limit))
    data = json.loads(raw)
    items = []
    for h in data.get('hits', [])[:limit]:
        title = clean_text(h.get('title', ''), 170)
        url = h.get('url') or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        pts = h.get('points', 0)
        comments = h.get('num_comments', 0)
        items.append({
            'source': 'Hacker News (Engenharia IA)',
            'section': 'labs',
            'title': title,
            'url': url,
            'date': (h.get('created_at') or '')[:10],
            'summary': f"Discussão técnica em alta no Hacker News com {pts} votos e {comments} comentários de engenheiros e pesquisadores.",
            'full_paragraphs': []
        })
    return items

def parse_the_batch(limit=4):
    raw = fetch_url('https://www.deeplearning.ai/the-batch/')
    items = []
    matches = re.findall(r'href="(/the-batch/[^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>', raw, re.DOTALL)
    seen = set()
    for path, title_html in matches:
        title = clean_text(title_html, 160)
        if title and path not in seen and len(title) > 12 and title.lower() != 'popular articles':
            seen.add(path)
            items.append({
                'source': 'The Batch (Andrew Ng)',
                'section': 'newsletters',
                'title': title,
                'url': 'https://www.deeplearning.ai' + path,
                'date': 'Semanal',
                'summary': 'Edição semanal da DeepLearning.AI (equipe do Andrew Ng) analisando avanços técnicos e aplicações reais de negócios.',
                'full_paragraphs': []
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
                'summary': 'Artigo técnico da Ultralytics sobre visão computacional, modelos YOLO e aplicações práticas em edge AI e indústria.',
                'full_paragraphs': []
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
        m_head = re.search(r'<h[1-4][^>]*>(.*?)</h[1-4]>', inner, re.DOTALL | re.IGNORECASE)
        title = clean_text(m_head.group(1) if m_head else inner, 160)
        if title and path not in seen and len(title) > 15:
            seen.add(path)
            items.append({
                'source': 'Anthropic News (Claude)',
                'section': 'labs',
                'title': title,
                'url': 'https://www.anthropic.com' + path,
                'date': 'Oficial',
                'summary': 'Comunicado oficial publicado no portal da Anthropic (criadora do Claude).',
                'full_paragraphs': []
            })
            if len(items) >= limit:
                break
    return items

def enrich_article_fulltext(item):
    """Para matérias sem parágrafos completos vindos do RSS, busca os parágrafos reais da página oficial."""
    if item.get('full_paragraphs') and len(item['full_paragraphs']) >= 3:
        return
    url = item.get('url', '')
    if not url or 'news.google.com' in url or 'github.com' in url or 'huggingface.co' in url:
        return
    try:
        page_html = fetch_url(url, timeout=10)
        paras = extract_paragraphs_from_html(page_html, max_paragraphs=10, min_len=60)
        if paras:
            item['full_paragraphs'] = paras
            if len(item.get('summary', '')) < 150:
                item['summary'] = ' '.join(paras[:2])[:520]
    except Exception:
        pass

def fetch_artificial_analysis_rankings():
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
    return {
        'source_name': 'Artificial Analysis — Intelligence Index (Oficial)',
        'source_url': 'https://artificialanalysis.ai/leaderboards/models',
        'total_evaluated': len(models),
        'top50_overall': models[:50],
        'top20_open_source': [m for m in models if m['is_open_weights']][:20]
    }

def load_translation_cache():
    latest_json = os.path.join(DATA_DIR, 'latest.json')
    cache = {}
    if not os.path.exists(latest_json):
        return cache
    try:
        with open(latest_json, 'r', encoding='utf-8') as f:
            old = json.load(f)
        for it in old.get('items', []):
            url = it.get('url')
            t_en = it.get('title') or ''
            t_pt = it.get('title_pt') or ''
            if url and t_pt and (t_pt != t_en or is_probably_pt(t_en)):
                cache[url] = {
                    'title': t_en,
                    'title_pt': t_pt,
                    'summary_pt': it.get('summary_pt') or '',
                    'full_paragraphs': it.get('full_paragraphs') or [],
                    'full_paragraphs_pt': it.get('full_paragraphs_pt') or [],
                }
    except Exception:
        pass
    return cache

def translate_item(it, trans_cache=None):
    """Traduz literalmente título, resumo e parágrafos completos para PT-BR (com reuso de cache)."""
    url = it.get('url', '')
    paras_en = (it.get('full_paragraphs') or [])[:8]
    it['full_paragraphs'] = paras_en

    cached = (trans_cache or {}).get(url)
    if cached and cached.get('title') == it.get('title') and len(cached.get('full_paragraphs_pt') or []) >= len(paras_en):
        it['title_pt'] = cached['title_pt']
        it['summary_pt'] = cached['summary_pt'] or it.get('summary', '')
        it['full_paragraphs_pt'] = (cached['full_paragraphs_pt'] or [])[:len(paras_en)]
        with TRANS_LOCK:
            TRANS_STATS['cache'] += 1
        return it

    title = it.get('title', '')
    summary = it.get('summary', '')
    # Traduz título + resumo numa única requisição quando ambos precisarem (economiza 50% das chamadas)
    if title and summary and not is_probably_pt(title) and not is_probably_pt(summary) and (len(title) + len(summary) < 1200):
        sep = '\n§§§\n'
        combo = translate_literal_pt(title + sep + summary)
        if '§§§' in combo:
            parts = combo.split('§§§', 1)
            it['title_pt'] = parts[0].strip()
            it['summary_pt'] = parts[1].strip()
        else:
            it['title_pt'] = translate_literal_pt(title)
            it['summary_pt'] = translate_literal_pt(summary)
    else:
        it['title_pt'] = translate_literal_pt(title)
        it['summary_pt'] = translate_literal_pt(summary)

    paras_pt = []
    if paras_en:
        if 'gtx' in BLOCKED_PROVIDERS and 'clients5' in BLOCKED_PROVIDERS:
            paras_pt = [translate_literal_pt(p) for p in paras_en]
        else:
            joined = '\n\n'.join(paras_en)
            translated_block = translate_literal_pt(joined)
            paras_pt = [p.strip() for p in translated_block.split('\n') if len(p.strip()) > 20]
            if len(paras_pt) != len(paras_en):
                paras_pt = [translate_literal_pt(p) for p in paras_en]
    it['full_paragraphs_pt'] = paras_pt
    return it

def collect_all():
    tasks = [
        ('TLDR AI', lambda: parse_rss('TLDR AI', 'newsletters', 'https://tldr.tech/api/rss/ai', 5)),
        ('The Rundown AI', lambda: parse_rss('The Rundown AI', 'newsletters', 'https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml', 4)),
        ('One Useful Thing (Ethan Mollick)', lambda: parse_rss('One Useful Thing (Ethan Mollick)', 'newsletters', 'https://www.oneusefulthing.org/feed', 3)),
        ('The Batch (Andrew Ng)', lambda: parse_the_batch(4)),
        ('TechCrunch AI (Diário 24/7)', lambda: parse_rss('TechCrunch AI', 'newsletters', 'https://techcrunch.com/category/artificial-intelligence/feed/', 5)),
        ('The Verge AI (Diário 24/7)', lambda: parse_rss('The Verge AI', 'newsletters', 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml', 4)),
        ('MIT Technology Review AI', lambda: parse_rss('MIT Technology Review AI', 'newsletters', 'https://www.technologyreview.com/topic/artificial-intelligence/feed', 4)),
        ('Ars Technica AI', lambda: parse_rss('Ars Technica AI', 'labs', 'https://feeds.arstechnica.com/arstechnica/technology-lab', 4)),
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

    # Normaliza published_ts para todos os itens (incluindo fontes não-RSS) e deduplica por URL
    deduped = []
    seen_urls = set()
    for it in results:
        u = it.get('url', '')
        if not u or u in seen_urls:
            continue
        seen_urls.add(u)
        if not it.get('published_ts'):
            it['published_ts'] = parse_pub_ts(it.get('date', ''))
        deduped.append(it)
    results = deduped
    results.sort(key=lambda x: x.get('published_ts', 0), reverse=True)

    # Enriquece com parágrafos completos os itens MAIS RECENTES das fontes editoriais
    priority_sources = {
        'TechCrunch AI', 'The Verge AI', 'MIT Technology Review AI', 'Ars Technica AI',
        'The Rundown AI', 'TLDR AI', 'OpenAI News', 'Anthropic News (Claude)',
        'Google AI / DeepMind', 'NVIDIA Industrial & AI', 'n8n (Automação & Orquestração)',
        'One Useful Thing (Ethan Mollick)', 'Ultralytics (YOLO / Visão Industrial)',
        'The Batch (Andrew Ng)'
    }
    to_enrich = [it for it in results if it.get('source') in priority_sources and len(it.get('full_paragraphs') or []) < 3][:20]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(enrich_article_fulltext, to_enrich))

    # Traduz literalmente TODOS os itens (título + resumo + texto completo) para PT-BR com cache e cadência segura
    trans_cache = load_translation_cache()
    print(f"[CK AI TIMES] Traduzindo literalmente {len(results)} notícias reais para PT-BR (cache={len(trans_cache)} itens)...")
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda it: translate_item(it, trans_cache), results))
    print(f"[CK AI TIMES] Tradução stats: cache={TRANS_STATS['cache']} gtx={TRANS_STATS['gtx']} clients5={TRANS_STATS['clients5']} mymemory={TRANS_STATS['mymemory']} falhas={TRANS_STATS['fail']} last_err={TRANS_STATS['last_err'] or 'nenhum'}")

    # Ranking Top 50 Artificial Analysis
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

    latest_json = os.path.join(DATA_DIR, 'latest.json')
    with open(latest_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    rich_count = sum(1 for it in results if len(it.get('full_paragraphs_pt', [])) >= 2)
    print(f"[CK AI TIMES] Concluído: {len(results)} notícias traduzidas ({rich_count} com matéria longa) + Top {len(rankings['top50_overall'])} LLMs!")

if __name__ == '__main__':
    collect_all()
