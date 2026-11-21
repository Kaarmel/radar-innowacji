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
