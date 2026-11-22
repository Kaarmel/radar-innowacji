"""Zakładki dla grup odbiorców: prosty język, konkretne demo, technika schowana."""
from radar import db, slowniki
from radar.model import Zgloszenie

from .test_app import klient  # noqa: F401


def test_kazda_rola_ma_strone_z_demo(klient):
    assert set(slowniki.ROLE) >= {"analityk", "mlodzi", "naukowcy", "gmina", "firma"}
    for slug, r in slowniki.ROLE.items():
        s = klient.get(f"/dla/{slug}")
        assert s.status_code == 200, slug
        assert r["nazwa"] in s.text and r["korzysc"] in s.text
        assert all(href in s.text for _, href in r["demo"]), slug
        assert len(r["kroki"]) == 3
        # zakładki do pozostałych ról na każdej stronie
        assert all(f'href="/dla/{inna}"' in s.text for inna in slowniki.ROLE)


def test_nieznana_rola_404(klient):
    assert klient.get("/dla/kosmita").status_code == 404


def test_start_prowadzi_od_odkrywania(klient):
    con = db.polacz()
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="radar", tytul="Aplikacja RescuePet", opis="Aplikacja do zgłaszania zwierząt.",
                                               link="https://szkola.pl/r", instytucja="ZST", typ_instytucji="szkola_ponadpodstawowa",
                                               typ_innowacji="techniczna", etap="prototyp", wiek_przedzial="16_30", organizacja="pci"))
    with con:
        con.execute("UPDATE zgloszenie SET werdykt='dalej' WHERE id=?", (zid,))
    s = klient.get("/").text
    s = s[s.index("<main"):]  # treść strony, bez menu
    assert "Bez flag, dalej" in s
    assert "Ostatnio wykryte przez radar" in s and f"/karta/{zid}" in s and "Aplikacja RescuePet" in s
    assert s.index("Przejrzyj wykryte innowacje") < s.index("Oceń projekt")
    assert "Zgłoś innowację" not in s and 'href="/dla/analityk"' in s


def test_start_pokazuje_tylko_wykrycia_po_bramce(klient):
    """Rutyna wykryta przez radar (np. przebudowa drogi) zostaje w kolejce do przeglądu, ale nie na stronie głównej."""
    con = db.polacz()
    ids = {}
    for tytul, werdykt in (("Aplikacja RescuePet", "dalej"), ("Przebudowa nawierzchni drogi", "odrzucone_do_przegladu")):
        ids[tytul] = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="radar", tytul=tytul, opis="Opis.", link=f"https://x.pl/{len(ids)}",
                                                          instytucja="ZST", typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna",
                                                          etap="prototyp", wiek_przedzial="16_30", organizacja="pci"))
        with con:
            con.execute("UPDATE zgloszenie SET werdykt=?, status='gotowe' WHERE id=?", (werdykt, ids[tytul]))
    s = klient.get("/").text
    s = s[s.index("<main"):]
    assert "Aplikacja RescuePet" in s and "Przebudowa nawierzchni drogi" not in s
    assert "1 odrzuciła bramka" in s


def test_radar_odrzuca_inwestycje_i_remonty(monkeypatch):
    from radar import ai
    wyslane = {}
    monkeypatch.setattr(ai, "czat_json", lambda s, u: (wyslane.update(u=u), ({}, 0.0))[1])
    ai.czy_innowacja("t", "x")
    for slowo in ("przebudowa", "remont", "wyposażenie pracowni", "inwestycja"):
        assert slowo in wyslane["u"], slowo


def test_radar_odrzuca_zajecia_kampanie_i_maskotki(monkeypatch):
    """Karta 10 (zajęcia straży miejskiej z maskotką) i 13 (szkolenie z pierwszej pomocy) przeszły bramkę AI: to rutyna, nie innowacja."""
    from radar import ai
    wyslane = {}
    monkeypatch.setattr(ai, "czat_json", lambda s, u: (wyslane.update(u=u), ({}, 0.0))[1])
    ai.czy_innowacja("t", "x")
    for slowo in ("szkolenie", "pokaz", "kampania", "pogadanka", "maskotka", "konkurs", "zakup lub montaż gotowych instalacji"):
        assert slowo in wyslane["u"], slowo


def test_formularz_to_ocena_projektu_przez_analityka(klient):
    s = klient.get("/zglos").text
    assert "Oceń projekt" in s and "Do kogo kierujesz" not in s and "Profil oceny" in s


def test_zatwierdzone_logo_w_naglowku_i_ikonie(klient):
    """LOGO.md: logo 08 „Wyłoniony moduł” z zatwierdzonych plików, bez zmian znaku i kolorów."""
    s = klient.get("/").text
    assert 'src="/static/logo.svg' in s and 'alt="Radar Innowacji"' in s
    assert 'rel="icon"' in s and "/static/logo.png" in s
    svg = klient.get("/static/logo.svg")
    assert svg.status_code == 200 and "#0085CC" in svg.text and "#6BB437" in svg.text
    assert klient.get("/static/logo.png").status_code == 200
