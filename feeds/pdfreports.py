"""Monthly 'permits issued' PDF reports that cities post (Orem, Riverton, West Jordan, Summit County, ...).
Finds the newest report links on the listed page, extracts the text, and keeps the lines for new buildings.
Claude (the Permit Watch routine) turns the lines into permits; no web searches needed."""
import re, io
from bs4 import BeautifulSoup
from pypdf import PdfReader
from .common import get, log, load, save, iid, today, score_text

def pull(src):
    seen = load("state/pdf_seen.json", {})
    urls = [src["url"]] if src["url"].lower().endswith(".pdf") or src.get("direct") else []
    if not urls:
        r = get(src["url"])
        if r:
            s = BeautifulSoup(r.text, "html.parser")
            for a in s.find_all("a", href=True):
                h, t = a["href"], a.get_text(" ", strip=True)
                if re.search(src.get("linkMatch", r"permit"), h + " " + t, re.I) and re.search(r"\.pdf|DocumentCenter/View", h, re.I):
                    urls.append(requests_join(src["url"], h))
    out = []
    for u in urls[: src.get("maxFiles", 3)]:
        r = get(u, timeout=90)
        if not r: continue
        sig = iid(u, len(r.content))
        if seen.get(u) == sig: continue
        seen[u] = sig
        try: text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages[:60])
        except Exception as e: log("pdf fail", u, e); continue
        lines = [l.strip() for l in text.splitlines() if re.search(src.get("lineMatch", r"new|single|family|dwelling|commercial|townhome|apartment|multi"), l, re.I)]
        out.append({"id": iid("pdf", u, sig), "source": "pdf:" + src["name"], "kind": "permit-report", "jurisdiction": src["jurisdiction"],
                    "url": u, "lines": lines[:800], "foundAt": today()})
    save("state/pdf_seen.json", seen); log("pdf", src["name"], len(out)); return out

def requests_join(base, href):
    from urllib.parse import urljoin; return urljoin(base, href)
