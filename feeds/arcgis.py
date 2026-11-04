"""City/county permit layers published on ArcGIS REST (e.g. Provo CurrentProjects). Generic: each source in
sources.json gives the layer query URL, the date field and how fields map. Queries only what changed recently."""
import datetime
from .common import get, log, iid, today

def pull(src, days=45):
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    where = src.get("where") or f"{src['dateField']} >= DATE '{since}'"
    out, off = [], 0
    while True:
        r = get(src["url"].rstrip("/") + "/query", params={"where": where, "outFields": "*", "f": "json", "resultOffset": off,
                "resultRecordCount": 500, "orderByFields": src["dateField"] + " DESC", "returnGeometry": "false"}, delay=1.0)
        if not r: break
        js = r.json(); feats = js.get("features", [])
        for f in feats:
            a = f.get("attributes", {}); m = src.get("map", {})
            g = lambda k: a.get(m.get(k, ""), "") if m.get(k) else ""
            d = a.get(src["dateField"])
            if isinstance(d, (int, float)): d = datetime.datetime.utcfromtimestamp(d / 1000).date().isoformat()
            out.append({"id": iid("arcgis", src["name"], g("number") or a.get("OBJECTID")), "source": "arcgis:" + src["name"], "kind": "permit",
                        "jurisdiction": src["jurisdiction"], "permitNumber": g("number"), "type": g("type"), "description": g("description"),
                        "address": g("address"), "valuation": g("valuation"), "contractor": g("contractor"), "status": g("status"),
                        "issuedDate": d, "url": src.get("link", src["url"]), "raw": {k: v for k, v in a.items() if v not in (None, "")}, "foundAt": today()})
        if not js.get("exceededTransferLimit") or not feats: break
        off += len(feats)
    log("arcgis", src["name"], len(out)); return out
