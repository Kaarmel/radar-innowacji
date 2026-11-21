from radar import ai, filtry, instytucje
from radar.model import Dokument, Zgloszenie

ORYG = ("Uczniowie technikum zbudowali filtr wody inspirowany skrzelami ryb. Urządzenie zatrzymuje drobiny mikroplastiku "
        "bez użycia wymiennych wkładów. Prototyp przetestowano w szkolnym laboratorium na próbkach z pobliskiej rzeki.")
INNY = ("Gmina wyremontowała płytę rynku i posadziła nowe drzewa. Mieszkańcy zyskali ławki, fontannę oraz oświetlenie "
        "energooszczędne. Prace prowadzono etapami przez cały rok budżetowy w porozumieniu z konserwatorem zabytków.")


def zgl(opis, inst="Zespół Szkół Technicznych w Jaśle"):
    return Zgloszenie(id=1, wejscie="formularz", tytul="Filtr", opis=opis, link=None, instytucja=inst,
                      typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna", etap="prototyp",
                      wiek_przedzial="16_30", opis_en="Water filter inspired by fish gills removing microplastics")


def dok(id, opis, inst, zrodlo="mapadotacji", typ="projekt", jezyk="pl"):
    return Dokument(id=id, zrodlo=zrodlo, typ=typ, tytul="T", opis=opis, link="https://x/" + id, instytucje=[inst], jezyk=jezyk)


DF = (lambda t: 1, 100)


def test_plagiat_obcy_czerwony_z_fragmentem():
    zd = ORYG.split(". ")
    w = filtry.plagiat(zgl(". ".join([zd[0], zd[1]]) + ". " + INNY.split(". ")[0]), [dok("a", ORYG, "Inna Fundacja Wodna")])
    assert w.pasmo == "czerwone" and w.dowody[0]["fragmenty"]


def test_plagiat_wlasna_praca_zielone():
    w = filtry.plagiat(zgl(ORYG), [dok("a", ORYG, "Zespół Szkół Technicznych w Jaśle")])
    assert w.wlasna_praca is True and w.pasmo == "zielone"


def test_duplikat_zgloszenia_czerwony():
    w = filtry.plagiat(zgl(ORYG), [dok("zgloszenie:7", ORYG, "Zespół Szkół Technicznych w Jaśle", zrodlo="zgloszenie", typ="zgloszenie")])
    assert w.pasmo == "czerwone" and w.uwaga == "duplikat zgłoszenia"


def test_kopia_czerwona_gdy_ai_potwierdza(monkeypatch):
    monkeypatch.setattr(ai, "ten_sam_pomysl", lambda o, d: ({x.id: {"ocena": "ten_sam", "uzasadnienie": "u"} for x in d}, 0.0))
    w = filtry.kopia(zgl(ORYG), [dok("a", ORYG + " Dodatkowe zdanie.", "Fundacja Inna")], *DF)
    assert w.pasmo == "czerwone" and w.procent > 60


def test_kopia_zolta_gdy_ai_mowi_inny(monkeypatch):
    monkeypatch.setattr(ai, "ten_sam_pomysl", lambda o, d: ({x.id: {"ocena": "inny", "uzasadnienie": "u"} for x in d}, 0.0))
    w = filtry.kopia(zgl(ORYG), [dok("a", ORYG, "Fundacja Inna")], *DF)
    assert w.pasmo == "zolte"


def test_kopia_po_angielsku_uzywa_tlumaczenia(monkeypatch):
    monkeypatch.setattr(ai, "ten_sam_pomysl", lambda o, d: ({}, 0.0))
    w = filtry.kopia(zgl(ORYG), [dok("a", "Water filter inspired by fish gills removing microplastics", "X", jezyk="en")], *DF)
    assert w.procent > 60


def test_patent_niedostepny_brak_danych():
    w = filtry.patent(zgl(ORYG), [], *DF, dostepne=False)
    assert w.pasmo == "brak_danych" and "18 miesiącach" in w.uwaga


def test_nowosc_pasma(monkeypatch):
    def rub(n):
        return lambda o, d: ([{"pytanie": f"Q{i}", "odpowiedz": "tak" if i <= n else "nie", "dokument_id": None,
                               "uzasadnienie": ""} for i in range(1, 6)], 0.0)
    for n, pasmo in [(1, "czerwone"), (2, "zolte"), (4, "zielone")]:
        monkeypatch.setattr(ai, "rubryka_nowosci", rub(n))
        assert filtry.nowosc(zgl(ORYG), []).pasmo == pasmo


def test_nowosc_same_nie_wiadomo_brak_danych(monkeypatch):
    monkeypatch.setattr(ai, "rubryka_nowosci", lambda o, d: ([{"pytanie": f"Q{i}", "odpowiedz": "nie_wiadomo",
                                                               "dokument_id": None, "uzasadnienie": ""} for i in range(1, 6)], 0.0))
    assert filtry.nowosc(zgl(ORYG), []).pasmo == "brak_danych"


def test_koszt_sumowany(monkeypatch):
    monkeypatch.setattr(ai, "rubryka_nowosci", lambda o, d: ([], 0.25))
    koszt = []
    filtry.nowosc(zgl(ORYG), [], koszt=koszt)
    assert koszt == [0.25]


def test_ta_sama_instytucja():
    assert instytucje.ta_sama("Politechnika Rzeszowska im. Ignacego Łukasiewicza", ["POLITECHNIKA RZESZOWSKA"])
    assert not instytucje.ta_sama("Szkoła Podstawowa nr 5 w Rzeszowie", ["Szkoła Podstawowa"])
    assert not instytucje.ta_sama("Gmina Czarna", ["Gmina Biała"])
    assert not instytucje.ta_sama("", ["Gmina Biała"])
