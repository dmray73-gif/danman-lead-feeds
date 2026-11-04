"""Shared helpers: polite HTTP (robots.txt, rate limit, identifying user agent), JSON store, keyword scoring."""
import json, os, re, time, hashlib, datetime, urllib.robotparser
from urllib.parse import urlparse
import requests

START = time.time()
BUDGET = float(os.environ.get("FEEDS_BUDGET_MIN", "105")) * 60
def left(): return BUDGET - (time.time() - START)

UA = "DanMan-Lead-Feeds/1.0 (public records research; contact via GitHub repo)"
S = requests.Session(); S.headers["User-Agent"] = UA
_robots, _last = {}, {}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def allowed(url):
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    rp = _robots.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser(host + "/robots.txt")
        try: rp.read()
        except Exception: rp = None
        _robots[host] = rp
    return True if rp is None else rp.can_fetch(UA, url)

def get(url, delay=1.0, **kw):
    """GET with robots.txt check and a per-host delay. Returns Response or None."""
    if not allowed(url):
        log("robots.txt disallows", url); return None
    host = urlparse(url).netloc
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0: time.sleep(wait)
    _last[host] = time.time()
    try:
        r = S.get(url, timeout=kw.pop("timeout", 40), **kw)
        if r.status_code == 200: return r
        log("HTTP", r.status_code, url)
    except Exception as e:
        log("ERR", e, url)
    return None

def log(*a): print(datetime.datetime.utcnow().strftime("%H:%M:%S"), *a, flush=True)
def today(): return datetime.date.today().isoformat()
def iid(*parts): return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

def load(name, default):
    p = os.path.join(ROOT, name)
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def save(name, obj):
    p = os.path.join(ROOT, name); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: json.dump(obj, f, indent=1, ensure_ascii=False)

# What makes an agenda item or document worth Dan's attention (insulation = new buildings, additions, big remodels)
KW = {
 "subdivision": 3, "preliminary plat": 3, "final plat": 3, "plat amendment": 1, "site plan": 3, "conditional use": 2,
 "townhome": 3, "townhouse": 3, "apartment": 3, "multi-family": 3, "multifamily": 3, "condominium": 3, "mixed use": 3, "mixed-use": 3,
 "planned unit development": 2, "pud": 2, "master plan": 1, "phase": 1, "lots": 1, "units": 1, "dwelling": 1,
 "commercial": 2, "warehouse": 2, "industrial": 2, "office building": 2, "hotel": 3, "assisted living": 3, "senior living": 3,
 "school": 1, "church": 1, "meetinghouse": 2, "data center": 3, "medical": 2, "clinic": 2, "design review": 2, "new construction": 3,
}
ENT = re.compile(r"\b([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,5}\s+(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Company|Co\.|Homes|Builders|Building|Construction|Development|Developers|Communities|Partners|Group|Architects?|Architecture|Engineering|Properties|Ventures|Investments|Holdings))\b")

def score_text(t):
    low = t.lower(); hits = {k: v for k, v in KW.items() if re.search(r"\b" + re.escape(k) + r"\b", low)}
    return sum(hits.values()), sorted(hits)

def entities(t, limit=25):
    out = []
    for m in ENT.finditer(t):
        e = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
        if len(e) > 4 and e not in out and not re.match(r"^(The|City|Planning|Utah|County|State)\b", e): out.append(e)
        if len(out) >= limit: break
    return out

def snippets(t, terms, width=220, limit=8):
    out, low = [], t.lower()
    for k in terms:
        for m in re.finditer(r"\b" + re.escape(k) + r"\b", low):
            s = max(0, m.start() - width // 2); seg = re.sub(r"\s+", " ", t[s:s + width]).strip()
            if seg not in out: out.append(seg)
            if len(out) >= limit: return out
    return out
