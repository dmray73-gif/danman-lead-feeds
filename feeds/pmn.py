"""Utah Public Notice Website (utah.gov/pmn): every city, town and county in Utah posts its planning commission,
council and design-review agendas here. Statewide coverage.

discover(): walks public-body ids and keeps the bodies that approve buildings (planning, council, design review,
            housing boards). Resumable; run weekly.
daily():    for each kept body, reads new notices (last 60 days), downloads the agenda/packet PDFs and keeps items
            about subdivisions, site plans, multifamily, commercial, etc., with the companies named."""
import re, io, datetime
from bs4 import BeautifulSoup
from pypdf import PdfReader
from .common import get, log, load, save, score_text, entities, snippets, iid, today

BASE = "https://www.utah.gov/pmn/sitemap"
KEEP = re.compile(r"planning|zoning|council|commission|design review|development review|architectural|board of adjustment|"
                  r"redevelopment|housing|private activity bond|olene walker|land use|appeal authority|county commission", re.I)
SKIP = re.compile(r"school board|library|cemetery|mosquito|water conservancy|fire district board|arts|museum|audit|retirement", re.I)

def _body(i):
    r = get(f"{BASE}/publicbody/{i}.html", delay=0.6)
    if not r: return None
    s = BeautifulSoup(r.text, "html.parser")
    text = s.get_text(" ", strip=True)
    m = re.search(r"Public Body Name:?\s*(.+?)\s+Entity Name:?\s*(.+?)\s+(?:Contact|Street|Address|Mailing)", text)
    name, entity = (m.group(1), m.group(2)) if m else ((s.title.string or "").strip() if s.title else "", "")
    return {"id": i, "name": name.strip()[:120], "entity": entity.strip()[:120]}

def discover(batch=1500, max_id=12000):
    reg = load("state/pmn_bodies.json", {"next": 1, "bodies": {}, "misses": 0})
    i, end = reg["next"], min(reg["next"] + batch, max_id)
    while i < end:
        b = _body(i)
        if b and b["name"]:
            reg["misses"] = 0
            full = b["name"] + " " + b["entity"]
            if KEEP.search(full) and not SKIP.search(full): reg["bodies"][str(i)] = b
        else:
            reg["misses"] += 1
        i += 1
        if reg["misses"] > 400: log("pmn discover: 400 empty ids in a row, wrapping"); i = max_id; break
    if i >= max_id: reg["complete"] = True
    reg["next"] = 1 if i >= max_id else i
    reg["updated"] = today(); save("state/pmn_bodies.json", reg)
    log("pmn bodies kept:", len(reg["bodies"]), "next id:", reg["next"])

def _rows(body_id):
    r = get(f"{BASE}/publicbody/{body_id}.html", delay=0.8)
    if not r: return []
    s = BeautifulSoup(r.text, "html.parser"); out = []
    for tr in s.select("tr"):
        a = tr.find("a", href=re.compile(r"/notice/\d+\.html"))
        if not a: continue
        m = re.search(r"(\d{4})/(\d{2})/(\d{2})", tr.get_text(" "))
        out.append({"notice": re.search(r"/notice/(\d+)", a["href"]).group(1), "title": a.get_text(" ", strip=True),
                    "date": "-".join(m.groups()) if m else ""})
    return out

def _pdf_text(url, max_pages=120):
    r = get(url, delay=0.8, timeout=90)
    if not r or len(r.content) > 40_000_000: return ""
    try:
        rd = PdfReader(io.BytesIO(r.content))
        return "\n".join((p.extract_text() or "") for p in rd.pages[:max_pages])
    except Exception as e:
        log("pdf fail", url, e); return ""

def daily(days=60):
    reg = load("state/pmn_bodies.json", {"bodies": {}})
    seen = load("state/pmn_seen.json", {})
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    items = []
    for bid, b in reg["bodies"].items():
        for row in _rows(bid):
            if row["notice"] in seen or (row["date"] and row["date"] < cutoff): continue
            seen[row["notice"]] = today()
            if re.search(r"minutes|cancel|audio|recording", row["title"], re.I): continue
            nurl = f"{BASE}/notice/{row['notice']}.html"
            r = get(nurl, delay=0.8)
            if not r: continue
            s = BeautifulSoup(r.text, "html.parser")
            text = s.get_text(" ", strip=True)
            files = sorted({("https://www.utah.gov" + a["href"]) if a["href"].startswith("/") else a["href"]
                            for a in s.find_all("a", href=re.compile(r"/pmn/files/\d+\.pdf", re.I))})
            for f in files[:4]: text += "\n" + _pdf_text(f)
            sc, terms = score_text(text)
            if sc < 3: continue
            items.append({"id": iid("pmn", row["notice"]), "source": "pmn", "kind": "agenda", "body": b["name"], "entity": b["entity"],
                          "title": row["title"], "meetingDate": row["date"], "url": nurl, "files": files[:4], "score": sc, "terms": terms,
                          "companies": entities(text), "snippets": snippets(text, [t for t in terms if KW_STRONG(t)] or terms), "foundAt": today()})
    save("state/pmn_seen.json", seen)
    log("pmn items:", len(items)); return items

def KW_STRONG(t): return t in ("subdivision", "preliminary plat", "final plat", "site plan", "townhome", "apartment", "multifamily",
                               "multi-family", "mixed use", "commercial", "hotel", "warehouse", "data center", "new construction")
