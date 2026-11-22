"""Formularz „Szukam rozwiązania” wysyła puste pole „Od roku” (rok_od=); strona ma pokazać wyniki, nie błąd 422."""
from .test_app import POLA, klient  # noqa: F401


def test_puste_od_roku_z_formularza_nie_daje_bledu(klient):
    klient.post("/zglos", data=POLA)
    r = klient.get("/szukaj", params={"q": "czujnik powietrza", "zrodlo": "", "woj": "", "rok_od": ""})
    assert r.status_code == 200
    assert "Szukam rozwiązania" in r.text


def test_rok_od_z_formularza_dziala_i_bledny_jest_pomijany(klient):
    assert klient.get("/szukaj", params={"q": "czujnik powietrza", "rok_od": "2020"}).status_code == 200
    assert klient.get("/szukaj", params={"q": "czujnik powietrza", "rok_od": "abc"}).status_code == 200
    assert klient.get("/api/szukaj", params={"q": "czujnik powietrza", "rok_od": ""}).status_code == 200
