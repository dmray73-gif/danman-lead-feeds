"""Pull the people/companies behind an agenda item: applicant, developer, owner, engineer, architect, builder,
plus company-looking names (LLC, Homes, Development...) and project size (units, lots, acres)."""
import re

ROLE = r"(applicant|developer|owner|property owner|petitioner|representative|agent|engineer|architect|builder|contractor|sponsor|requestor|requester)"
SUFFIX = (r"(?:LLC|L\.L\.C\.|Inc\.?|Incorporated|Corp\.?|Corporation|LP|LLP|Ltd\.?|Homes|Home Builders|Builders|Building|Development|Developers|"
          r"Construction|Constructors|Contractors|Communities|Partners|Properties|Property Group|Group|Holdings|Investments|Engineering|"
          r"Engineers|Architects|Architecture|Design|Company|Co\.|Ventures|Capital|Land|Realty|Associates|Enterprises|Companies|Residential|"
          r"Living|Real Estate|Trust)")
NAME = r"([A-Z0-9][A-Za-z0-9&'.\-]*(?:\s+(?:[A-Z0-9&][A-Za-z0-9&'.\-]*|of|and|at|the)){0,6})"
LABEL = re.compile(r"\b" + ROLE + r"s?\s*(?:/\s*\w+\s*)?[:\-–—]\s*", re.I)
NAMEAT = re.compile(NAME)
VERB = re.compile(NAME + r",?\s+(?:is\s+)?(?:requesting|requests|has requested|has applied|applied|is applying|proposes|is proposing|seeks)\b")
BY = re.compile(r"(?:submitted|requested|filed|presented|represented|sponsored|proposed|applied for)\s+by\s+" + NAME, re.I)
BEHALF = re.compile(r"on behalf of\s+" + NAME, re.I)
ORG = re.compile(r"\b((?:[A-Z][A-Za-z0-9&'.\-]+\s+){1,5}" + SUFFIX + r")\b")
SIZE = re.compile(r"\b(\d{1,4}(?:,\d{3})?(?:\.\d+)?)\s*[- ]?(units?|lots?|townhomes?|townhouses?|dwelling units?|homes|apartments?|acres?|rooms?|beds?|square feet|sq\.? ?ft)\b", re.I)
JUNK = re.compile(r"^(the|city|town|county|state|planning|staff|public|council|commission|item|agenda|motion|section|exhibit|zone|zoning|"
                  r"utah|department|community development|economic development|mr|mrs|ms|this|that|said|all|any|each|none|n/a|tbd)\b", re.I)

def _clean(s):
    s = re.sub(r"\s+", " ", s or "")
    s = re.split(r"(?<!\b[A-Z])(?<!Inc)(?<!Co)(?<!Corp)(?<!Ltd)\.\s+(?=[A-Z])", s)[0]
    s = re.split(r"\.\s+(?=(?:Engineer|Architect|Owner|Applicant|Developer|Agent|Item|Agenda|Staff|The)\b)", s)[0]
    s = s.strip(" .,;:-–—()\"'")
    s = re.split(r"\s+(?:to|for|requesting|requests|regarding|located|at approximately|on property|which|who|in the)\s", s)[0]
    return s[:80]

def parties(text, limit=12):
    out, seen = [], set()
    def add(role, name):
        n = _clean(name)
        if len(n) < 4 or JUNK.match(n): return
        k = n.lower()
        if any(k == x or k.startswith(x + " ") or x.startswith(k + " ") for x in seen): return
        seen.add(k); out.append({"role": role, "name": n})
    for m in LABEL.finditer(text):
        n = NAMEAT.match(text, m.end())
        if n: add(m.group(1).lower(), n.group(1))
    for m in BY.finditer(text): add("applicant", m.group(1))
    for m in BEHALF.finditer(text): add("applicant", m.group(1))
    for m in VERB.finditer(text):
        n = m.group(1)
        if re.search(SUFFIX + r"\s*$", n) or len(n.split()) <= 4: add("applicant", n)
    for m in ORG.finditer(text): add("company", m.group(1))
    return out[:limit]

def sizes(text, limit=6):
    out = []
    for m in SIZE.finditer(text):
        v = f"{m.group(1)} {m.group(2).lower()}"
        if v not in out: out.append(v)
        if len(out) >= limit: break
    return out

def party_snippets(text, ps, width=240, limit=6):
    out = []
    for p in ps:
        i = text.find(p["name"])
        if i < 0: continue
        seg = re.sub(r"\s+", " ", text[max(0, i - 90): i + width - 90]).strip()
        if seg not in out: out.append(seg)
        if len(out) >= limit: break
    return out
