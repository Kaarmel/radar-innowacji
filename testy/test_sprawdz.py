import pytest

from radar import ai, db, sprawdz
from radar.model import Dokument, Zgloszenie
from radar.zrodla import BrakDostepu, mapadotacji

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
