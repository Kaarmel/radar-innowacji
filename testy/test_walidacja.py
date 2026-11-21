from radar import walidacja


def k(plagiat="zielone", kopia="zielone", patent="zielone", nowosc="zielone", uwaga="", wlasna=False, potencjal=50):
    return {"wyniki": [{"filtr": "plagiat", "pasmo": plagiat, "uwaga": uwaga, "wlasna_praca": wlasna},
                       {"filtr": "kopia", "pasmo": kopia, "uwaga": "", "wlasna_praca": False},
                       {"filtr": "patent", "pasmo": patent, "uwaga": "", "wlasna_praca": False},
                       {"filtr": "nowosc", "pasmo": nowosc, "uwaga": "", "wlasna_praca": False}],
            "potencjal": {"wynik": potencjal}, "czas_s": 10.0, "koszt_usd": 0.001}


def test_czulosc_dwie_trzecie():
    wiersze = [("plagiat", k(plagiat="czerwone")), ("plagiat", k(plagiat="czerwone")), ("plagiat", k(plagiat="zolte"))]
    m = walidacja.miary(wiersze, etykiety={})
    assert m["plagiat"] == {"trafione": 2, "wszystkie": 3, "czulosc": 0.67}


def test_rodzaje_oczekiwan():
    assert walidacja.trafione("parafraza", k(kopia="zolte"))
    assert not walidacja.trafione("parafraza", k(kopia="zielone"))
    assert walidacja.trafione("wlasna", k(plagiat="zielone", wlasna=True))
    assert not walidacja.trafione("wlasna", k(plagiat="czerwone", wlasna=True))
    assert walidacja.trafione("duplikat", k(plagiat="czerwone", uwaga="duplikat zgłoszenia"))


def test_zgodnosc_z_etykietami():
    wiersze = [("etykieta:1", k(nowosc="zielone", potencjal=70)), ("etykieta:2", k(nowosc="czerwone", potencjal=30)),
               ("etykieta:3", k(nowosc="zielone", potencjal=65))]
    m = walidacja.miary(wiersze, etykiety={"1": "nowosc", "2": "rutyna", "3": "rutyna"})
    assert m["etykiety"]["zgodnosc"] == 0.67 and m["etykiety"]["n"] == 3
    assert m["etykiety"]["potencjal_nowosc"] == 70 and m["etykiety"]["potencjal_rutyna"] == 47.5


def test_opis_nie_twierdzi_o_etykietach_gdy_ich_brak(tmp_path, monkeypatch):
    from radar import db
    monkeypatch.setattr(walidacja, "ETYKIETY", tmp_path / "brak.csv")
    monkeypatch.setattr(walidacja, "RAPORT_JSON", tmp_path / "r.json")
    monkeypatch.setattr(walidacja, "KATALOG", tmp_path)
    monkeypatch.setattr(walidacja, "RAPORT_MD", tmp_path / "r.md")
    con = db.polacz(tmp_path / "t.sqlite")
    con.execute("CREATE TABLE test(zgl_id INTEGER, rodzaj TEXT, filtr TEXT, oczekiwane TEXT)")
    w = walidacja.raport(con, log=lambda *a: None)
    assert "nadał człowiek" not in w["opis"] and "nie zostały jeszcze" in w["opis"]


def test_opis_etykiet_mowi_kto_je_nadal():
    assert "nadał człowiek" in walidacja.opis_etykiet("człowiek", True)
    o = walidacja.opis_etykiet("głosowanie 5 modeli (a, b)", True)
    assert "głosowanie 5 modeli" in o and "nie ocena człowieka" in o and "nadał człowiek" not in o
    assert "nie zostały jeszcze" in walidacja.opis_etykiet("człowiek", False)
