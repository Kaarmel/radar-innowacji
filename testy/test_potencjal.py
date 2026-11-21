from radar import organizacje, potencjal
from radar.model import Dokument, WynikFiltra, Zgloszenie

PCI = organizacje.wczytaj("pci")
OGOLNY = organizacje.wczytaj("ogolny")


def zgl(opis="Aplikacja do zapisów na zajęcia dla rodziców.", etap="prototyp", inst="Szkoła A"):
    return Zgloszenie(id=1, wejscie="formularz", tytul="T", opis=opis, link=None, instytucja=inst, typ_instytucji="szkola_podstawowa",
                      typ_innowacji="techniczna", etap=etap, wiek_przedzial="16_30", opis_en="Enrollment app for parents")


def rubryka(*odp):
    return [{"pytanie": f"Q{i}", "odpowiedz": o, "dokument_id": None, "uzasadnienie": "u"} for i, o in enumerate(odp, 1)]


def wyniki(nowosc=("tak", "tak", "nie", "tak", "tak"), patent="zielone", pasmo_nowosci="zielone"):
    return [WynikFiltra("plagiat", 0.0, "zielone", []), WynikFiltra("kopia", 20.0, "zielone", []),
            WynikFiltra("patent", 10.0, patent, []),
            WynikFiltra("nowosc", 80.0, pasmo_nowosci, rubryka(*nowosc) if nowosc else [])]


def dok(i, inst, zrodlo="radon"):
    return Dokument(id=f"{zrodlo}:{i}", zrodlo=zrodlo, typ="projekt", tytul=f"D{i}", opis="", link=f"https://d/{i}", instytucje=[inst])


def kryt(ocena, nazwa):
    return next(k for k in ocena["kryteria"] if k["id"] == nazwa)


def test_formula_jawna_i_zrodla():
    o = potencjal.ocen(zgl(), wyniki(), [], PCI)
    assert {k["zrodlo"] for k in o["kryteria"]} <= {"kod", "AI", "formularz"}
    assert all(k["max"] == PCI["potencjal"]["wagi"][k["id"]] for k in o["kryteria"])
    dostepne = [k for k in o["kryteria"] if k["punkty"] is not None]
    assert o["wynik"] == round(100 * sum(k["punkty"] for k in dostepne) / sum(k["max"] for k in dostepne))
    assert kryt(o, "nowosc")["punkty"] == PCI["potencjal"]["wagi"]["nowosc"] * 3 / 4   # Q1,Q2,Q5 tak; Q3 nie (Q4 osobno)
    assert kryt(o, "przewaga")["punkty"] == PCI["potencjal"]["wagi"]["przewaga"]


def test_brak_danych_nie_zaniza():
    o = potencjal.ocen(zgl(), wyniki(patent="brak_danych"), [], PCI)
    assert kryt(o, "ochrona")["punkty"] is None and o["wynik"] is not None
    assert "brak danych" in o["uwaga"].lower() and o["suma_max"] == 100 - PCI["potencjal"]["wagi"]["ochrona"]


def test_dojrzalosc_z_etapu():
    assert kryt(potencjal.ocen(zgl(etap="wdrozone"), wyniki(), [], PCI), "dojrzalosc")["punkty_bez_bramki"] == PCI["potencjal"]["wagi"]["dojrzalosc"]
    assert kryt(potencjal.ocen(zgl(etap="pomysl"), wyniki(), [], PCI), "dojrzalosc")["punkty_bez_bramki"] < PCI["potencjal"]["wagi"]["dojrzalosc"] / 2


def test_specjalizacje_pci_i_brak_w_ogolnym():
    o = potencjal.ocen(zgl(opis="Dron do inspekcji linii energetycznych z kamerą termowizyjną."), wyniki(), [], PCI)
    s = kryt(o, "specjalizacje")
    assert s["punkty_bez_bramki"] == s["max"] and "Lotnictwo" in s["uzasadnienie"]
    assert all(k["id"] != "specjalizacje" for k in potencjal.ocen(zgl(), wyniki(), [], OGOLNY)["kryteria"])


def test_zapotrzebowanie_inne_instytucje_bez_kopii_i_wlasnych():
    ranking = [(0.3, dok(1, "Gmina X")), (0.3, dok(2, "Gmina Y")), (0.25, dok(3, "Gmina X")), (0.7, dok(4, "Kopista")),
               (0.3, dok(5, "Szkoła A")), (0.05, dok(6, "Daleko"))]
    k = kryt(potencjal.ocen(zgl(), wyniki(), ranking, PCI), "zapotrzebowanie")
    assert [d["instytucja"] for d in k["dowody"]] == ["Gmina X", "Gmina Y"]


def test_finansowanie_z_linkiem():
    ranking = [(0.3, dok(1, "Firma", zrodlo="mapadotacji"))]
    k = kryt(potencjal.ocen(zgl(), wyniki(), ranking, PCI), "finansowanie")
    assert k["punkty"] > 0 and k["dowody"][0]["link"] == "https://d/1"


def test_finansowanie_pomija_kopie():
    ranking = [(0.65, dok(1, "Kopiowany", zrodlo="mapadotacji")), (0.3, dok(2, "Firma", zrodlo="mapadotacji"))]
    k = kryt(potencjal.ocen(zgl(), wyniki(), ranking, PCI), "finansowanie")
    assert [d["link"] for d in k["dowody"]] == ["https://d/2"]


def test_liczebnik_jednej_instytucji():
    k = kryt(potencjal.ocen(zgl(), wyniki(), [(0.3, dok(1, "Gmina X"))], PCI), "zapotrzebowanie")
    assert k["uzasadnienie"].startswith("1 inna instytucja ma")


def bogaty_ranking():
    return [(0.3, dok(i, f"Gmina {i}", zrodlo="mapadotacji")) for i in range(6)]


def test_bramka_nowosci_rutyna_nie_ma_potencjalu():
    rutyna = potencjal.ocen(zgl(etap="zakonczone"), wyniki(nowosc=("nie",) * 5), bogaty_ranking(), PCI)
    innowacja = potencjal.ocen(zgl(etap="zakonczone"), wyniki(nowosc=("tak",) * 5), bogaty_ranking(), PCI)
    assert rutyna["bramka"] == 0.0 and rutyna["wynik"] == 0
    assert kryt(rutyna, "zapotrzebowanie")["punkty"] == 0 and kryt(rutyna, "zapotrzebowanie")["punkty_bez_bramki"] == 15
    assert innowacja["bramka"] == 1.0 and innowacja["wynik"] >= 90


def test_bez_oceny_nowosci_brak_wyniku():
    o = potencjal.ocen(zgl(), wyniki(nowosc=None, pasmo_nowosci="brak_danych"), bogaty_ranking(), PCI)
    assert o["wynik"] is None and "nowości" in o["uwaga"]


def test_przelicz_stara_ocene_bez_bramki():
    stara = {"wynik": 74, "kryteria": [
        {"id": "nowosc", "max": 25, "punkty": 12.5}, {"id": "przewaga", "max": 10, "punkty": 0.0},
        {"id": "zapotrzebowanie", "max": 15, "punkty": 15.0}, {"id": "ochrona", "max": 10, "punkty": 10.0}]}
    nowa = potencjal.przelicz(stara)
    assert nowa["bramka"] == 0.5 and nowa["wynik"] == round(100 * (12.5 + 0 + 7.5 + 5) / 60)
    assert potencjal.przelicz(nowa)["wynik"] == nowa["wynik"]  # ponowne przeliczenie niczego nie zmienia


def test_przelicz_zapisane_oceny(tmp_path):
    from radar import db
    con = db.polacz(tmp_path / "t.sqlite")
    db.zapisz_ocene(con, 7, {"wynik": 74, "kryteria": [{"id": "nowosc", "max": 25, "punkty": 0.0},
                                                       {"id": "ochrona", "max": 10, "punkty": 10.0}]})
    assert potencjal.przelicz_zapisane(con) == 1
    assert con.execute("SELECT wynik FROM ocena WHERE zgl_id=7").fetchone()[0] == 0
