import json
from pathlib import Path

import pytest

from radar.zrodla import BrakDostepu, crossref, epo, openalex, radon_patenty

D = Path(__file__).parent / "dane"


def test_crossref_parsuj():
    docs = crossref.parsuj(json.loads((D / "crossref.json").read_text()))
    assert all(d.zrodlo == "crossref" and d.typ == "publikacja" and d.jezyk == "en" for d in docs)
    assert all(d.link.startswith("https://") for d in docs)


def test_openalex_abstrakt_z_indeksu():
    assert openalex.abstrakt({"Ala": [0], "kota": [2], "ma": [1]}) == "Ala ma kota"
    docs = openalex.parsuj(json.loads((D / "openalex.json").read_text()))
    assert docs[0].opis.startswith("Microplastics") and docs[0].instytucje


def test_openalex_bez_klucza(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    with pytest.raises(BrakDostepu):
        openalex.szukaj(["microplastic filter"])


def test_epo_status_i_grupowanie():
    docs = epo.parsuj(json.loads((D / "epo_sparql.json").read_text()))
    d = docs[0]
    assert d.id.startswith("epo:EP") and d.typ == "patent" and d.status in {"zgloszenie", "udzielony"}
    assert d.link.startswith("https://worldwide.espacenet.com/patent/search?q=pn%3DEP")
    assert len({x.id for x in docs}) == len(docs)
    assert epo.status_z_kodu("B1") == "udzielony" and epo.status_z_kodu("A1") == "zgloszenie"


def test_epo_zapytanie_lucene():
    q = epo.zapytanie(["microplastic filter", "fish gills"])
    assert q.startswith("(") and q.endswith(")")
    assert "microplast*" in q and "filter*" in q and "gill*" in q and " OR " in q


def test_epo_abstrakt_z_xml():
    assert "microplastic" in epo.abstrakt_z_xml((D / "eps_EP4424149A1.xml").read_text()).lower() or \
        len(epo.abstrakt_z_xml((D / "eps_EP4424149A1.xml").read_text())) > 50


def test_radon_patenty_bez_tworcow():
    surowe = json.loads((D / "radon_patenty.json").read_text())
    docs = radon_patenty.parsuj(surowe)
    d = docs[0]
    assert d.typ == "patent" and d.status == "udzielony" and d.zrodlo == "radon_patenty"
    assert d.link.startswith("https://worldwide.espacenet.com/patent/search?q=pn%3DPL")
    tekst = json.dumps([x.__dict__ for x in docs], ensure_ascii=False)
    for r in surowe["results"]:
        for inv in r.get("inventors") or []:
            for osoba in inv.get("persons") or []:
                for k in ("firstName", "lastName", "name", "surname"):
                    if osoba.get(k):
                        assert osoba[k] not in tekst
