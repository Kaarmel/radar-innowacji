"""Strona główna: na pierwszym ekranie ostatnie wykrycie z dowodami (cytat, cztery filtry z procentami), potem lejek ostatniego przebiegu."""
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


def test_pierwszy_ekran_woli_wykrycie_bez_flag(klient):
    """Na pierwszym ekranie najnowsze wykrycie, które przeszło wszystkie filtry bez flag; nowsze „do przeglądu” zostaje na liście."""
    con = db.polacz()
    starsze = _wykrycie(con, "Aplikacja do zgłaszania zwierząt", "aplikacja przesyła zgłoszenie z lokalizacją")
    with con:
        con.execute("UPDATE zgloszenie SET werdykt='dalej' WHERE id=?", (starsze,))
    _wykrycie(con, "Instalacje OZE w szkołach", "panele i magazyny energii")
    s = klient.get("/").text
    karta = s[s.index('class="dowod-karta"'):s.index("Ostatnio wykryte przez radar")]
    assert "Aplikacja do zgłaszania zwierząt" in karta and "Ostatnie wykrycie bez flag" in karta
    assert "Instalacje OZE w szkołach" in s[s.index("Ostatnio wykryte przez radar"):]


def test_odrzucone_przez_analityka_nie_trafia_na_pierwszy_ekran(klient):
    con = db.polacz()
    _wykrycie(con, "Pracownia robotyki", "roboty z drukarki 3D")
    zle = _wykrycie(con, "Szkolenie z pierwszej pomocy", "pokaz dla uczniów")
    assert klient.post(f"/karta/{zle}/decyzja", data={"decyzja": "odrzuc", "powod": "Wydarzenie, nie innowacja"}).status_code == 200
    s = klient.get("/").text
    assert "Szkolenie z pierwszej pomocy" not in s and "Pracownia robotyki" in s[s.index('class="dowod-karta"'):]


def test_start_bez_statystyk_radaru(klient, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DANE", tmp_path)
    r = klient.get("/")
    assert r.status_code == 200 and 'class="lejek"' not in r.text
