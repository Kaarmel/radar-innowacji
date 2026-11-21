"""Karta innowacji wg FAQ §5: obszar, poziom wdrożenia, TRL, wiarygodność, fakty a szacunki (reguły w kodzie)."""
from radar import klasyfikacja as K

from .test_app import POLA, klient  # noqa: F401


def _k(**kw):
    k = dict(wejscie="formularz", zrodlo_dok=None, typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna",
             etap="prototyp", link=None, cytat=None, wyniki=[], pokrycie={}, potencjal=None)
    return k | kw


def test_obszar_z_typu_innowacji_i_instytucji():
    assert K.profil(_k())["obszar"]["wartosc"] == "technologiczny"
    assert K.profil(_k(typ_innowacji="edukacyjna"))["obszar"]["wartosc"] == "edukacyjny"
    assert K.profil(_k(typ_innowacji="organizacyjna", typ_instytucji="jst"))["obszar"]["wartosc"] == "administracyjny"
    assert K.profil(_k())["obszar"]["pochodzenie"] == "regula"


def test_poziom_wdrozenia_i_trl_z_etapu():
    p = K.profil(_k(etap="pomysl"))
    assert p["wdrozenie"]["kroki"][0]["zaznaczony"] and not p["wdrozenie"]["kroki"][4]["zaznaczony"]
    assert [x["nazwa"] for x in p["wdrozenie"]["kroki"]] == ["koncepcja", "prototyp", "testy", "wdrożenie pilotażowe",
                                                              "rozwiązanie stosowane w praktyce"]
    assert p["trl"]["wartosc"] == "1–3" and p["trl"]["pochodzenie"] == "regula"
    assert K.profil(_k(etap="wdrozone"))["trl"]["wartosc"] == "7–9"
    assert K.profil(_k(etap="wdrozone"))["wdrozenie"]["kroki"][4]["zaznaczony"]
    assert K.profil(_k(typ_innowacji="edukacyjna"))["trl"]["wartosc"] is None  # TRL „jeśli ma zastosowanie”


def test_pochodzenie_fakt_deklaracja_szacunek():
    assert K.profil(_k())["wdrozenie"]["pochodzenie"] == "deklaracja"
    assert K.profil(_k(wejscie="radar"))["wdrozenie"]["pochodzenie"] == "szacunek_ai"
    assert K.profil(_k(wejscie="baza", zrodlo_dok="mapadotacji:1", etap="zakonczone"))["wdrozenie"]["pochodzenie"] == "fakt"


def test_wiarygodnosc_liczy_kod():
    dowod = [{"filtr": "kopia", "dowody": [{"dokument_id": "radon:1"}]}]
    mocna = K.profil(_k(wejscie="baza", zrodlo_dok="mapadotacji:1", link="https://mapadotacji.gov.pl/p/1",
                        cytat="Prototyp przetestowano w laboratorium", wyniki=dowod, pokrycie={"niedostepne": []}))
    slaba = K.profil(_k(pokrycie={"niedostepne": ["epo"]}))
    assert mocna["wiarygodnosc"]["poziom"] == "wysoka" and slaba["wiarygodnosc"]["poziom"] == "niska"
    assert len(mocna["wiarygodnosc"]["kryteria"]) == 5 and all("spelnione" in x for x in mocna["wiarygodnosc"]["kryteria"])


def test_karta_pokazuje_karte_innowacji(klient):
    r = klient.post("/zglos", data=POLA)
    for tekst in ("Karta innowacji", "Obszar zastosowania", "TRL", "Wiarygodność", "Oslo Manual", "deklaracja"):
        assert tekst in r.text, tekst
    zid = int(str(r.url).rsplit("/", 1)[1])
    assert klient.get(f"/api/karta/{zid}").json()["klasyfikacja"]["obszar"]["wartosc"] == "technologiczny"
