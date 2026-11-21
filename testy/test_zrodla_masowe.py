import json
from pathlib import Path

import pytest

from radar import siec
from radar.zrodla import interreg, mapadotacji, radon

D = Path(__file__).parent / "dane"


def test_mapadotacji_parsuj():
    docs = mapadotacji.parsuj(json.loads((D / "mapadotacji_1.json").read_text(encoding="utf-8")))
    d = docs[0]
    assert d.id == "mapadotacji:1855670"
    assert d.typ == "projekt" and d.zrodlo == "mapadotacji"
    assert "<" not in d.opis and len(d.opis) > 50
    assert d.tytul.startswith("„Gminny Program Rewitalizacji")
    assert d.link == "https://mapadotacji.gov.pl/projekty/1855670/"


def test_mapadotacji_beneficjent_z_html():
    html = (D / "mapadotacji_strona.html").read_text(encoding="utf-8")
    assert mapadotacji.beneficjent_z_html(html) == "Gmina Czarna"


def test_interreg_parsuj():
    docs = interreg.parsuj(D / "interreg_mini.xlsx")
    assert len(docs) == 3
    d = docs[0]
    assert d.id == "interreg:PLSK.01.01-IP.01-0001/23"
    assert d.instytucje and d.instytucje[0].startswith("Gmina Kęty")
    assert d.rok == 2023 and len(d.opis) > 100


def test_radon_parsuj_bez_nazwisk():
    surowe = json.loads((D / "radon_1.json").read_text(encoding="utf-8"))
    docs = radon.parsuj(surowe)
    assert len(docs) == 2
    d = docs[0]
    assert d.id == "radon:61978f6914f9235546114ca8"
    assert d.instytucje and "Instytut" in d.instytucje[0]
    tekst = json.dumps([x.__dict__ for x in docs], ensure_ascii=False)
    for r in surowe["results"]:
        for m in r.get("projectManagers") or []:
            for k, v in m.items():
                if k.lower().endswith(("name", "surname")) and "institution" not in k.lower() and v:
                    assert str(v) not in tekst


def test_robots_zakaz():
    siec.ustaw_robots("przyklad.test", "User-agent: *\nDisallow: /")
    with pytest.raises(siec.Zablokowane):
        siec.pobierz("https://przyklad.test/strona")


def test_mapadotacji_stronicowanie_stabilne(tmp_path, monkeypatch):
    """WP REST bez stałego sortowania zwraca duplikaty między stronami (20 069 pobranych → 14 791 unikalnych)."""
    from radar import db, siec
    from radar.zrodla import mapadotacji

    wywolania = []

    class Odp:
        status_code = 200
        headers = {"X-WP-Total": "150"}
        text = "[]"

    def pobierz(url, params=None, **kw):
        wywolania.append(params)
        return Odp()
    monkeypatch.setattr(siec, "pobierz", pobierz)
    mapadotacji.pobierz_wszystko(db.polacz(tmp_path / "t.sqlite"), log=lambda *a: None)
    strony = [p for p in wywolania if p.get("per_page") == 100]
    assert len(strony) == 2 and all(p.get("orderby") == "id" and p.get("order") == "asc" for p in strony)
