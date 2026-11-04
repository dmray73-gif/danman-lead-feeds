"""Accela Citizen Access (ACA) portals: Salt Lake City (SLCREF) and any other Utah agency on Accela.
Searches records opened in the last N days, reads the result grid (record #, type, address, description, status),
then opens new-construction records to read the licensed professional (contractor) and job value.
Uses a real browser (Playwright) because ACA pages are ASP.NET postbacks. Respects robots.txt."""
import re, datetime
from .common import allowed, log, iid, today, load, save

GRID = "[id$='gdvPermitList'] tr"
NEWISH = re.compile(r"new|single|family|dwelling|commercial|multi|townho|apartment|addition|shell|tenant", re.I)

def pull(src, days=14, max_details=60):
    from playwright.sync_api import sync_playwright
    base = src["url"]
    if not allowed(base): log("robots.txt disallows", base); return []
    seen = load("state/accela_seen.json", {})
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%m/%d/%Y"); end = datetime.date.today().strftime("%m/%d/%Y")
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(user_agent="DanMan-Lead-Feeds/1.0 (public records research)")
        for module in src.get("modules", ["Building"]):
            try:
                pg.goto(f"{base}/Cap/CapHome.aspx?module={module}&TabName={module}", wait_until="domcontentloaded", timeout=60000)
                pg.fill("[id$='txtGSStartDate']", start); pg.fill("[id$='txtGSEndDate']", end)
                pg.click("[id$='btnNewSearch']"); pg.wait_for_timeout(5000)
            except Exception as e:
                log("accela search failed", module, e); continue
            for page_no in range(1, src.get("maxPages", 15) + 1):
                rows = pg.query_selector_all(GRID)
                hdr = [c.inner_text().strip().lower() for c in (rows[0].query_selector_all("th") if rows else [])]
                for r in rows[1:]:
                    cells = [c.inner_text().strip() for c in r.query_selector_all("td")]
                    if len(cells) < 3: continue
                    rec = dict(zip(hdr, cells)) if hdr and len(hdr) == len(cells) else {"cells": cells}
                    link = r.query_selector("a[href*='CapDetail']")
                    num = (rec.get("record number") or rec.get("permit number") or (link.inner_text().strip() if link else "")).strip()
                    if not num: continue
                    href = link.get_attribute("href") if link else ""
                    out.append({"id": iid("accela", src["name"], num), "source": "accela:" + src["name"], "kind": "permit", "module": module,
                                "jurisdiction": src["jurisdiction"], "permitNumber": num, "type": rec.get("record type", ""),
                                "description": rec.get("description", "") or rec.get("project name", ""), "address": rec.get("address", ""),
                                "status": rec.get("status", ""), "openedDate": rec.get("date", ""), "detail": href, "foundAt": today()})
                nxt = pg.query_selector("a:has-text('Next >')")
                if not nxt: break
                nxt.click(); pg.wait_for_timeout(3500)
        # details for new-construction records not seen before: contractor (licensed professional) and job value
        n = 0
        for it in out:
            if n >= max_details or it["id"] in seen or not it["detail"] or not NEWISH.search(it["type"] + " " + it["description"]): continue
            try:
                url = it["detail"] if it["detail"].startswith("http") else base.split("/")[0] + "//" + base.split("/")[2] + it["detail"]
                pg.goto(url, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(1500); n += 1
                t = pg.inner_text("body")
                m = re.search(r"Licensed Professional:?\s*(.{0,300})", t, re.S); it["contractorBlock"] = re.sub(r"\s+", " ", m.group(1))[:300] if m else ""
                v = re.search(r"Job Value\(\$\):?\s*\$?([\d,\.]+)", t); it["valuation"] = v.group(1).replace(",", "") if v else ""
                a = re.search(r"Applicant:?\s*(.{0,200})", t, re.S); it["applicantBlock"] = re.sub(r"\s+", " ", a.group(1))[:200] if a else ""
                seen[it["id"]] = today()
            except Exception as e:
                log("accela detail failed", it["permitNumber"], e)
        b.close()
    save("state/accela_seen.json", seen); log("accela", src["name"], len(out)); return out
