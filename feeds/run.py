"""Run every feed in sources.json and write data/latest.json (rolling 45 days) and data/YYYY-MM-DD.json (today's new items).
The DanMan Leads routines (Lead Finder, Permit Watch) read data/latest.json instead of spending web searches."""
import sys, json, datetime, traceback
from .common import load, save, log, today
from . import pmn, arcgis, pdfreports, accela

def main(mode="daily"):
    src = load("sources.json", {})
    if mode == "discover": pmn.discover(); return
    new, report = [], {}
    if not load("state/pmn_bodies.json", {}).get("complete"): pmn.discover(batch=2500)  # first weeks: keep mapping Utah public bodies
    def run(name, fn):
        try: items = fn(); new.extend(items); report[name] = {"items": len(items), "ok": True}
        except Exception as e: report[name] = {"ok": False, "error": str(e)[:300]}; traceback.print_exc()
    if src.get("pmn", {}).get("on", True): run("pmn", pmn.daily)
    for s in src.get("arcgis", []): run("arcgis:" + s["name"], lambda s=s: arcgis.pull(s))
    for s in src.get("pdf", []): run("pdf:" + s["name"], lambda s=s: pdfreports.pull(s))
    for s in src.get("accela", []): run("accela:" + s["name"], lambda s=s: accela.pull(s))
    latest = load("data/latest.json", {"items": []})
    keep = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
    byid = {i["id"]: i for i in latest.get("items", []) if i.get("foundAt", "") >= keep}
    fresh = [i for i in new if i["id"] not in byid]
    for i in new: byid.setdefault(i["id"], i)
    save("data/latest.json", {"updated": datetime.datetime.utcnow().isoformat() + "Z", "report": report, "newToday": len(fresh),
                              "items": sorted(byid.values(), key=lambda x: x.get("foundAt", ""), reverse=True)})
    save(f"data/{today()}.json", {"report": report, "items": fresh})
    log("done", json.dumps(report), "new:", len(fresh))

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "daily")
