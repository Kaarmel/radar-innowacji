"""Kropki P K Pa N mają małą legendę przy liście wykryć i w kolejce (juror nie musi zgadywać skrótów)."""
from radar import db
from radar.model import Zgloszenie

from .test_app import klient  # noqa: F401


def test_dowody_kryterium_bez_powtorzen(klient):
    """Kilka pytań rubryki może wskazać ten sam dokument; w tabeli potencjału pokazujemy go raz."""
    from .test_app import POLA
    klient.post("/zglos", data=POLA)
    con = db.polacz()
    d = {"tytul": "Rój dronów 2021", "link": "https://radon.example/projekt-1"}
    db.zapisz_ocene(con, 1, {"wynik": 20, "uwaga": "", "formula": "wzór", "kryteria": [
        {"id": "nowosc", "nazwa": "Nowość", "max": 25, "punkty": 6.2, "zrodlo": "AI", "uzasadnienie": "1 z 4", "dowody": [d, d, dict(d)]}]})
    s = klient.get("/karta/1").text
    assert s.count("https://radon.example/projekt-1") == 1


def test_legenda_kropek_na_starcie_i_w_kolejce(klient):
    con = db.polacz()
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="radar", tytul="Aplikacja", opis="Opis.", link="https://x.pl/1",
                                               instytucja="ZST", typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna",
                                               etap="prototyp", wiek_przedzial="16_30", organizacja="pci"))
    with con:
        con.execute("UPDATE zgloszenie SET werdykt='dalej', status='gotowe' WHERE id=?", (zid,))
    for adres in ("/", "/o/pci/kolejka", "/kolejka"):
        s = klient.get(adres).text
        assert 'class="legenda"' in s, adres
        legenda = s[s.index('class="legenda"'):]
        for tekst in ("plagiat", "kopia pomysłu", "patent", "nowość", "bez flagi", "do sprawdzenia", "flaga"):
            assert tekst in legenda[:900], (adres, tekst)
