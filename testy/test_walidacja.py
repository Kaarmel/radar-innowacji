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
