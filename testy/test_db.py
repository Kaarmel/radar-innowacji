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
