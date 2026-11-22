"""Radar WWW co godzinę i na żądanie: jeden przebieg naraz (blokada pliku), przycisk na stronie głównej z przerwą 10 minut,
lejek z całej historii radaru (przy przebiegach co godzinę pojedynczy przebieg zwykle nie ma nic nowego)."""
import json
import time

from radar import app as A
from radar import config, db, slowniki
from radar.zrodla import www

from .test_app import klient  # noqa: F401


def test_blokada_jeden_przebieg_naraz(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    assert www.trwa() is None
    with www.blokada() as mam:
        assert mam is True and www.trwa() is not None
        with www.blokada() as druga:
            assert druga is False
    assert www.trwa() is None


def test_uruchom_pomija_gdy_inny_przebieg_trwa(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    monkeypatch.setattr(config, "BAZA", tmp_path / "t.sqlite")
    with www.blokada():
        assert www.uruchom(db.polacz(), log=lambda *_: None) == {"pominiety": "inny przebieg trwa"}


def test_harmonogram_co_godzine():
    assert slowniki.HARMONOGRAM["www"]["co_ile"].startswith("co godzinę")


def test_przycisk_sprawdz_teraz_uruchamia_radar_raz(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    wywolania = []
    monkeypatch.setattr(A, "_radar_w_tle", lambda: wywolania.append(1))
    s = klient.get("/").text
    assert 'action="/radar/sprawdz-teraz"' in s and "co godzinę" in s
    r = klient.post("/radar/sprawdz-teraz", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/?radar=uruchomiony") and wywolania == [1]
    assert "Radar sprawdza źródła teraz" in klient.get("/").text
    r = klient.post("/radar/sprawdz-teraz", follow_redirects=False)
    assert r.headers["location"].startswith("/?radar=trwa") and wywolania == [1]


def test_sprawdz_teraz_najwyzej_raz_na_10_minut(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    (tmp_path / "radar_statystyki.json").write_text(json.dumps({"start": time.time() - 300, "koniec": time.time() - 120, "wpisow": 5}))
    wywolania = []
    monkeypatch.setattr(A, "_radar_w_tle", lambda: wywolania.append(1))
    r = klient.post("/radar/sprawdz-teraz", follow_redirects=False)
    assert r.headers["location"].startswith("/?radar=za_wczesnie") and wywolania == []
    assert "najwyżej raz na 10 minut" in klient.get("/?radar=za_wczesnie").text


def test_lejek_z_calej_historii_radaru(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    (tmp_path / "radar_statystyki.json").write_text(json.dumps({"start": 1795293483.0, "koniec": 1795294201.2, "zrodel": 172, "kanalow": 125,
                                                               "wpisow": 1510}))
    con = db.polacz()
    www._widziane(con)
    with con:
        con.executemany("INSERT INTO radar_widziane VALUES(?,?,?,?)",
                        [(f"https://s.pl/{i}", 1, "tak" if i < 3 else ("nie" if i < 10 else None), 0.0) for i in range(1510)])
    s = klient.get("/").text
    lejek = s[s.index('class="lejek"'):]
    for tekst in ("Od początku działania radaru", "<b>1 510</b>", "<b>10</b>", "<b>3</b>", "Ostatni przebieg: 21.11.2026, 21:50", "<b>172</b>"):
        assert tekst in lejek, tekst
