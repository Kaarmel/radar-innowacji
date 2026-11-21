from radar import organizacje, werdykt
from radar.model import Dokument, WynikFiltra, Zgloszenie


def zgl(**kw):
    baza = dict(id=1, wejscie="formularz", tytul="T", opis="O", link=None, instytucja="Politechnika Rzeszowska",
                typ_instytucji="uczelnia", typ_innowacji="techniczna", etap="prototyp", wiek_przedzial="powyzej_30")
    baza.update(kw)
    return Zgloszenie(**baza)


def W(filtr, pasmo, procent=50.0, wlasna=False):
    return WynikFiltra(filtr, procent, pasmo, [], wlasna_praca=wlasna)


ZIELONE = [W("plagiat", "zielone", 0), W("kopia", "zielone", 20), W("patent", "zielone", 10), W("nowosc", "zielone", 80)]
PCI = organizacje.wczytaj("pci")


def nazwy(reks):
    return [r for rek in reks for r in rek.reguly]


def test_werdykt():
    assert werdykt.werdykt(ZIELONE) == "dalej"
    assert werdykt.werdykt(ZIELONE[:3] + [W("nowosc", "zolte")]) == "do_przegladu"
    assert werdykt.werdykt([W("plagiat", "czerwone")] + ZIELONE[1:]) == "odrzucone_do_przegladu"
    assert werdykt.werdykt([W("patent", "brak_danych", None)] + ZIELONE[:2]) == "dalej"


def test_komorki_pci():
    assert werdykt.komorka(zgl(wiek_przedzial="16_30", typ_instytucji="firma"), PCI) == "mlodzi_16_30"
    assert werdykt.komorka(zgl(typ_instytucji="szkola_ponadpodstawowa"), PCI) == "mlodzi_16_30"
    assert werdykt.komorka(zgl(typ_instytucji="uczelnia"), PCI) == "naukowcy"
    assert werdykt.komorka(zgl(typ_instytucji="jst"), PCI) == "inni"
    assert werdykt.komorka(zgl(typ_instytucji="firma"), PCI) == "ogolne"


def test_nieznany_profil_to_ogolny():
    assert organizacje.wczytaj("nie-ma-takiej")["slug"] == "ogolny"
    assert {p["slug"] for p in organizacje.lista()} >= {"pci", "ogolny"}


def test_r1_akceleracja():
    assert "R1" in nazwy(werdykt.sciezka(zgl(), ZIELONE, [], PCI))


def test_r2_ochrona_przy_wlasnej_pracy():
    w = ZIELONE[:2] + [W("patent", "zolte", 50, wlasna=True), W("nowosc", "zielone", 80)]
    assert "R2" in nazwy(werdykt.sciezka(zgl(), w, [], PCI))


def test_r3_transfer():
    assert "R3" in nazwy(werdykt.sciezka(zgl(typ_innowacji="organizacyjna", etap="wdrozone"), ZIELONE, [], PCI))


def test_r4_finansowanie_z_linkami():
    pod = [Dokument(id="mapadotacji:1", zrodlo="mapadotacji", typ="projekt", tytul="Projekt X", opis="", link="https://m/1")]
    reks = werdykt.sciezka(zgl(), ZIELONE, pod, PCI)
    r4 = [r for r in reks if "R4" in r.reguly][0]
    assert "Projekt X" in r4.powod and "https://m/1" in r4.powod


def test_r5_wspolpraca():
    w = [ZIELONE[0], W("kopia", "zolte", 45)] + ZIELONE[2:]
    assert "R5" in nazwy(werdykt.sciezka(zgl(), w, [], PCI))


def test_odrzucone_tylko_przeglad():
    reks = werdykt.sciezka(zgl(), [W("plagiat", "czerwone")] + ZIELONE[1:], [], PCI)
    assert nazwy(reks) == ["ODRZUCENIE"]


def test_partnerzy_bez_wlasnej():
    pod = [Dokument(id="a", zrodlo="radon", typ="projekt", tytul="A", opis="", link="https://a", instytucje=["POLITECHNIKA RZESZOWSKA"]),
           Dokument(id="b", zrodlo="radon", typ="projekt", tytul="B", opis="", link="https://b", instytucje=["Uniwersytet Rzeszowski"]),
           Dokument(id="c", zrodlo="epo", typ="patent", tytul="C", opis="", link="https://c", instytucje=["Uniwersytet Rzeszowski"])]
    p = werdykt.partnerzy(zgl(), pod)
    assert [x["nazwa"] for x in p] == ["Uniwersytet Rzeszowski"]
    assert p[0]["link"] == "https://b"


def test_do_przegladu_zaczyna_od_przegladu():
    reks = werdykt.sciezka(zgl(), ZIELONE[:3] + [W("nowosc", "zolte", 40)], [], PCI)
    assert reks[0].reguly == ["PRZEGLAD"] and "nowość" in reks[0].powod.lower()


def test_partnerzy_najpierw_lokalni():
    pod = [Dokument(id="e", zrodlo="epo", typ="patent", tytul="E", opis="", link="https://e", instytucje=["Haier Group"]),
           Dokument(id="m", zrodlo="mapadotacji", typ="projekt", tytul="M", opis="", link="https://m", instytucje=["Firma z Rzeszowa"])]
    assert [p["nazwa"] for p in werdykt.partnerzy(zgl(), pod)] == ["Firma z Rzeszowa", "Haier Group"]
