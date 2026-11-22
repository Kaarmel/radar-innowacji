"""Każda ścieżka dalej ma oczekiwany miernik skuteczności (zadanie PCI §6 e)."""
import json

from radar import db, slowniki

from .test_app import POLA, klient  # noqa: F401


def test_kazda_regula_sciezki_ma_miernik():
    from radar.werdykt import DOMYSLNE
    for r in list(DOMYSLNE) + ["PRZEGLAD", "ODRZUCENIE"]:
        assert slowniki.MIERNIKI.get(r), r


def test_karta_pokazuje_miernik_przy_sciezce(klient):
    klient.post("/zglos", data=POLA)
    con = db.polacz()
    rek = [{"nazwa": "Finansowanie: programy podobnych projektów", "powod": "Podobne projekty.", "reguly": ["R4"]}]
    with con:
        con.execute("UPDATE zgloszenie SET status='gotowe', werdykt='dalej', rekomendacje=? WHERE id=1", (json.dumps(rek),))
    s = klient.get("/karta/1").text
    assert "Miernik skuteczności" in s
    assert slowniki.MIERNIKI["R4"] in s
