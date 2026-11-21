"""Limit czasu sprawdzenia: wolne źródło albo zawieszony dostawca AI nie blokują karty."""
import time

from radar import ai, sprawdz, termin


def test_wolne_zrodlo_na_zadanie_nie_blokuje(monkeypatch):
    def wolne(t):
        time.sleep(3)
        return []
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {"epo": wolne, "crossref": lambda t: []})
    termin.ustaw(61.0)  # na źródła zostaje ok. 1 s
    try:
        t0 = time.time()
        docs, ok, nie = sprawdz._na_zadanie(["water filter"])
        assert time.time() - t0 < 2.5
        assert "epo" in nie and "crossref" in ok
        assert any("epo" in p for p in termin.przekroczenia())
    finally:
        termin.ustaw(None)


def test_czat_json_po_terminie_nie_pyta(monkeypatch):
    def nie_wolno(*a, **kw):
        raise AssertionError("zapytanie po terminie")
    monkeypatch.setattr(ai, "_czat_json", nie_wolno)
    termin.ustaw(0)
    try:
        assert ai.czat_json("s", "u") == ({}, 0.0)
        assert termin.przekroczenia()
    finally:
        termin.ustaw(None)
    assert termin.zostalo() == float("inf") and termin.przekroczenia() == []


def test_wolny_beneficjent_nie_blokuje(monkeypatch):
    """Mapa Dotacji potrafi nie odpowiadać minutami (21.11 wieczorem: 189 s na jedną stronę)."""
    from radar.model import Dokument, Zgloszenie
    from radar.zrodla import mapadotacji
    opis = "Filtr wody inspirowany skrzelami ryb zatrzymuje mikroplastik bez wymiennych wkładów."
    def wolny(link):
        time.sleep(3)
        return "Fundacja"
    monkeypatch.setattr(mapadotacji, "beneficjent", wolny)
    d = Dokument(id="mapadotacji:9", zrodlo="mapadotacji", typ="projekt", tytul="Filtr", opis=opis, link="https://m/9")
    z = Zgloszenie(id=None, wejscie="formularz", tytul="Filtr", opis=opis, link=None, instytucja="ZST",
                   typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna", etap="prototyp",
                   wiek_przedzial="16_30", organizacja="pci")
    termin.ustaw(76.0)  # na beneficjentów zostaje ok. 1 s
    try:
        t0 = time.time()
        sprawdz._uzupelnij_beneficjentow(None, z, [(0.9, d)])
        assert time.time() - t0 < 2.5
        assert d.instytucje == []
        assert any("beneficjenci" in p for p in termin.przekroczenia())
    finally:
        termin.ustaw(None)
