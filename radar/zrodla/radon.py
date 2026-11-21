"""RAD-on (OPI): projekty naukowe z POL-on. Zapisujemy instytucje, nigdy kierowników projektów (dane osobowe)."""
import sqlite3

from .. import db, siec
from ..model import Dokument
from .mapadotacji import _postep

API = "https://radon.nauka.gov.pl/opendata/polon/projects"


def parsuj(surowe: dict) -> list[Dokument]:
    out = []
    for p in surowe.get("results", []):
        tytul = p.get("projectTitlePl") or p.get("projectTitleEn") or ""
        opis = p.get("projectAbstractPl") or p.get("projectAbstractEn") or ""
        if not tytul:
            continue
        jezyk = "pl" if (p.get("projectAbstractPl") or (p.get("projectTitlePl") and not p.get("projectAbstractEn"))) else "en"
        start = p.get("projectStartDate") or ""
        instytucje = [i["institutionName"] for i in (p.get("implementingInstitutions") or []) if i.get("institutionName")]
        if not instytucje and p.get("entityShowingAchievementsName"):
            instytucje = [p["entityShowingAchievementsName"]]
        if p.get("keywords"):
            opis = f"{opis}\nSłowa kluczowe: {p['keywords']}"
        out.append(Dokument(id=f"radon:{p['projectUuid']}", zrodlo="radon", typ="projekt", tytul=tytul, opis=opis,
                            link=f"https://radon.nauka.gov.pl/dane/projekty-naukowe?uuid={p['projectUuid']}",
                            rok=int(start[:4]) if start[:4].isdigit() else None, instytucje=instytucje, jezyk=jezyk))
    return out


def pobierz_wszystko(con: sqlite3.Connection, log=print) -> int:
    """Stronicowanie tokenem; ostatni token w tabeli postep (wznawialne)."""
    token = _postep(con, "radon:token")
    razem, strona = 0, 0
    while True:
        params = {"resultNumbers": 100}
        if token:
            params["token"] = token
        r = siec.pobierz(API, params=params, timeout=60)
        if r.status_code != 200:
            log(f"radon: HTTP {r.status_code}, przerywam (ponowne uruchomienie wznowi)")
            break
        d = r.json()
        if not d.get("results"):
            break
        razem += db.zapisz_dokumenty(con, parsuj(d))
        nowy = (d.get("pagination") or {}).get("token")
        if not nowy or nowy == token:
            break
        token = _postep(con, "radon:token", nowy)
        strona += 1
        if strona % 50 == 0:
            log(f"radon: {razem} projektów")
    return razem
