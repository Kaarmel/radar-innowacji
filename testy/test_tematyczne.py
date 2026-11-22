"""Zapotrzebowanie, finansowanie (R4) i partnerzy tylko z dokumentów o tym samym problemie: AI potwierdza temat,
bo podobieństwo słów myli przedmiot (np. bezdomne zwierzęta i bezdomność ludzi)."""
from radar import ai, db, filtry, sprawdz
from radar.model import Dokument, WynikFiltra, Zgloszenie

LUDZIE = Dokument(id="mapadotacji:10", zrodlo="mapadotacji", typ="projekt", tytul="Aktywizacja zawodowa osób bezdomnych",
                  opis="Wsparcie mężczyzn w kryzysie bezdomności.", link="https://mapadotacji.gov.pl/projekty/10/",
                  instytucje=["Fundacja Dach nad Głową"])
ZWIERZETA = Dokument(id="mapadotacji:11", zrodlo="mapadotacji", typ="projekt", tytul="Schronisko dla bezdomnych zwierząt",
                     opis="Gmina buduje schronisko i system zgłaszania zwierząt.", link="https://mapadotacji.gov.pl/projekty/11/",
                     instytucje=["Gmina Zielona"])
OCENY = {LUDZIE.id: {"ten_sam": False, "uzasadnienie": "ludzie, nie zwierzęta"},
         ZWIERZETA.id: {"ten_sam": True, "uzasadnienie": "zwierzęta"}}


def _z():
    return Zgloszenie(id=None, wejscie="radar", tytul="Aplikacja do zgłaszania rannych zwierząt",
                      opis="Uczniowie zaprojektowali aplikację: zdjęcie rannego lub bezdomnego zwierzęcia wskazuje najbliższą pomoc.",
                      link=None, instytucja="Technikum w Trzcianie", typ_instytucji="szkola_ponadpodstawowa",
                      typ_innowacji="techniczna", etap="pomysl", wiek_przedzial="16_30", organizacja="pci")


def test_tematyczne_usuwa_dokument_o_innym_problemie(monkeypatch):
    monkeypatch.setattr(ai, "ten_sam_problem", lambda o, d: (OCENY, 0.001))
    koszt = []
    ranking, info = sprawdz._tematyczne(_z(), [(0.3, LUDZIE), (0.25, ZWIERZETA)], koszt)
    assert [d.id for _, d in ranking] == [ZWIERZETA.id]
    assert info["sprawdzono"] and info["odrzucone"][0]["tytul"] == LUDZIE.tytul
    assert koszt == [0.001]


def test_tematyczne_bez_odpowiedzi_ai_zostawia_ranking(monkeypatch):
    monkeypatch.setattr(ai, "ten_sam_problem", lambda o, d: ({}, 0.0))
    ranking, info = sprawdz._tematyczne(_z(), [(0.3, LUDZIE), (0.25, ZWIERZETA)], [])
    assert len(ranking) == 2 and not info["sprawdzono"]


def test_ten_sam_problem_odrzuca_obce_id(monkeypatch):
    monkeypatch.setattr(ai, "czat_json", lambda s, u: ({"oceny": [
        {"dokument_id": "obcy:1", "ten_sam_problem": "nie"},
        {"dokument_id": LUDZIE.id, "ten_sam_problem": "nie", "uzasadnienie": "u"}]}, 0.0))
    wynik, _ = ai.ten_sam_problem("opis", [LUDZIE])
    assert wynik == {LUDZIE.id: {"ten_sam": False, "uzasadnienie": "u"}}


def test_przelicz_podobne_zmienia_tylko_czesc_zalezna_od_podobnych(tmp_path, monkeypatch):
    con = db.polacz(tmp_path / "t.sqlite")
    db.zapisz_dokumenty(con, [LUDZIE, ZWIERZETA])
    zid = db.zapisz_zgloszenie(con, _z())
    nowosc = WynikFiltra("nowosc", 80.0, "zielone", [{"pytanie": f"Q{i}", "odpowiedz": "nie" if i == 4 else "tak",
                                                       "dokument_id": None} for i in range(1, 6)])
    wyniki = [WynikFiltra("plagiat", 0.0, "zielone", []), WynikFiltra("kopia", 20.0, "zielone", []),
              WynikFiltra("patent", 17.0, "zielone", []), nowosc]
    db.zapisz_wyniki(con, zid, wyniki, "dalej", "mlodzi_16_30", [], [{"nazwa": "Fundacja Dach nad Głową"}], 21.5, 0.001,
                     pokrycie={"ai": ["model"]})
    monkeypatch.setattr(sprawdz, "_lokalne", lambda con, z, t, df, N: [LUDZIE, ZWIERZETA])
    monkeypatch.setattr(filtry, "ranking", lambda z, k, df, N: [(0.3, LUDZIE), (0.25, ZWIERZETA)])
    monkeypatch.setattr(ai, "ten_sam_problem", lambda o, d: (OCENY, 0.001))
    sprawdz.przelicz_podobne(con, zid)
    k = db.karta(con, zid)
    assert [p["nazwa"] for p in k["partnerzy"]] == ["Gmina Zielona"]
    r4 = next(r for r in k["rekomendacje"] if r["reguly"] == ["R4"])
    assert ZWIERZETA.tytul in r4["powod"] and LUDZIE.tytul not in r4["powod"]
    assert {w["filtr"]: w["pasmo"] for w in k["wyniki"]} == {"plagiat": "zielone", "kopia": "zielone", "patent": "zielone",
                                                             "nowosc": "zielone"}
    assert k["werdykt"] == "dalej" and k["czas_s"] == 21.5 and k["pokrycie"]["ai"] == ["model"]
    assert k["pokrycie"]["tematy"]["odrzucone"][0]["tytul"] == LUDZIE.tytul
    zap = next(x for x in k["potencjal"]["kryteria"] if x["id"] == "zapotrzebowanie")
    assert [d["instytucja"] for d in zap["dowody"]] == ["Gmina Zielona"]
