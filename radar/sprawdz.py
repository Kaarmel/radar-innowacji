"""Sprawdzenie jednego zgłoszenia: wyszukiwanie w bazie i źródłach na żądanie, cztery filtry, werdykt, karta."""
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from . import ai, db, filtry, instytucje, organizacje, tekst, werdykt
from .model import Dokument, Zgloszenie
from .zrodla import BrakDostepu, crossref, epo, mapadotacji, openalex

ZRODLA_NA_ZADANIE = {"epo": epo.szukaj, "openalex": openalex.szukaj, "crossref": crossref.szukaj}
ZRODLA_PATENTOWE = {"epo"}
MAX_BENEFICJENTOW = 5  # strona projektu Mapy Dotacji ładuje się kilka sekund


def _poprzednie_zgloszenia(con: sqlite3.Connection, zgl_id: int, limit: int = 2000) -> list[Dokument]:
    wiersze = con.execute("SELECT id, tytul, opis, instytucja, utworzono_at FROM zgloszenie WHERE id != ? ORDER BY id DESC LIMIT ?",
                          (zgl_id, limit))
    return [Dokument(id=f"zgloszenie:{r['id']}", zrodlo="zgloszenie", typ="zgloszenie", tytul=r["tytul"] or "", opis=r["opis"] or "",
                     link=f"/karta/{r['id']}", rok=time.localtime(r["utworzono_at"] or 0).tm_year,
                     instytucje=[r["instytucja"]] if r["instytucja"] else []) for r in wiersze]


def _na_zadanie(terminy_en: list[str]) -> tuple[list[Dokument], list[str], list[str]]:
    """Źródła zewnętrzne równolegle; niedostępne nie przerywają sprawdzenia."""
    if not ZRODLA_NA_ZADANIE:
        return [], [], []
    if not terminy_en:
        return [], [], list(ZRODLA_NA_ZADANIE)
    docs, ok, nie = [], [], []
    with ThreadPoolExecutor(max_workers=len(ZRODLA_NA_ZADANIE)) as pula:
        zadania = {n: pula.submit(f, terminy_en) for n, f in ZRODLA_NA_ZADANIE.items()}
        for nazwa, zad in zadania.items():
            try:
                docs += zad.result()
                ok.append(nazwa)
            except BrakDostepu:
                nie.append(nazwa)
            except Exception:  # nieprzewidziany błąd źródła = źródło niedostępne, nie awaria sprawdzenia
                nie.append(nazwa)
    return docs, ok, nie


def _lokalne(con: sqlite3.Connection, z: Zgloszenie, terminy_en: list[str], df, N) -> list[Dokument]:
    terminy = tekst.terminy(f"{z.tytul}. {z.opis}", n=15, df=df, N=N)
    wyniki = db.szukaj(con, terminy, limit=50) + db.szukaj(con, terminy, limit=20, typ="patent")
    if terminy_en:
        wyniki += db.szukaj(con, terminy_en, limit=20)
    return list({d.id: d for d, _ in wyniki}.values())


def _uzupelnij_beneficjentow(con: sqlite3.Connection, z: Zgloszenie, ranking: list[tuple[float, Dokument]]) -> None:
    """Mapa Dotacji podaje beneficjenta tylko na stronie projektu: pobieramy go dla kilku najbliższych (reguła własnej pracy)."""
    bez = [d for s, d in ranking if d.zrodlo == "mapadotacji" and not d.instytucje]
    trafienia = [d for d in bez if tekst.pokrycie_ngramow(z.opis, f"{d.tytul}. {d.opis}")[0] > 0]
    brakujace = trafienia + [d for d in bez[:8] if d not in trafienia]
    zmienione = []
    for d in brakujace[:MAX_BENEFICJENTOW]:
        try:
            nazwa = mapadotacji.beneficjent(d.link)
        except Exception:
            nazwa = None
        if nazwa:
            d.instytucje = [nazwa]
            zmienione.append(d)
    if zmienione:
        db.zapisz_dokumenty(con, zmienione)


def sprawdz(con: sqlite3.Connection, zgl_id: int) -> dict:
    t0 = time.time()
    z = db.zgloszenie(con, zgl_id)
    if z is None:
        raise KeyError(f"brak zgłoszenia {zgl_id}")
    db.ustaw_status(con, zgl_id, "w_toku")
    koszt: list[float] = []
    try:
        tl, k = ai.tlumacz_zapytanie(z.opis)
        koszt.append(k)
        z.opis_en = tl.get("opis_en") or z.opis_en
        db.zapisz_zgloszenie(con, z)
        terminy_en = tl.get("terminy_en") or []

        df, N = db.funkcja_df(con)
        lokalne = _lokalne(con, z, terminy_en, df, N)
        zewnetrzne, ok, niedostepne = _na_zadanie(terminy_en)
        if zewnetrzne:
            db.zapisz_dokumenty(con, zewnetrzne)  # pamięć podręczna: dowody i radar zostają w bazie
        kandydaci = list({d.id: d for d in lokalne + zewnetrzne}.values())
        poprzednie = _poprzednie_zgloszenia(con, zgl_id)

        ranking = filtry.ranking(z, kandydaci, df, N)
        _uzupelnij_beneficjentow(con, z, ranking)
        obce = [(s, d) for s, d in ranking if not instytucje.ta_sama(z.instytucja, d.instytucje)]

        patenty_dostepne = any(n in ok for n in ZRODLA_PATENTOWE)
        wyniki = [
            filtry.plagiat(z, kandydaci + poprzednie),
            filtry.kopia(z, kandydaci + poprzednie, df, N, koszt=koszt),
            filtry.patent(z, kandydaci, df, N, dostepne=patenty_dostepne, koszt=koszt),
            filtry.nowosc(z, [d for s, d in obce[:10] if s > 0], koszt=koszt),
        ]
        profil = organizacje.wczytaj(z.organizacja)
        podobne = [d for s, d in ranking[:20] if s > 0]
        lokalne_liczby = db.liczba_dokumentow(con)
        pokrycie = {"zrodla": sorted(set(lokalne_liczby) - {"zgloszenie"} | set(ok)),
                    "lokalne": lokalne_liczby, "dokumentow": sum(lokalne_liczby.values()),
                    "kandydatow": len(kandydaci), "zgloszen_porownanych": len(poprzednie), "niedostepne": niedostepne}
        db.zapisz_wyniki(con, zgl_id, wyniki, werdykt.werdykt(wyniki), werdykt.komorka(z, profil),
                         werdykt.sciezka(z, wyniki, podobne, profil), werdykt.partnerzy(z, podobne),
                         round(time.time() - t0, 1), round(sum(koszt), 5), pokrycie=pokrycie)
    except Exception:
        db.ustaw_status(con, zgl_id, "blad")
        raise
    return db.karta(con, zgl_id)
