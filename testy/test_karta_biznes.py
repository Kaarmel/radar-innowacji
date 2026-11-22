"""Karta dla jury i analityka: specjalizacje regionu (RIS3), głębokość zwiadu na stronie głównej, decyzja człowieka na górze."""
from radar import db
from radar import klasyfikacja as K
from radar.model import Dokument, Zgloszenie

from .test_app import POLA, klient  # noqa: F401
from .test_klasyfikacja import _k


def _pot(uzasadnienie):
    return {"wynik": 40, "kryteria": [{"id": "specjalizacje", "nazwa": "Zgodność ze specjalizacjami organizacji", "max": 15,
                                        "punkty": 5.0, "punkty_bez_bramki": 15.0, "zrodlo": "kod", "uzasadnienie": uzasadnienie,
                                        "dowody": []}]}


def test_specjalizacje_regionu_z_oceny_potencjalu():
    assert K.profil(_k(potencjal=_pot("Pasuje do: Lotnictwo i kosmos (dron, lotnic); ICT (algorytm).")))["specjalizacje"] == {
        "wartosc": "Lotnictwo i kosmos, ICT", "pasuje": True, "pochodzenie": "regula"}
    s = K.profil(_k(potencjal=_pot("Nie pasuje do specjalizacji: Lotnictwo i kosmos, ICT.")))["specjalizacje"]
    assert s["pasuje"] is False and s["wartosc"] == "nie pasuje do: Lotnictwo i kosmos, ICT"
    assert K.profil(_k())["specjalizacje"]["wartosc"] is None


def test_start_pokazuje_glebokosc_zwiadu(klient):
    con = db.polacz()
    db.zapisz_dokumenty(con, [Dokument(id=f"mapadotacji:{i}", zrodlo="mapadotacji", typ="projekt", tytul="P", opis="O",
                                       link=f"https://m/{i}") for i in range(3)]
                        + [Dokument(id="uprp:1", zrodlo="uprp", typ="patent", tytul="P", opis="O", link="https://u/1"),
                           Dokument(id="radon_patenty:1", zrodlo="radon_patenty", typ="patent", tytul="P", opis="O", link="https://r/1")])
    s = klient.get("/").text
    assert s.index('class="zwiad"') < s.index("Ostatnio wykryte")
    for tekst in ("<b>3</b> projektów z dotacją", "<b>2</b> patentów i zgłoszeń patentowych", "<b>172</b> stron szkół, uczelni",
                  "EPO, OpenAlex i Crossref na żywo"):
        assert tekst in s, tekst


def test_decyzja_czlowieka_nad_wynikami_filtrow(klient):
    klient.post("/zglos", data=POLA)
    s = klient.get("/karta/1").text
    assert s.index('id="decyzja"') < s.index('class="filtry-paski"')
    assert "Ostateczną decyzję podejmuje człowiek" in s


def test_analityk_odrzuca_wykrycie_ktore_nie_jest_innowacja(klient):
    """Wydarzenie wykryte przez radar: analityk odrzuca je z powodem i znika ze strony głównej (zostaje w dzienniku)."""
    con = db.polacz()
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="radar", tytul="Szkolenie z pierwszej pomocy", opis="Opis.",
                                               link="https://x.pl/1", instytucja="CKZ", typ_instytucji="szkola_ponadpodstawowa",
                                               typ_innowacji="techniczna", etap="prototyp", wiek_przedzial="16_30", organizacja="pci"))
    with con:
        con.execute("UPDATE zgloszenie SET werdykt='dalej', status='gotowe' WHERE id=?", (zid,))
    s = klient.get("/").text
    assert "Szkolenie z pierwszej pomocy" in s[s.index("<main"):]
    assert klient.post(f"/karta/{zid}/decyzja", data={"decyzja": "odrzuc", "powod": "Wydarzenie, nie innowacja"}).status_code == 200
    s = klient.get("/").text
    assert "Szkolenie z pierwszej pomocy" not in s[s.index("<main"):]
