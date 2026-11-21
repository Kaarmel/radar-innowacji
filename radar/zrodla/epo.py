"""Patenty europejskie (EP): EPO Linked Data (SPARQL, indeks Lucene na tytułach) + abstrakty z European Publication
Server dla kilku najlepszych. Bez klucza. robots.txt: /linked-data/query i /publication-server/ dozwolone."""
import datetime
import json
import re

from .. import siec
from ..model import Dokument
from ..tekst import bez_html, tokeny
from . import BrakDostepu

SPARQL = "https://data.epo.org/linked-data/query"
EPS = "https://data.epo.org/publication-server/publications"
ZAPYTANIE = """PREFIX pat: <http://data.epo.org/linked-data/def/patent/>
PREFIX text: <http://jena.apache.org/text#>
PREFIX vcard: <http://www.w3.org/2006/vcard/ns#>
SELECT ?pub ?score ?title ?date ?kind ?appnum (SAMPLE(?applicant) AS ?app1)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?ipc), "/ipc/"); separator=";") AS ?ipcs)
WHERE {
  (?pub ?score) text:query (pat:titleOfInvention "%s" %d) .
  ?pub pat:titleOfInvention ?title . FILTER(LANG(?title) = "en")
  ?pub pat:publicationDate ?date ; pat:publicationKind ?kind ; pat:application ?app .
  ?app pat:applicationNumberEpodoc ?appnum .
  OPTIONAL { ?pub pat:applicantVC/vcard:fn ?applicant }
  OPTIONAL { ?pub pat:classificationIPCInventive ?ipc }
} GROUP BY ?pub ?score ?title ?date ?kind ?appnum ORDER BY DESC(?score)"""
STOP_EN = {"and", "or", "the", "of", "for", "with", "without", "based", "using", "method", "system", "device", "a", "an", "in", "on", "to", "no"}


def status_z_kodu(kod: str) -> str:
    return "udzielony" if kod.upper().startswith("B") else "zgloszenie"


def _prefiks(w: str) -> str:
    """Prosty stemming dla Lucene bez stemmera: liczba mnoga i końcówki (microplastics → microplast*)."""
    if w.endswith("s") and len(w) > 4:
        w = w[:-1]
    return w[:len(w) - 2] if len(w) > 7 else w


def zapytanie(terminy_en: list[str]) -> str:
    """Lucene: każda fraza to AND rdzeni z *, frazy łączone OR; całość w nawiasie (wymóg serwera)."""
    frazy = []
    for t in terminy_en[:6]:
        slowa = [w for w in tokeny(t) if w not in STOP_EN and len(w) > 2][:3]
        if slowa:
            frazy.append("(" + " AND ".join(f"{_prefiks(w)}*" for w in slowa) + ")")
    return "(" + " OR ".join(frazy) + ")" if frazy else ""


def parsuj(surowe: dict) -> list[Dokument]:
    """Jedno zgłoszenie (appnum) = jeden dokument; udzielony (B) wygrywa z publikacją zgłoszenia (A)."""
    najlepsze: dict[str, Dokument] = {}
    for b in surowe.get("results", {}).get("bindings", []):
        m = re.search(r"/publication/([A-Z]{2})/(\w+)/(\w+)/", b["pub"]["value"])
        if not m:
            continue
        kraj, nr, kod = m.groups()
        ipcs = b.get("ipcs", {}).get("value", "").replace("-", "/")
        d = Dokument(id=f"epo:{kraj}{nr}{kod}", zrodlo="epo", typ="patent", tytul=b["title"]["value"].capitalize(),
                     opis=f"IPC: {ipcs}" if ipcs else "",
                     link=f"https://worldwide.espacenet.com/patent/search?q=pn%3D{kraj}{nr}{kod}",
                     rok=int(b["date"]["value"][:4]), instytucje=[bez_html(b["app1"]["value"])] if b.get("app1") else [],
                     status=status_z_kodu(kod), jezyk="en")
        app = b["appnum"]["value"]
        if app not in najlepsze or (d.status == "udzielony" and najlepsze[app].status != "udzielony"):
            najlepsze[app] = d
    return list(najlepsze.values())


def abstrakt_z_xml(xml: str) -> str:
    m = re.search(r"<abstract[^>]*>(.*?)</abstract>", xml or "", re.S)
    return bez_html(m.group(1)) if m else ""


def _abstrakt(nr: str) -> str:
    rok, tydzien, _ = datetime.date.today().isocalendar()
    cialo = {"publicationNumber": nr, "applicationNumber": None, "ipcSymbol": None,
             "publicationDateRange": {"isRange": True, "publicationYear": None, "publicationWeek": None,
                                      "publicationYearStart": 1978, "publicationWeekStart": 51,
                                      "publicationYearEnd": rok, "publicationWeekEnd": tydzien},
             "publicationKinds": ["A1", "A2", "A3", "A8", "A9", "B1", "B2", "B3", "B8", "B9"]}
    r = siec.pobierz(EPS, params={"page": 0, "size": 3, "lng": "en"}, metoda="POST", dane=json.dumps(cialo),
                     headers={"Content-Type": "application/json"}, timeout=30)
    for p in (r.json().get("content") or []):
        if p.get("xmlFile"):
            x = siec.pobierz(f"{EPS}/xml", params={"path": p["xmlFile"]}, timeout=30)
            if x.status_code == 200:
                return abstrakt_z_xml(x.text)
    return ""


def szukaj(terminy_en: list[str], limit: int = 25, abstrakty: int = 5) -> list[Dokument]:
    q = zapytanie(terminy_en)
    if not q:
        return []
    try:
        r = siec.pobierz(SPARQL, params={"query": ZAPYTANIE % (q.replace('"', ""), limit)},
                         headers={"Accept": "application/sparql-results+json"}, timeout=40)
        r.raise_for_status()
        docs = parsuj(r.json())
    except Exception as e:
        raise BrakDostepu(f"EPO Linked Data: {e}") from e
    for d in docs[:abstrakty]:
        try:
            nr = re.match(r"epo:EP(\d+)", d.id).group(1)
            a = _abstrakt(nr)
            if a:
                d.opis = f"{a}\n{d.opis}".strip()
        except Exception:
            pass
    return docs
