"""Interreg 2021–2027 (programy zarządzane przez Polskę): wykaz projektów XLSX z interreg.gov.pl."""
import datetime
import sqlite3
import tempfile
from pathlib import Path

import openpyxl

from .. import db, siec
from ..model import Dokument

URL = "https://interreg.gov.pl/wp-content/uploads/2026/11/Wykaz_projektow_Interreg_2021-2027_art_49_CPR_20261116.xlsx"
LISTA = "https://interreg.gov.pl/lista-projektow/"


def _kolumna(naglowki: list, poczatek: str) -> int:
    for i, n in enumerate(naglowki):
        if n and str(n).strip().startswith(poczatek):
            return i
    raise KeyError(poczatek)


def parsuj(plik: Path) -> list[Dokument]:
    wiersze = list(openpyxl.load_workbook(plik, read_only=True).active.iter_rows(values_only=True))
    h = next(i for i, w in enumerate(wiersze[:10]) if w and any(str(x or "").startswith("Numer projektu") for x in w))
    n = wiersze[h]
    k = {nazwa: _kolumna(n, p) for nazwa, p in [("nr", "Numer projektu"), ("tytul", "Tytul projektu"), ("opis", "Opis projektu"),
                                                ("start", "Data rozpoczęcia"), ("partnerzy", "Nazwa partnera wiodącego i partnerów"),
                                                ("woj", "Województwo lub region")]}
    out = []
    for w in wiersze[h + 1:]:
        if not w or not w[k["nr"]]:
            continue
        start = w[k["start"]]
        rok = start.year if isinstance(start, (datetime.date, datetime.datetime)) else None
        out.append(Dokument(id=f"interreg:{w[k['nr']]}", zrodlo="interreg", typ="projekt", tytul=str(w[k["tytul"]] or ""),
                            opis=str(w[k["opis"]] or ""), link=LISTA, rok=rok,
                            instytucje=[p.strip() for p in str(w[k["partnerzy"]] or "").split("|") if p.strip()],
                            wojewodztwo=(str(w[k["woj"]]).strip().lower() if w[k["woj"]] else None)))
    return out


def pobierz_wszystko(con: sqlite3.Connection, log=print) -> int:
    r = siec.pobierz(URL, timeout=120)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
        f.write(r.content)
        f.flush()
        return db.zapisz_dokumenty(con, parsuj(Path(f.name)))
