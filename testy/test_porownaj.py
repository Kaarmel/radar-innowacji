"""FAQ: wyszukiwanie, filtrowanie i porównywanie innowacji."""
from radar import db
from radar.model import Dokument
from testy.test_app import OPIS, POLA, klient  # noqa: F401


def _dwa(klient):
    a = klient.post("/zglos", data=POLA, follow_redirects=False).headers["location"].rsplit("/", 1)[1]
    b = klient.post("/zglos", data={**POLA, "tytul": "Rejestr awarii oświetlenia", "typ_innowacji": "organizacyjna",
                                    "typ_instytucji": "jst", "wiek_przedzial": "powyzej_30"},
                    follow_redirects=False).headers["location"].rsplit("/", 1)[1]
    return a, b


def test_porownanie_dwoch_kart(klient):
    a, b = _dwa(klient)
    r = klient.get(f"/porownaj?id={a}&id={b}")
    assert r.status_code == 200
    for s in ("Filtr mikroplastiku", "Rejestr awarii oświetlenia", "Obszar", "TRL", "Wiarygodność", "Potencjał",
              "technologiczny", "administracyjny", "Plagiat"):
        assert s in r.text, s


def test_porownanie_wymaga_2_do_4_istniejacych(klient):
    a, _ = _dwa(klient)
    assert klient.get(f"/porownaj?id={a}").status_code == 400
    assert klient.get(f"/porownaj?id={a}&id=9999").status_code == 404


def test_katalog_filtr_obszaru_i_porownanie(klient):
    _dwa(klient)
    t = klient.get("/kolejka", params={"obszar": "administracyjny"}).text
    assert "Rejestr awarii oświetlenia" in t and "Filtr mikroplastiku" not in t
    k = klient.get("/kolejka").text
    assert 'action="/porownaj"' in k and 'name="id"' in k and 'name="obszar"' in k


def test_szukaj_filtr_zrodla_i_roku(klient):
    con = db.polacz()
    db.zapisz_dokumenty(con, [
        Dokument(id="radon:1", zrodlo="radon", typ="projekt", tytul="Filtr wody mikroplastik", opis=OPIS, link="https://r/1", rok=2019),
        Dokument(id="mapadotacji:2", zrodlo="mapadotacji", typ="projekt", tytul="Filtr wody mikroplastik", opis=OPIS,
                 link="https://m/2", rok=2024)])
    def ids(**p):
        w = klient.get("/api/szukaj", params={"q": "filtr wody mikroplastik", **p}).json()
        return sorted(d["id"] for docs in w["dokumenty"].values() for d in docs)
    assert ids() == ["mapadotacji:2", "radon:1"]
    assert ids(zrodlo="radon") == ["radon:1"]
    assert ids(rok_od=2020) == ["mapadotacji:2"]
    s = klient.get("/szukaj", params={"q": "filtr wody", "zrodlo": "radon"}).text
    assert 'name="zrodlo"' in s and 'name="rok_od"' in s


def test_szukaj_filtr_wojewodztwa(klient):
    """Produkt dla całej Polski: projekty z województwa (Mapa Dotacji podaje je dla każdego projektu) i ogólnopolskie."""
    con = db.polacz()
    docs = [("mapadotacji:1", "podkarpackie"), ("mapadotacji:2", "śląskie"), ("mapadotacji:3", "ogólnopolski"),
            ("mapadotacji:4", "podkarpackie, śląskie"), ("radon:5", None)]
    db.zapisz_dokumenty(con, [Dokument(id=i, zrodlo=i.split(":")[0], typ="projekt", tytul="Filtr wody mikroplastik", opis=OPIS,
                                       link=f"https://x/{i}", wojewodztwo=w) for i, w in docs])
    w = klient.get("/api/szukaj", params={"q": "filtr wody mikroplastik", "woj": "śląskie"}).json()
    assert sorted(d["id"] for docs in w["dokumenty"].values() for d in docs) == ["mapadotacji:2", "mapadotacji:3", "mapadotacji:4"]
    s = klient.get("/szukaj", params={"q": "filtr wody", "woj": "śląskie"}).text
    assert 'name="woj"' in s and '<option value="śląskie" selected' in s
