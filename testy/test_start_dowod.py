"""Strona główna: na pierwszym ekranie ostatnie wykrycie z dowodami (cytat, cztery filtry z procentami), potem lejek ostatniego przebiegu."""
import json

from radar import config, db
from radar.model import WynikFiltra, Zgloszenie

from .test_app import klient  # noqa: F401


def _wykrycie(con, tytul, cytat):
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="radar", tytul=tytul, opis="Opis rozwiązania.", link="https://szkola.pl/a",
                                               instytucja="ZST w Jaśle", typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna",
                                               etap="prototyp", wiek_przedzial="16_30", organizacja="pci", cytat=cytat))
    db.zapisz_wyniki(con, zid, [WynikFiltra("plagiat", 0.0, "zielone", []), WynikFiltra("kopia", 31.9, "zielone", []),
                                WynikFiltra("patent", 20.5, "zielone", []), WynikFiltra("nowosc", 40.0, "zolte", [])],
                     "do_przegladu", "inni", [], [], 1.0, 0.001)
    db.zapisz_ocene(con, zid, {"wynik": 38, "kryteria": [], "uwaga": "", "formula": ""})
    return zid


def test_start_zaczyna_od_ostatniego_wykrycia_z_dowodami(klient):
    zid = _wykrycie(db.polacz(), "Systemy OZE w szkołach", "kompletne systemy z magazynami energii")
    s = klient.get("/").text
    s = s[s.index("<main"):]
    assert s.index('class="dowod-karta"') < s.index("Ostatnio wykryte przez radar")
    karta = s[s.index('class="dowod-karta"'):s.index("Ostatnio wykryte przez radar")]
    for tekst in ("Systemy OZE w szkołach", "ZST w Jaśle", "kompletne systemy z magazynami energii", "Plagiat", "0,0%",
                  "Kopia pomysłu", "31,9%", "Patent", "20,5%", "Nowość", "40,0%", "<b>38</b>", f'href="/karta/{zid}"'):
        assert tekst in karta, tekst


def test_odrzucone_przez_analityka_nie_trafia_na_pierwszy_ekran(klient):
    con = db.polacz()
    _wykrycie(con, "Pracownia robotyki", "roboty z drukarki 3D")
    zle = _wykrycie(con, "Szkolenie z pierwszej pomocy", "pokaz dla uczniów")
    assert klient.post(f"/karta/{zle}/decyzja", data={"decyzja": "odrzuc", "powod": "Wydarzenie, nie innowacja"}).status_code == 200
    s = klient.get("/").text
    assert "Szkolenie z pierwszej pomocy" not in s and "Pracownia robotyki" in s[s.index('class="dowod-karta"'):]


def test_lejek_ostatniego_przebiegu_radaru(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    (tmp_path / "radar_statystyki.json").write_text(json.dumps({"start": 1795293483.0, "koniec": 1795294201.2, "zrodel": 172, "kanalow": 125,
                                                               "wpisow": 1510, "sygnal": 107, "do_ai": 107, "zgloszen": 9, "innowacje": 9}))
    s = klient.get("/").text
    lejek = s[s.index('class="lejek"'):]
    for tekst in ("Ostatni przebieg radaru", "21.11.2026, 21:50", "<b>172</b>", "<b>1 510</b>", "<b>107</b>", "<b>9</b>"):
        assert tekst in lejek, tekst


def test_start_bez_statystyk_radaru(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    r = klient.get("/")
    assert r.status_code == 200 and 'class="lejek"' not in r.text
