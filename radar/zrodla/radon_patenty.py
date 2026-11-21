"""RAD-on: patenty i prawa ochronne polskich uczelni i instytutów (udzielone), z opisami. Bez twórców (osoby)."""
import sqlite3

from .. import db, siec
from ..model import Dokument
from .mapadotacji import _postep

API = "https://radon.nauka.gov.pl/opendata/polon/products"


def parsuj(surowe: dict) -> list[Dokument]:
    out = []
    for p in surowe.get("results", []):
        tytul = p.get("protectionTitle") or next((t["value"] for t in p.get("productTitles") or [] if t.get("value")), "")
        if not tytul or not p.get("protectionUuid"):
            continue
        inst = list(dict.fromkeys(i["institutionName"] for a in p.get("applicants") or []
                                  for i in a.get("institutions") or [] if i.get("institutionName")))
        wzor = "wzór" in (p.get("protectionType") or "").lower()
        nr = p.get("publicationNumber") or p.get("applicationNumber") or ""
        kod = "Y1" if wzor else "B1"
        region = (p.get("protectionRegion") or "").lower()
        link = (f"https://worldwide.espacenet.com/patent/search?q=pn%3DPL{nr}{kod}" if region == "polska" and nr
                else "https://radon.nauka.gov.pl/dane/patenty-i-prawa-ochronne")
        data = p.get("publicationDate") or p.get("applicationDate") or ""
        out.append(Dokument(id=f"radon_patenty:{p['protectionUuid']}", zrodlo="radon_patenty", typ="patent",
                            tytul=tytul.strip(), opis=f"{p.get('protectionType') or ''}. {p.get('productDescription') or ''}".strip(),
                            link=link, rok=int(data[:4]) if data[:4].isdigit() else None, instytucje=inst,
                            status="udzielony", jezyk="pl"))
    return out


def pobierz_wszystko(con: sqlite3.Connection, log=print) -> int:
    token = _postep(con, "radon_patenty:token")
    razem = 0
    while True:
        params = {"resultNumbers": 100}
        if token:
            params["token"] = token
        r = siec.pobierz(API, params=params, timeout=60)
        if r.status_code != 200:
            log(f"radon_patenty: HTTP {r.status_code}, przerywam")
            break
        d = r.json()
        if not d.get("results"):
            break
        razem += db.zapisz_dokumenty(con, parsuj(d))
        nowy = (d.get("pagination") or {}).get("token")
        if not nowy or nowy == token:
            break
        token = _postep(con, "radon_patenty:token", nowy)
    return razem
