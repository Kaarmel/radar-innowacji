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
# taksonomia wojewodztwa_projekty (GET /wp-json/wp/v2/wojewodztwa_projekty, 21.11.2026)
WOJ = {"128": "dolnośląskie", "159": "kujawsko-pomorskie", "183": "lubelskie", "208": "lubuskie", "223": "łódzkie",
       "248": "małopolskie", "271": "mazowieckie", "314": "opolskie", "327": "podkarpackie", "353": "podlaskie",
       "371": "pomorskie", "392": "śląskie", "429": "świętokrzyskie", "444": "warmińsko-mazurskie", "466": "wielkopolskie",
       "502": "zachodniopomorskie", "724": "ogólnopolski"}
CALA_POLSKA = "pl"


def _wojewodztwo(p: dict) -> str | None:
    nazwy = [WOJ[str(i)] for i in (p.get("wojewodztwa_projekty") or []) if str(i) in WOJ]
    return ", ".join(dict.fromkeys(nazwy)) or None


def parsuj(surowe: list[dict]) -> list[Dokument]:
    out = []
    for p in surowe:
        tytul = bez_html(htmlmod.unescape((p.get("title") or {}).get("rendered", "")))
        opis = bez_html((p.get("content") or {}).get("rendered", ""))
        if not tytul:
            continue
        out.append(Dokument(id=f"mapadotacji:{p['id']}", zrodlo="mapadotacji", typ="projekt", tytul=tytul, opis=opis,
                            link=p.get("link") or f"https://mapadotacji.gov.pl/projekty/{p['id']}/", wojewodztwo=_wojewodztwo(p)))
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


def pobierz_wszystko(con: sqlite3.Connection, woj: str = CALA_POLSKA, log=print) -> int:
    """Wznawialne: pamięta ostatnią pobraną stronę w tabeli postep. woj="pl": cała Polska, inaczej id województwa."""
    filtr = {} if woj == CALA_POLSKA else {"wojewodztwa_projekty": woj}
    r = siec.pobierz(API, params={**filtr, "per_page": 1})
    stron = math.ceil(int(r.headers.get("X-WP-Total", "0")) / 100)
    klucz = f"mapadotacji:{woj}"
    start = int(_postep(con, klucz) or 0) + 1
    razem = 0
    for strona in range(start, stron + 1):
        # stałe sortowanie po id: domyślne (po dacie, z remisami) gubi i dubluje wpisy między stronami
        r = siec.pobierz(API, params={**filtr, "per_page": 100, "page": strona, "orderby": "id", "order": "asc"}, timeout=60)
        if r.status_code != 200:
            log(f"mapadotacji: strona {strona} → HTTP {r.status_code}, przerywam (ponowne uruchomienie wznowi)")
            break
        razem += db.zapisz_dokumenty(con, parsuj(json.loads(r.text)))
        _postep(con, klucz, str(strona))
        if strona % 20 == 0:
            log(f"mapadotacji: {strona}/{stron}")
    return razem


def pobierz_od_konca(con: sqlite3.Connection, woj: str = CALA_POLSKA, log=print, koniec_po: int = 5) -> int:
    """Dopełnienie od najnowszych projektów: strony malejąco po id, aż koniec_po stron z rzędu jest już w bazie
    (pojedyncza znana strona to za mało: wcześniejsze pobrania zostawiają wyspy). Potrzebne, gdy strony z dużym
    przesunięciem nie odpowiadają. Wznawialne (osobny klucz w tabeli postep)."""
    filtr = {} if woj == CALA_POLSKA else {"wojewodztwa_projekty": woj}
    klucz = f"mapadotacji:{woj}:od_konca"
    strona = int(_postep(con, klucz) or 0) + 1
    razem = 0
    znanych_z_rzedu = 0
    while True:
        r = siec.pobierz(API, params={**filtr, "per_page": 100, "page": strona, "orderby": "id", "order": "desc"}, timeout=90)
        if r.status_code != 200:
            log(f"mapadotacji (od końca): strona {strona} → HTTP {r.status_code}, przerywam (ponowne uruchomienie wznowi)")
            break
        docs = parsuj(json.loads(r.text))
        if not docs:
            break
        ids = [d.id for d in docs]
        znane = con.execute(f"SELECT count(*) FROM dokument WHERE id IN ({','.join('?' * len(ids))})", ids).fetchone()[0]
        razem += db.zapisz_dokumenty(con, docs)
        _postep(con, klucz, str(strona))
        znanych_z_rzedu = znanych_z_rzedu + 1 if znane == len(ids) else 0
        if znanych_z_rzedu >= koniec_po:
            log(f"mapadotacji (od końca): {koniec_po} stron z rzędu już w bazie (do strony {strona}), koniec")
            break
        if strona % 20 == 0:
            log(f"mapadotacji (od końca): strona {strona}")
        strona += 1
    return razem
