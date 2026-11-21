"""Warunki działania: aktualność danych, harmonogram źródeł, ścieżki AI i wymagania (prośba mentorów PCI 21.11)."""
import httpx
import pytest

from radar import ai, db, slowniki
from radar.model import Dokument

from .test_app import klient  # noqa: F401  (ta sama baza tymczasowa i udawane sprawdzenie)


def test_stan_zrodel(tmp_path):
    con = db.polacz(tmp_path / "t.sqlite")
    db.zapisz_dokumenty(con, [
        Dokument(id="radon:1", zrodlo="radon", typ="projekt", tytul="A", opis="a", link="https://r/1", rok=2023),
        Dokument(id="radon:2", zrodlo="radon", typ="projekt", tytul="B", opis="b", link="https://r/2", rok=2026),
    ])
    s = db.stan_zrodel(con)
    assert s["radon"]["dokumentow"] == 2 and s["radon"]["najnowszy_rok"] == 2026
    assert s["radon"]["pobrano_do"] >= s["radon"]["pobrano_od"] > 0


def test_harmonogram_dla_kazdego_zrodla():
    for z in slowniki.ZRODLA:
        if z != "zgloszenie":
            assert z in slowniki.HARMONOGRAM, z
            assert slowniki.HARMONOGRAM[z]["co_ile"]
    assert "18" in slowniki.HARMONOGRAM["epo"]["uwaga"]


def test_strona_warunki_i_api_zrodla(klient):
    r = klient.get("/warunki")
    assert r.status_code == 200
    for tekst in ("Harmonogram", "Stan danych", "OPENROUTER_API_KEY", "lokalnie", "Wymagania"):
        assert tekst in r.text, tekst
    j = klient.get("/api/zrodla").json()
    radon = next(x for x in j if x["zrodlo"] == "radon_patenty")
    assert {"nazwa", "dokumentow", "stan_na", "co_ile", "tryb"} <= set(radon)


def test_lokalny_model_bez_klucza(monkeypatch):
    wyslane = {}

    class Odp:
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": '{"a": 1}'}, "finish_reason": "stop"}]}

    def post(url, json=None, headers=None, **kw):
        wyslane.update(url=url, body=json, headers=headers)
        return Odp()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("AI_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("MODEL", "qwen3:8b")
    monkeypatch.setattr(httpx, "post", post)
    assert ai.czat_json("s", "u")[0] == {"a": 1}
    assert wyslane["url"].startswith("http://127.0.0.1:11434") and wyslane["body"]["model"] == "qwen3:8b"
    assert "provider" not in wyslane["body"] and "Authorization" not in (wyslane["headers"] or {})


def test_pobierz_od_nowa_czysci_postep(tmp_path, monkeypatch):
    from radar import cli, config
    from radar.zrodla import mapadotacji, radon
    monkeypatch.setattr(config, "BAZA", tmp_path / "t.sqlite")
    con = db.polacz()
    mapadotacji._postep(con, "radon:token", "stary")
    widziane = []
    monkeypatch.setattr(radon, "pobierz_wszystko", lambda c: widziane.append(mapadotacji._postep(c, "radon:token")) or 0)
    cli.main(["pobierz", "radon", "--od-nowa"])
    assert widziane == [None]
