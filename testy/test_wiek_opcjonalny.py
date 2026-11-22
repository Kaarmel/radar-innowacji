"""Pole „Wiek twórców, jeśli wiadomo” jest opcjonalne: puste nie blokuje zgłoszenia (jak w radarze: nieznany = zespół mieszany)."""
from radar import db

from .test_app import POLA, klient  # noqa: F401


def test_puste_pole_wieku_nie_blokuje_zgloszenia(klient):
    r = klient.post("/zglos", data={**POLA, "wiek_przedzial": ""}, follow_redirects=False)
    assert r.status_code == 303, r.text[:300]
    z = db.polacz().execute("SELECT wiek_przedzial FROM zgloszenie ORDER BY id DESC LIMIT 1").fetchone()
    assert z[0] == "mieszany"


def test_bledny_wiek_nadal_jest_bledem(klient):
    r = klient.post("/zglos", data={**POLA, "wiek_przedzial": "sto_lat"}, follow_redirects=False)
    assert r.status_code != 303
