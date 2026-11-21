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



def test_zestaw_kontrolny_liczony_osobno():
    """Zestaw kontrolny: projekty, których nie widziała żadna poprawka rubryki; zgodność liczona oddzielnie."""
    wiersze = [("etykieta:1", k(nowosc="zolte")), ("kontrolny:2", k(nowosc="zolte", potencjal=60)),
               ("kontrolny:3", k(nowosc="czerwone", potencjal=10)), ("kontrolny:4", k(nowosc="czerwone"))]
    m = walidacja.miary(wiersze, etykiety={"1": "rutyna"}, kontrolne={"2": "nowosc", "3": "rutyna", "4": "nowosc"})
    assert m["etykiety"]["n"] == 1 and m["etykiety"]["zgodnosc"] == 0.0
    assert m["kontrolny"]["n"] == 3 and m["kontrolny"]["zgodnosc"] == 0.67


def test_zestaw_kontrolny_pomija_projekty_juz_uzyte(tmp_path, monkeypatch):
    from radar import db
    from radar.model import Dokument
    monkeypatch.setattr(walidacja, "KONTROLNE", tmp_path / "kontrolne.csv")
    monkeypatch.setattr(walidacja, "KATALOG", tmp_path)
    con = db.polacz(tmp_path / "t.sqlite")
    opis = "Projekt obejmuje prace B+R i wdrożenie nowej technologii produkcji w przedsiębiorstwie. " * 8
    db.zapisz_dokumenty(con, [Dokument(id=f"mapadotacji:{i}", zrodlo="mapadotacji", typ="projekt", tytul=f"Projekt {i}",
                                       opis=opis, link=f"https://m/{i}", instytucje=["Firma"]) for i in range(1, 7)])
    uzyty = walidacja._zgl(con, "Projekt 1", opis, "Firma", zrodlo_dok="mapadotacji:1")
    with con:
        con.execute("CREATE TABLE IF NOT EXISTS test(zgl_id INTEGER, rodzaj TEXT, filtr TEXT, oczekiwane TEXT)")
        con.execute("INSERT INTO test VALUES(?,?,?,?)", (uzyty, "etykieta", "nowosc", "etykieta"))
    ids = walidacja.zbuduj_kontrolny(con, n_losowe=3, n_br=2, log=lambda *a: None)
    zrodla = {db.karta(con, z)["zrodlo_dok"] for z in ids}
    assert len(ids) == 5 and "mapadotacji:1" not in zrodla
    assert {r for (r,) in con.execute("SELECT rodzaj FROM test WHERE zgl_id IN (%s)" % ",".join(map(str, ids)))} == {"kontrolny"}
    assert (tmp_path / "kontrolne.csv").read_text(encoding="utf-8").count("\n") == 6



def test_kontrolny_auc_potencjalu_i_werdykty():
    """Miara bez progu: jak często projekt z etykietą „nowość” ma wyższy potencjał niż „rutyna” (AUC); do tego decyzje lejka."""
    def kw(pot, werdykt, nowosc="zolte"):
        return k(nowosc=nowosc, potencjal=pot) | {"werdykt": werdykt}
    wiersze = [("kontrolny:1", kw(80, "dalej")), ("kontrolny:2", kw(30, "do_przegladu")),
               ("kontrolny:3", kw(20, "odrzucone_do_przegladu", "czerwone")), ("kontrolny:4", kw(30, "odrzucone_do_przegladu"))]
    m = walidacja.miary(wiersze, etykiety={}, kontrolne={"1": "nowosc", "2": "nowosc", "3": "rutyna", "4": "rutyna"})
    assert m["kontrolny"]["auc_potencjalu"] == 0.88  # (1 + 1 + 1 + 0.5) / 4
    assert m["kontrolny"]["werdykty"] == {"nowosc": {"dalej": 1, "do_przegladu": 1}, "rutyna": {"odrzucone_do_przegladu": 2}}
