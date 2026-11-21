from radar import db
from radar.model import Dokument


def _baza(tmp_path):
    con = db.polacz(tmp_path / "t.sqlite")
    db.zapisz_dokumenty(con, [
        Dokument(id="t:1", zrodlo="t", typ="projekt", tytul="Rewitalizacja rynku", opis="Remont płyty rynku w gminie.", link="https://a"),
        Dokument(id="t:2", zrodlo="t", typ="projekt", tytul="Filtr mikroplastiku", opis="Filtr wody usuwający mikroplastik, inspirowany skrzelami ryb.", link="https://b"),
        Dokument(id="t:3", zrodlo="t", typ="publikacja", tytul="Źródło danych", opis="Opis źródła danych o wodzie.", link="https://c"),
    ])
    return con


def test_szukaj_zwraca_trafny_dokument_pierwszy(tmp_path):
    con = _baza(tmp_path)
    wyniki = db.szukaj(con, ["mikroplast", "filtr"])
    assert wyniki[0][0].id == "t:2"


def test_zapis_idempotentny(tmp_path):
    con = _baza(tmp_path)
    db.zapisz_dokumenty(con, [Dokument(id="t:1", zrodlo="t", typ="projekt", tytul="Rewitalizacja rynku 2", opis="x", link="https://a")])
    assert db.liczba_dokumentow(con) == {"t": 3}
    assert db.dokument(con, "t:1").tytul == "Rewitalizacja rynku 2"
    assert db.szukaj(con, ["remont"]) == []  # stara treść usunięta z indeksu


def test_diakrytyki(tmp_path):
    con = _baza(tmp_path)
    ids = [d.id for d, _ in db.szukaj(con, ["zrodl"])]
    assert "t:3" in ids


def test_funkcja_df(tmp_path):
    con = _baza(tmp_path)
    df, n = db.funkcja_df(con)
    assert n == 3
    assert df("filtr") == 1 and df("niema") == 0


def test_migracja_starej_bazy(tmp_path):
    import sqlite3
    stara = sqlite3.connect(tmp_path / "s.sqlite")
    stara.execute("CREATE TABLE zgloszenie(id INTEGER PRIMARY KEY AUTOINCREMENT, wejscie TEXT, tytul TEXT, opis TEXT, link TEXT, "
                  "instytucja TEXT, typ_instytucji TEXT, typ_innowacji TEXT, etap TEXT, wiek_przedzial TEXT, opis_en TEXT, cytat TEXT, "
                  "demo INTEGER, organizacja TEXT, utworzono_at REAL, status TEXT DEFAULT 'nowe', werdykt TEXT, komorka TEXT, "
                  "rekomendacje TEXT, partnerzy TEXT, pokrycie TEXT, czas_s REAL, koszt_usd REAL)")
    stara.commit()
    stara.close()
    con = db.polacz(tmp_path / "s.sqlite")
    assert "zrodlo_dok" in {r[1] for r in con.execute("PRAGMA table_info(zgloszenie)")}
    db.polacz(tmp_path / "s.sqlite")  # drugi raz bez błędu


def test_ocena_w_karcie(tmp_path):
    from radar.model import Zgloszenie
    con = db.polacz(tmp_path / "t.sqlite")
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="baza", tytul="T", opis="O", link=None, instytucja="I",
                                               typ_instytucji="firma", typ_innowacji="techniczna", etap="pomysl",
                                               wiek_przedzial="powyzej_30", zrodlo_dok="radon:1"))
    assert db.karta(con, zid)["potencjal"] is None
    db.zapisz_ocene(con, zid, {"wynik": 64, "kryteria": []})
    k = db.karta(con, zid)
    assert k["potencjal"]["wynik"] == 64 and k["zrodlo_dok"] == "radon:1"
