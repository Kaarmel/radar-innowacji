import os

import pytest

from radar import ai
from radar.model import Dokument

D1 = Dokument(id="mapadotacji:1", zrodlo="mapadotacji", typ="projekt", tytul="Filtr", opis="Filtr wody", link="https://a")
D2 = Dokument(id="epo:EP1A1", zrodlo="epo", typ="patent", tytul="Filter", opis="Water filter", link="https://b", jezyk="en")


def _podstaw(monkeypatch, odpowiedz):
    monkeypatch.setattr(ai, "czat_json", lambda system, user: (odpowiedz, 0.001))


def test_rubryka_id_spoza_listy_to_nie_wiadomo(monkeypatch):
    _podstaw(monkeypatch, {"odpowiedzi": [
        {"pytanie": "Q1", "odpowiedz": "tak", "dokument_id": "zmyslony:9", "uzasadnienie": "x"},
        {"pytanie": "Q2", "odpowiedz": "tak", "dokument_id": "mapadotacji:1", "uzasadnienie": "y"},
        {"pytanie": "Q3", "odpowiedz": "nie", "dokument_id": None, "uzasadnienie": "z"},
    ]})
    wynik, koszt = ai.rubryka_nowosci("opis", [D1, D2])
    assert [w["pytanie"] for w in wynik] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert wynik[0]["odpowiedz"] == "nie_wiadomo"
    assert wynik[1]["odpowiedz"] == "tak"
    assert wynik[3]["odpowiedz"] == "nie_wiadomo"  # brak odpowiedzi modelu
    assert koszt == 0.001


def test_zla_odpowiedz_bez_wyjatku(monkeypatch):
    _podstaw(monkeypatch, {})
    wynik, _ = ai.ten_sam_pomysl("opis", [D1])
    assert wynik == {}
    wynik, _ = ai.tlumacz_zapytanie("opis")
    assert wynik == {"opis_en": "", "terminy_en": [], "ipc": []}


def test_ten_sam_pomysl_odrzuca_obce_id(monkeypatch):
    _podstaw(monkeypatch, {"oceny": [{"dokument_id": "mapadotacji:1", "ocena": "ten_sam", "uzasadnienie": "a"},
                                     {"dokument_id": "inny:2", "ocena": "ten_sam", "uzasadnienie": "b"}]})
    wynik, _ = ai.ten_sam_pomysl("opis", [D1])
    assert list(wynik) == ["mapadotacji:1"] and wynik["mapadotacji:1"]["ocena"] == "ten_sam"


def test_zmyslony_cytat_usuniety(monkeypatch):
    _podstaw(monkeypatch, {"co": "Filtr", "instytucja": "ZST", "typ_innowacji": "techniczna", "etap": "prototyp",
                           "cytat": "tego zdania nie ma w tekście"})
    wynik, _ = ai.karta_z_tekstu("Tytuł", "Uczniowie zbudowali filtr wody.")
    assert wynik["cytat"] is None and wynik["typ_innowacji"] == "techniczna"


def test_prawdziwy_cytat_zostaje(monkeypatch):
    _podstaw(monkeypatch, {"czy": "tak", "cytat": "zbudowali  filtr"})
    wynik, _ = ai.czy_innowacja("Tytuł", "Uczniowie zbudowali filtr wody.")
    assert wynik == {"czy": "tak", "cytat": "zbudowali  filtr"}


@pytest.mark.zywe
@pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"), reason="brak klucza")
def test_tlumaczenie_na_zywo():
    wynik, koszt = ai.tlumacz_zapytanie("Filtr mikroplastiku inspirowany skrzelami ryb, bez wymiennych wkładów")
    assert wynik["terminy_en"] and wynik["opis_en"]
    assert koszt >= 0


def test_rozumowanie_wylaczone(monkeypatch):
    """DeepSeek v4.1 domyślnie rozumuje i zużywał cały limit tokenów (finish=length, pusta treść)."""
    import httpx
    wyslane = {}

    class Odp:
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {"cost": 0}}

    def post(url, json=None, **kw):
        wyslane.update(json)
        return Odp()
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setattr(httpx, "post", post)
    ai._czat_json("s", "u")
    assert wyslane["reasoning"] == {"enabled": False}


def test_odpowiedzi_zlego_typu_nie_wywracaja(monkeypatch):
    """Model potrafi oddać listę albo obiekt tam, gdzie oczekujemy tekstu (przegląd końcowy, pkt 2)."""
    from radar.model import Dokument
    d = Dokument(id="radon:1", zrodlo="radon", typ="projekt", tytul="T", opis="o", link="https://r/1")
    odpowiedzi = {
        "rubryka": {"odpowiedzi": [{"pytanie": ["Q1"], "odpowiedz": ["tak"], "dokument_id": ["radon:1", "x"]},
                                   {"pytanie": "Q2", "odpowiedz": "tak", "dokument_id": {"id": "radon:1"}}]},
        "kopia": {"oceny": [{"dokument_id": ["radon:1"], "ocena": "ten_sam"}, {"dokument_id": "radon:1", "ocena": ["ten_sam"]}]},
        "czy": {"czy": ["tak"], "cytat": ["a"]},
        "karta": {"co": ["x"], "typ_innowacji": ["techniczna"], "etap": {"a": 1}, "cytat": 5, "opis": ["y"]},
    }
    for klucz, odp in odpowiedzi.items():
        monkeypatch.setattr(ai, "czat_json", lambda s, u, odp=odp: (odp, 0.0))
        if klucz == "rubryka":
            w, _ = ai.rubryka_nowosci("opis", [d])
            assert all(x["odpowiedz"] == "nie_wiadomo" or x["pytanie"] == "Q2" for x in w)
            assert next(x for x in w if x["pytanie"] == "Q2")["dokument_id"] is None
        elif klucz == "kopia":
            assert ai.ten_sam_pomysl("opis", [d])[0] == {}
        elif klucz == "czy":
            assert ai.czy_innowacja("t", "tekst")[0] == {"czy": "niepewne", "cytat": None}
        else:
            k, _ = ai.karta_z_tekstu("t", "tekst")
            assert k["typ_innowacji"] == "" and k["etap"] == "" and k["cytat"] is None and isinstance(k["co"], str)


def test_rubryka_bez_podwojnego_przeczenia_i_z_definicja_tego_samego(monkeypatch):
    """Q5 „czy to NIE jest rutyna” model mylił („nie, to nie rutyna” = punkt mniej dla B+R)."""
    pytania = dict(ai.RUBRYKA)
    assert "nie jest" not in pytania["Q5"] and "rutyn" in pytania["Q5"]
    wyslane = {}
    monkeypatch.setattr(ai, "czat_json", lambda s, u: (wyslane.update(u=u), ({}, 0.0))[1])
    ai.rubryka_nowosci("opis", [])
    assert "TO SAMO rozwiązanie" in wyslane["u"] and "podobny temat" in wyslane["u"]


def test_rubryka_mowi_kiedy_tak_a_kiedy_nie_wiadomo(monkeypatch):
    """Model odpowiadał „nie_wiadomo”, gdy dokumenty opisywały coś innego (a to znaczy „tak”): nowość nieoceniona."""
    wyslane = {}
    monkeypatch.setattr(ai, "czat_json", lambda s, u: (wyslane.update(u=u), ({}, 0.0))[1])
    ai.rubryka_nowosci("opis", [])
    assert "żaden znaleziony dokument nie opisuje tego samego rozwiązania" in wyslane["u"]
    assert "zbyt ogólne" in wyslane["u"]
