import pytest

from radar import ai, db, sprawdz
from radar.model import Dokument, Zgloszenie
from radar.zrodla import BrakDostepu, mapadotacji

PRAWDZIWE = {n: getattr(ai, n) for n in ("tlumacz_zapytanie", "ten_sam_pomysl", "rubryka_nowosci")}

ORYG = ("Uczniowie technikum zbudowali filtr wody inspirowany skrzelami ryb. Urządzenie zatrzymuje drobiny mikroplastiku "
        "bez użycia wymiennych wkładów. Prototyp przetestowano w szkolnym laboratorium na próbkach z pobliskiej rzeki.")


@pytest.fixture
def con(tmp_path, monkeypatch):
    c = db.polacz(tmp_path / "t.sqlite")
    db.zapisz_dokumenty(c, [
        Dokument(id="mapadotacji:1", zrodlo="mapadotacji", typ="projekt", tytul="Filtr wody ze skrzelami", opis=ORYG,
                 link="https://mapadotacji.gov.pl/projekty/1/", instytucje=["Fundacja Czysta Woda"]),
        Dokument(id="radon:2", zrodlo="radon", typ="projekt", tytul="Rewitalizacja", opis="Remont rynku i fontanny.",
                 link="https://r/2", instytucje=["Gmina Czarna"]),
    ])
    monkeypatch.setattr(ai, "tlumacz_zapytanie", lambda o: ({"opis_en": "fish gill water filter", "terminy_en": ["water filter"], "ipc": []}, 0.001))
    monkeypatch.setattr(ai, "ten_sam_pomysl", lambda o, d: ({x.id: {"ocena": "ten_sam", "uzasadnienie": "ten sam"} for x in d}, 0.001))
    monkeypatch.setattr(ai, "rubryka_nowosci", lambda o, d: ([{"pytanie": f"Q{i}", "odpowiedz": "nie", "dokument_id": None,
                                                               "uzasadnienie": ""} for i in range(1, 6)], 0.001))
    monkeypatch.setattr(ai, "ten_sam_problem", lambda o, d: ({}, 0.0))
    monkeypatch.setattr(mapadotacji, "beneficjent", lambda link: None)
    return c


def _zgl(c, opis=ORYG, inst="ZST Jasło"):
    return db.zapisz_zgloszenie(c, Zgloszenie(id=None, wejscie="formularz", tytul="Filtr mikroplastiku", opis=opis, link=None,
                                             instytucja=inst, typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna",
                                             etap="prototyp", wiek_przedzial="16_30", organizacja="pci"))


def test_przeplyw_odrzucenia(con, monkeypatch):
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    k = sprawdz.sprawdz(con, _zgl(con))
    assert k["werdykt"] == "odrzucone_do_przegladu"
    plagiat = next(w for w in k["wyniki"] if w["filtr"] == "plagiat")
    assert plagiat["pasmo"] == "czerwone" and plagiat["dowody"][0]["link"] == "https://mapadotacji.gov.pl/projekty/1/"
    assert k["komorka"] == "mlodzi_16_30" and k["status"] == "gotowe"
    assert k["pokrycie"]["ai"] == []  # AI podmienione w teście: żaden model nie odpowiadał
    assert k["koszt_usd"] > 0 and k["czas_s"] >= 0


def test_przeplyw_bez_epo(con, monkeypatch):
    def nie(*a, **kw):
        raise BrakDostepu("EPO: test")
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {"epo": nie})
    k = sprawdz.sprawdz(con, _zgl(con, opis="Aplikacja do zapisów na zajęcia pozalekcyjne z kalendarzem i powiadomieniami dla rodziców uczniów."))
    patent = next(w for w in k["wyniki"] if w["filtr"] == "patent")
    assert patent["pasmo"] == "brak_danych"
    assert "epo" in k["pokrycie"]["niedostepne"]
    assert k["werdykt"] in {"dalej", "do_przegladu", "odrzucone_do_przegladu"}


def test_drugie_zgloszenie_to_duplikat(con, monkeypatch):
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    opis = "Nasza gmina uruchomiła cyfrowy rejestr zgłoszeń awarii oświetlenia ulicznego z mapą i automatycznym przydziałem ekip serwisowych."
    sprawdz.sprawdz(con, _zgl(con, opis=opis, inst="Gmina Biała"))
    k = sprawdz.sprawdz(con, _zgl(con, opis=opis, inst="Gmina Biała"))
    plagiat = next(w for w in k["wyniki"] if w["filtr"] == "plagiat")
    assert plagiat["pasmo"] == "czerwone" and plagiat["uwaga"] == "duplikat zgłoszenia"


def test_pokrycie_bez_powtorzen(con, monkeypatch):
    znalezione = [Dokument(id="epo:EP1B1", zrodlo="epo", typ="patent", tytul="Water filter", opis="fish gill filter",
                           link="https://e/1", status="udzielony", jezyk="en")]
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {"epo": lambda t: znalezione})
    sprawdz.sprawdz(con, _zgl(con))
    k = sprawdz.sprawdz(con, _zgl(con, inst="Inna szkoła"))
    assert k["pokrycie"]["zrodla"].count("epo") == 1


def test_podobne_dolacza_finansowane_spoza_czolowki():
    epo = [(0.9 - i * 0.01, Dokument(id=f"epo:{i}", zrodlo="epo", typ="patent", tytul="E", opis="", link="https://e")) for i in range(25)]
    mapa = (0.2, Dokument(id="mapadotacji:9", zrodlo="mapadotacji", typ="projekt", tytul="M", opis="", link="https://m"))
    slaby = (0.05, Dokument(id="mapadotacji:8", zrodlo="mapadotacji", typ="projekt", tytul="S", opis="", link="https://s"))
    ids = [d.id for d in sprawdz._podobne(epo + [mapa, slaby])]
    assert "mapadotacji:9" in ids and "mapadotacji:8" not in ids and len(ids) == 21


def test_dokument_zrodlowy_wykluczony_i_ocena_potencjalu(con, monkeypatch):
    """Ocena projektu znalezionego w bazie: nie może porównać się sam ze sobą (100% plagiatu)."""
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="baza", tytul="Filtr wody ze skrzelami", opis=ORYG, link=None,
                                               instytucja="Fundacja Czysta Woda", typ_instytucji="ngo", typ_innowacji="techniczna",
                                               etap="prototyp", wiek_przedzial="mieszany", organizacja="pci", zrodlo_dok="mapadotacji:1"))
    k = sprawdz.sprawdz(con, zid)
    plagiat = next(w for w in k["wyniki"] if w["filtr"] == "plagiat")
    assert plagiat["pasmo"] == "zielone"
    assert all(d["dokument_id"] != "mapadotacji:1" for w in k["wyniki"] for d in w["dowody"] if "dokument_id" in d)
    assert 0 <= k["potencjal"]["wynik"] <= 100 and k["potencjal"]["kryteria"]


def test_beneficjenci_tylko_gdy_moga_zmienic_wynik(monkeypatch):
    """Strona projektu Mapy Dotacji ładuje się kilka sekund: pobieramy beneficjenta tylko dla trafień plagiatu i kandydatów na kopię."""
    pytane = []
    monkeypatch.setattr(mapadotacji, "beneficjent", lambda link: pytane.append(link) or None)
    z = Zgloszenie(id=1, wejscie="formularz", tytul="T", opis=ORYG, link=None, instytucja="X", typ_instytucji="firma",
                   typ_innowacji="techniczna", etap="pomysl", wiek_przedzial="powyzej_30")
    md = lambda i, opis: Dokument(id=f"mapadotacji:{i}", zrodlo="mapadotacji", typ="projekt", tytul="P", opis=opis, link=f"https://m/{i}")
    ranking = [(0.5, md(1, "Inny tekst o filtrach wody.")), (0.2, md(2, "Daleki temat budowy drogi.")), (0.1, md(3, ORYG))]
    sprawdz._uzupelnij_beneficjentow(None, z, ranking)
    assert pytane == ["https://m/3", "https://m/1"]


def test_karta_podaje_stan_danych(con, monkeypatch):
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    k = sprawdz.sprawdz(con, _zgl(con))
    stan = k["pokrycie"]["stan_danych"]
    assert set(stan) >= {"mapadotacji", "radon"} and all(len(v) == 10 for v in stan.values())  # RRRR-MM-DD
    assert k["pokrycie"]["na_zywo"][:4] == "2026" or len(k["pokrycie"]["na_zywo"]) == 16


def test_podwojny_klik_tylko_drugie_to_duplikat(con, monkeypatch):
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    opis = "Nasza gmina uruchomiła cyfrowy rejestr zgłoszeń awarii oświetlenia ulicznego z mapą i automatycznym przydziałem ekip serwisowych."
    pierwsze, drugie = _zgl(con, opis=opis, inst="Gmina Biała"), _zgl(con, opis=opis, inst="Gmina Biała")
    k1 = sprawdz.sprawdz(con, pierwsze)
    k2 = sprawdz.sprawdz(con, drugie)
    uwaga = lambda k: next(w for w in k["wyniki"] if w["filtr"] == "plagiat")["uwaga"]
    assert uwaga(k1) != "duplikat zgłoszenia" and uwaga(k2) == "duplikat zgłoszenia"


def test_zawieszone_ai_nie_blokuje_karty(con, monkeypatch):
    from radar import config
    for n, f in PRAWDZIWE.items():
        monkeypatch.setattr(ai, n, f)
    monkeypatch.setattr(ai, "_czat_json", lambda s, u, **kw: (__import__("time").sleep(0.5), ({}, 0.0))[1])
    monkeypatch.setattr(sprawdz, "ZRODLA_NA_ZADANIE", {})
    monkeypatch.setattr(config, "LIMIT_SPRAWDZENIA_S", 1.0)
    import time
    t0 = time.time()
    k = sprawdz.sprawdz(con, _zgl(con))
    assert time.time() - t0 < 3 and k["status"] == "gotowe"
    assert k["pokrycie"]["limit_czasu"]
    assert next(w for w in k["wyniki"] if w["filtr"] == "nowosc")["pasmo"] == "brak_danych"
