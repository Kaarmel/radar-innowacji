"""Mapa Dotacji UE (mapadotacji.gov.pl, WordPress REST): projekty z opisami. Beneficjent tylko ze strony HTML."""
import html as htmlmod
import json
import math
import re
import sqlite3

from .. import db, siec
from ..model import Dokument
from ..tekst import bez_html

API = "https://mapadotacji.gov.pl/wp-json/wp/v2/projekty"
WOJ = {"327": "podkarpackie"}


def parsuj(surowe: list[dict], wojewodztwo: str | None = "podkarpackie") -> list[Dokument]:
    out = []
    for p in surowe:
        tytul = bez_html(htmlmod.unescape((p.get("title") or {}).get("rendered", "")))
        opis = bez_html((p.get("content") or {}).get("rendered", ""))
        if not tytul:
            continue
        out.append(Dokument(id=f"mapadotacji:{p['id']}", zrodlo="mapadotacji", typ="projekt", tytul=tytul, opis=opis,
                            link=p.get("link") or f"https://mapadotacji.gov.pl/projekty/{p['id']}/", wojewodztwo=wojewodztwo))
    return out


def beneficjent_z_html(strona: str) -> str | None:
    m = re.search(r'text-up">\s*nazwa beneficjenta\s*</div>\s*<div class="[^"]*text-down">(.*?)</div>', strona, re.S | re.I)
    return bez_html(m.group(1)) if m else None


def beneficjent(link: str) -> str | None:
    try:
        r = siec.pobierz(link, timeout=40)
        return beneficjent_z_html(r.text) if r.status_code == 200 else None
    except Exception:
        return None


def _postep(con: sqlite3.Connection, klucz: str, wartosc: str | None = None) -> str | None:
    con.execute("CREATE TABLE IF NOT EXISTS postep(klucz TEXT PRIMARY KEY, wartosc TEXT)")
    if wartosc is not None:
        with con:
            con.execute("INSERT OR REPLACE INTO postep VALUES(?,?)", (klucz, wartosc))
        return wartosc
    r = con.execute("SELECT wartosc FROM postep WHERE klucz=?", (klucz,)).fetchone()
    return r[0] if r else None


def pobierz_wszystko(con: sqlite3.Connection, woj: str = "327", log=print) -> int:
    """Wznawialne: pamięta ostatnią pobraną stronę w tabeli postep."""
    r = siec.pobierz(API, params={"wojewodztwa_projekty": woj, "per_page": 1})
    stron = math.ceil(int(r.headers.get("X-WP-Total", "0")) / 100)
    klucz = f"mapadotacji:{woj}"
    start = int(_postep(con, klucz) or 0) + 1
    razem = 0
    for strona in range(start, stron + 1):
        # stałe sortowanie po id: domyślne (po dacie, z remisami) gubi i dubluje wpisy między stronami
        r = siec.pobierz(API, params={"wojewodztwa_projekty": woj, "per_page": 100, "page": strona, "orderby": "id",
                                      "order": "asc"}, timeout=60)
        if r.status_code != 200:
            log(f"mapadotacji: strona {strona} → HTTP {r.status_code}, przerywam (ponowne uruchomienie wznowi)")
            break
        razem += db.zapisz_dokumenty(con, parsuj(json.loads(r.text), WOJ.get(woj)))
        _postep(con, klucz, str(strona))
        if strona % 20 == 0:
            log(f"mapadotacji: {strona}/{stron}")
    return razem
