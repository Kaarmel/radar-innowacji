"""SQLite: dokumenty (FTS5, BM25), statystyka df rdzeni, zgłoszenia, wyniki, decyzje."""
import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from . import config
from .model import Dokument, Rekomendacja, WynikFiltra, Zgloszenie
from .tekst import bez_diakrytykow, rdzen, tokeny

SCHEMAT = """
CREATE TABLE IF NOT EXISTS dokument(
  id TEXT PRIMARY KEY, zrodlo TEXT, typ TEXT, tytul TEXT, opis TEXT, link TEXT, rok INTEGER,
  instytucje TEXT, wojewodztwo TEXT, status TEXT, jezyk TEXT, pobrano_at REAL);
CREATE VIRTUAL TABLE IF NOT EXISTS dokument_fts USING fts5(tytul, opis, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS df(termin TEXT PRIMARY KEY, liczba INTEGER);
CREATE TABLE IF NOT EXISTS zgloszenie(
  id INTEGER PRIMARY KEY AUTOINCREMENT, wejscie TEXT, tytul TEXT, opis TEXT, link TEXT, instytucja TEXT,
  typ_instytucji TEXT, typ_innowacji TEXT, etap TEXT, wiek_przedzial TEXT, opis_en TEXT, cytat TEXT,
  demo INTEGER, organizacja TEXT, utworzono_at REAL, status TEXT DEFAULT 'nowe',
  werdykt TEXT, komorka TEXT, rekomendacje TEXT, partnerzy TEXT, pokrycie TEXT, czas_s REAL, koszt_usd REAL, zrodlo_dok TEXT);
CREATE TABLE IF NOT EXISTS ocena(zgl_id INTEGER PRIMARY KEY, wynik REAL, dane TEXT);
CREATE TABLE IF NOT EXISTS wynik(
  zgl_id INTEGER, filtr TEXT, procent REAL, pasmo TEXT, dowody TEXT, uwaga TEXT, wlasna_praca INTEGER,
  PRIMARY KEY(zgl_id, filtr));
CREATE TABLE IF NOT EXISTS decyzja(
  id INTEGER PRIMARY KEY AUTOINCREMENT, zgl_id INTEGER, decyzja TEXT, powod TEXT, kiedy REAL);
"""


def polacz(sciezka: Path | None = None) -> sqlite3.Connection:
    sciezka = Path(sciezka or config.BAZA)
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(sciezka, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")  # kilka procesów pobierania naraz
    con.executescript(SCHEMAT)
    _migruj(con)
    return con


def _migruj(con: sqlite3.Connection) -> None:
    """Kolumny dodane po pierwszym wdrożeniu (CREATE TABLE IF NOT EXISTS ich nie doda do istniejącej tabeli)."""
    kolumny = {r[1] for r in con.execute("PRAGMA table_info(zgloszenie)")}
    if "zrodlo_dok" not in kolumny:
        with con:
            con.execute("ALTER TABLE zgloszenie ADD COLUMN zrodlo_dok TEXT")


def _rdzenie(tytul: str, opis: str) -> set[str]:
    return {rdzen(t) for t in tokeny(f"{tytul} {opis}")}


def _do_dokumentu(r: sqlite3.Row) -> Dokument:
    return Dokument(id=r["id"], zrodlo=r["zrodlo"], typ=r["typ"], tytul=r["tytul"], opis=r["opis"], link=r["link"],
                    rok=r["rok"], instytucje=json.loads(r["instytucje"] or "[]"), wojewodztwo=r["wojewodztwo"],
                    status=r["status"], jezyk=r["jezyk"])


def zapisz_dokumenty(con: sqlite3.Connection, docs: list[Dokument]) -> int:
    """Upsert po id: aktualizuje FTS i licznik df (stare rdzenie odejmowane)."""
    teraz = time.time()
    with con:
        for d in docs:
            stary = con.execute("SELECT rowid, tytul, opis, instytucje FROM dokument WHERE id=?", (d.id,)).fetchone()
            if stary:
                if not d.instytucje and stary["instytucje"]:  # beneficjent dociągnięty ze strony projektu zostaje
                    d.instytucje = json.loads(stary["instytucje"])
                for t in _rdzenie(stary["tytul"], stary["opis"]):
                    con.execute("UPDATE df SET liczba=liczba-1 WHERE termin=?", (t,))
                con.execute("DELETE FROM dokument_fts WHERE rowid=?", (stary["rowid"],))
                con.execute("""UPDATE dokument SET zrodlo=?,typ=?,tytul=?,opis=?,link=?,rok=?,instytucje=?,wojewodztwo=?,
                               status=?,jezyk=?,pobrano_at=? WHERE id=?""",
                            (d.zrodlo, d.typ, d.tytul, d.opis, d.link, d.rok, json.dumps(d.instytucje, ensure_ascii=False),
                             d.wojewodztwo, d.status, d.jezyk, teraz, d.id))
                rowid = stary["rowid"]
            else:
                rowid = con.execute("""INSERT INTO dokument(id,zrodlo,typ,tytul,opis,link,rok,instytucje,wojewodztwo,status,jezyk,pobrano_at)
                                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (d.id, d.zrodlo, d.typ, d.tytul, d.opis, d.link, d.rok,
                                     json.dumps(d.instytucje, ensure_ascii=False), d.wojewodztwo, d.status, d.jezyk, teraz)).lastrowid
            # FTS dostaje tekst bez polskich znaków: unicode61 nie rozkłada "ł", więc normalizujemy sami
            con.execute("INSERT INTO dokument_fts(rowid, tytul, opis) VALUES(?,?,?)",
                        (rowid, bez_diakrytykow(d.tytul), bez_diakrytykow(d.opis)))
            for t in _rdzenie(d.tytul, d.opis):
                con.execute("INSERT INTO df(termin, liczba) VALUES(?,1) ON CONFLICT(termin) DO UPDATE SET liczba=liczba+1", (t,))
    return len(docs)


def szukaj(con: sqlite3.Connection, terminy: list[str], limit: int = 50, typ: str | None = None) -> list[tuple[Dokument, float]]:
    """BM25 po tytule i opisie; terminy to rdzenie, dopasowanie prefiksowe. Wynik: (dokument, wynik > 0)."""
    czyste = [t for t in (tokeny(" ".join(terminy))) if t]
    if not czyste:
        return []
    zapytanie = " OR ".join(f'"{t}"*' for t in dict.fromkeys(czyste))
    sql = """SELECT d.*, -bm25(dokument_fts, 3.0, 1.0) AS wynik FROM dokument_fts
             JOIN dokument d ON d.rowid = dokument_fts.rowid WHERE dokument_fts MATCH ?"""
    args: list = [zapytanie]
    if typ:
        sql += " AND d.typ = ?"
        args.append(typ)
    sql += " ORDER BY bm25(dokument_fts, 3.0, 1.0) LIMIT ?"
    args.append(limit)
    return [(_do_dokumentu(r), r["wynik"]) for r in con.execute(sql, args)]


def dokument(con: sqlite3.Connection, id: str) -> Dokument | None:
    r = con.execute("SELECT * FROM dokument WHERE id=?", (id,)).fetchone()
    return _do_dokumentu(r) if r else None


def stan_zrodel(con: sqlite3.Connection) -> dict[str, dict]:
    """Aktualność danych: ile dokumentów, kiedy pobrane (od–do), najnowszy rok w danych; radar WWW z radar_widziane."""
    con.execute("CREATE INDEX IF NOT EXISTS dokument_stan ON dokument(zrodlo, pobrano_at, rok)")
    out = {r[0]: {"dokumentow": r[1], "pobrano_od": r[2] or 0.0, "pobrano_do": r[3] or 0.0, "najnowszy_rok": r[4]}
           for r in con.execute("SELECT zrodlo, count(*), min(pobrano_at), max(pobrano_at), max(rok) FROM dokument GROUP BY zrodlo")}
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='radar_widziane'").fetchone():
        n, do = con.execute("SELECT count(*), max(kiedy) FROM radar_widziane").fetchone()
        if n:  # stan radaru = ostatni przebieg (tabela tylko rośnie, więc min() zamarzłby na pierwszym dniu)
            out["www"] = {"dokumentow": n, "pobrano_od": do, "pobrano_do": do, "najnowszy_rok": None}
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='postep'").fetchone():
        for klucz, wartosc in con.execute("SELECT klucz, wartosc FROM postep WHERE klucz LIKE '%:pelne'"):
            z = klucz.rsplit(":", 1)[0]
            if z in out:  # znacznik ukończonego pełnego pobrania (pobierz --od-nowa) zamiast najstarszego rekordu
                out[z]["pobrano_od"] = float(wartosc)
    return out


def liczba_dokumentow(con: sqlite3.Connection) -> dict[str, int]:
    return {r[0]: r[1] for r in con.execute("SELECT zrodlo, count(*) FROM dokument GROUP BY zrodlo")}


def funkcja_df(con: sqlite3.Connection) -> tuple[Callable[[str], int], int]:
    n = con.execute("SELECT count(*) FROM dokument").fetchone()[0]
    pamiec: dict[str, int] = {}

    def df(termin: str) -> int:
        if termin not in pamiec:
            r = con.execute("SELECT liczba FROM df WHERE termin=?", (termin,)).fetchone()
            pamiec[termin] = max(r[0], 0) if r else 0
        return pamiec[termin]
    return df, n


_POLA_ZGL = ["wejscie", "tytul", "opis", "link", "instytucja", "typ_instytucji", "typ_innowacji", "etap",
             "wiek_przedzial", "opis_en", "cytat", "demo", "organizacja", "zrodlo_dok"]


def zapisz_zgloszenie(con: sqlite3.Connection, z: Zgloszenie) -> int:
    with con:
        if z.id:
            con.execute(f"UPDATE zgloszenie SET {', '.join(p + '=?' for p in _POLA_ZGL)} WHERE id=?",
                        [getattr(z, p) for p in _POLA_ZGL] + [z.id])
            return z.id
        return con.execute(f"INSERT INTO zgloszenie({', '.join(_POLA_ZGL)}, utworzono_at) VALUES({', '.join('?' * len(_POLA_ZGL))}, ?)",
                           [getattr(z, p) for p in _POLA_ZGL] + [time.time()]).lastrowid


def zgloszenie(con: sqlite3.Connection, id: int) -> Zgloszenie | None:
    r = con.execute("SELECT * FROM zgloszenie WHERE id=?", (id,)).fetchone()
    if not r:
        return None
    return Zgloszenie(id=r["id"], **{p: (bool(r[p]) if p == "demo" else r[p]) for p in _POLA_ZGL})


def zapisz_wyniki(con: sqlite3.Connection, zgl_id: int, wyniki: list[WynikFiltra], werdykt: str, komorka: str,
                  rekomendacje: list[Rekomendacja], partnerzy: list[str], czas_s: float, koszt_usd: float,
                  pokrycie: dict | None = None) -> None:
    with con:
        for w in wyniki:
            con.execute("INSERT OR REPLACE INTO wynik VALUES(?,?,?,?,?,?,?)",
                        (zgl_id, w.filtr, w.procent, w.pasmo, json.dumps(w.dowody, ensure_ascii=False), w.uwaga, int(w.wlasna_praca)))
        con.execute("""UPDATE zgloszenie SET status='gotowe', werdykt=?, komorka=?, rekomendacje=?, partnerzy=?, pokrycie=?,
                       czas_s=?, koszt_usd=? WHERE id=?""",
                    (werdykt, komorka, json.dumps([asdict(r) for r in rekomendacje], ensure_ascii=False),
                     json.dumps(partnerzy, ensure_ascii=False), json.dumps(pokrycie or {}, ensure_ascii=False),
                     czas_s, koszt_usd, zgl_id))


def ustaw_status(con: sqlite3.Connection, zgl_id: int, status: str) -> None:
    with con:
        con.execute("UPDATE zgloszenie SET status=? WHERE id=?", (status, zgl_id))


def karta(con: sqlite3.Connection, zgl_id: int) -> dict | None:
    r = con.execute("SELECT * FROM zgloszenie WHERE id=?", (zgl_id,)).fetchone()
    if not r:
        return None
    k = dict(r)
    for p in ("rekomendacje", "partnerzy", "pokrycie"):
        k[p] = json.loads(k[p]) if k[p] else ([] if p != "pokrycie" else {})
    k["demo"] = bool(k["demo"])
    k["wyniki"] = [dict(filtr=w["filtr"], procent=w["procent"], pasmo=w["pasmo"], dowody=json.loads(w["dowody"]),
                        uwaga=w["uwaga"], wlasna_praca=bool(w["wlasna_praca"]))
                   for w in con.execute("SELECT * FROM wynik WHERE zgl_id=? ORDER BY CASE filtr WHEN 'plagiat' THEN 1 WHEN 'kopia' THEN 2 WHEN 'patent' THEN 3 ELSE 4 END", (zgl_id,))]
    o = con.execute("SELECT dane FROM ocena WHERE zgl_id=?", (zgl_id,)).fetchone()
    k["potencjal"] = json.loads(o["dane"]) if o else None
    k["decyzje"] = [dict(d) for d in con.execute("SELECT decyzja, powod, kiedy FROM decyzja WHERE zgl_id=? ORDER BY kiedy", (zgl_id,))]
    from .klasyfikacja import profil
    k["klasyfikacja"] = profil(k)
    return k


def zapisz_ocene(con: sqlite3.Connection, zgl_id: int, ocena: dict) -> None:
    with con:
        con.execute("INSERT OR REPLACE INTO ocena VALUES(?,?,?)", (zgl_id, ocena.get("wynik"), json.dumps(ocena, ensure_ascii=False)))


def zapisz_decyzje(con: sqlite3.Connection, zgl_id: int, decyzja: str, powod: str) -> None:
    with con:
        con.execute("INSERT INTO decyzja(zgl_id, decyzja, powod, kiedy) VALUES(?,?,?,?)", (zgl_id, decyzja, powod, time.time()))
