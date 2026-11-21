"""Liczby o Podkarpaciu do opisu projektu → liczby.md (każda liczba z plikiem źródłowym).

Użycie: python3 radar/liczby.py
"""
import csv
import glob
import gzip
import json
import os
import re
import sys
from collections import Counter

TU = os.path.dirname(os.path.abspath(__file__))
DP = os.path.join(TU, "..", "..", "HackNation 2026", "dane_przygotowane")
DANE = os.path.join(TU, "..", "dane")
csv.field_size_limit(sys.maxsize)

TYPY = [  # kolejność ma znaczenie: pierwsze dopasowanie wygrywa
    ("uczelnia", r"uniwersytet|politechnik|wyższa szkoła|szkoła wyższa|uczelni|akademia nauk stosowanych|państwowa wyższa"),
    ("szkoła / przedszkole", r"szkoł|przedszkol|liceum|technikum|zespół szkół|centrum kształcenia|żłobek"),
    ("samorząd (gmina, powiat, województwo)", r"^(gmina|miasto|powiat|województwo)\b|urząd (gminy|miasta|marszałkowski)|starostwo"),
    ("NGO, Caritas, parafie", r"fundacj|stowarzysz|towarzystw|związek|koło gospodyń|ochotnicza straż|caritas|parafi|diecezj|zgromadzeni|izba gospodarcza|forum"),
    ("firma", r"sp\. ?z ?o\.? ?o|sp\. ?o\.? ?o|spółka|s\.a\.|sp\. ?k\.|sp\. ?j\.|przedsiębiorstw|p\.? ?p\.? ?u\.? ?h|f\.? ?h\.? ?u|zakład|firma|group"),
    ("inna instytucja publiczna", r"szpital|muzeum|bibliotek|dom kultury|park narodowy|urząd|dyrekcja|wody polskie|państwow|komenda|policj|instytut|pomocy społecznej|pomocy rodzin"),
]


def typ_beneficjenta(nazwa):
    """Typ z nazwy. „POWIAT X / ZESPÓŁ SZKÓŁ…”: projekt realizuje jednostka po ukośniku, więc to ona decyduje."""
    n = (nazwa or "").lower().strip()
    if "/" in n and n.rsplit("/", 1)[1].strip():
        n = n.rsplit("/", 1)[1].strip()
    return next((t for t, wz in TYPY if re.search(wz, n)), "inne (głównie jednoosobowe firmy i prywatne ośrodki)")


def kwota(s):
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return 0.0


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


def tabela(licznik, n, kol=("", "liczba", "udział")):
    w = [f"| {kol[0]} | {kol[1]} | {kol[2]} |", "|---|---:|---:|"]
    w += [f"| {k} | {fmt(v)} | {v / n:.0%} |" for k, v in licznik.most_common()]
    return "\n".join(w)


def fe_2014_2020():
    p = os.path.join(DP, "fundusze_ue", "lista_fe_2014_2020.csv.gz")
    r = list(csv.reader(gzip.open(p, "rt", encoding="utf-8")))
    h, d = r[2], r[3:]
    i = {k: next(j for j, c in enumerate(h) if c.replace("\xa0", " ").startswith(k)) for k in
         ("Tytuł", "Skrócony", "Nazwa beneficjenta", "Wartość projektu", "Miejsce")}
    pk = [x for x in d if all(s.strip().startswith("WOJ.: PODKARPACKIE") for s in x[i["Miejsce"]].split("|"))]
    typy = Counter(typ_beneficjenta(x[i["Nazwa beneficjenta"]]) for x in pk)
    wart = Counter()
    for x in pk:
        wart[typ_beneficjenta(x[i["Nazwa beneficjenta"]])] += kwota(x[i["Wartość projektu"]])
    edu = [x for x in pk if re.search(r"szkoł|przedszkol|uczni", (x[i["Tytuł"]] + " " + x[i["Skrócony"]]).lower())]
    edu_typy = Counter(typ_beneficjenta(x[i["Nazwa beneficjenta"]]) for x in edu)
    out = [f"## Fundusze Europejskie 2014–2020, projekty realizowane tylko na Podkarpaciu: {fmt(len(pk))}",
           f"Źródło: `dane_przygotowane/fundusze_ue/lista_fe_2014_2020.csv.gz` (oficjalna lista projektów, stan 30.06.2026; {fmt(len(d))} projektów w Polsce). Typ beneficjenta rozpoznany z nazwy (reguły w `radar/liczby.py`), więc to przybliżenie. Projekty z miejscem „Cały kraj” (np. 28 z 36 projektów Uniwersytetu Rzeszowskiego i Politechniki Rzeszowskiej) nie są tu liczone.",
           "", "**Kto realizuje projekty (liczba projektów):**", "", tabela(typy, len(pk), ("typ beneficjenta", "projekty", "udział")),
           "", "**Wartość projektów według typu beneficjenta (mln zł):**", "",
           "| typ beneficjenta | mln zł | udział |", "|---|---:|---:|"]
    suma = sum(wart.values())
    out += [f"| {k} | {fmt(v / 1e6)} | {v / suma:.0%} |" for k, v in wart.most_common()]
    out += ["", f"**Projekty dotyczące szkół** (słowa „szkoł”, „przedszkol”, „uczni” w tytule lub opisie): {fmt(len(edu))}. Kto je realizuje:",
            "", tabela(edu_typy, len(edu), ("typ beneficjenta", "projekty", "udział"))]
    return "\n".join(out), pk, i


def mapa_dotacji():
    p = os.path.join(DP, "mapadotacji", "projekty_327.jsonl.gz")
    s = json.load(open(os.path.join(DP, "mapadotacji", "slowniki.json"), encoding="utf-8"))
    r = [json.loads(l) for l in gzip.open(p, "rt", encoding="utf-8")]
    kat = Counter(s["kategorie"].get(str(k), str(k)) for x in r for k in x["kategorie"])
    persp = Counter(s["perspektywy"].get(str(k), str(k)) for x in r for k in x["perspektywy"])
    return "\n".join([f"## Mapa Dotacji, Podkarpacie: {fmt(len(r))} projektów z opisami",
                      "Źródło: `dane_przygotowane/mapadotacji/projekty_327.jsonl.gz`. Projekt może mieć kilka kategorii.", "",
                      tabela(kat, len(r), ("kategoria", "projekty", "udział")), "",
                      tabela(persp, len(r), ("perspektywa", "projekty", "udział"))])


def rspo():
    p = os.path.join(DANE, "instytucje.jsonl")
    if not os.path.exists(p):
        return "## RSPO\n(jeszcze nie pobrane)"
    r = [json.loads(l) for l in open(p, encoding="utf-8")]
    www = [x for x in r if x["www"]]
    return "\n".join([f"## Szkoły i placówki z Podkarpacia (RSPO): {fmt(len(r))}, ze stroną WWW: {fmt(len(www))} ({len(www) / len(r):.0%})",
                      "Źródło: `radar-innowacji/dane/instytucje.jsonl` (rspo.gov.pl; bez placówek prowadzonych przez osoby fizyczne).", "",
                      tabela(Counter(x["typ"] for x in r), len(r), ("typ", "placówki", "udział")), "",
                      tabela(Counter(x["publiczna"] for x in r), len(r), ("status", "placówki", "udział")), "",
                      tabela(Counter(x["powiat"] for x in r), len(r), ("powiat", "placówki", "udział"))])


def zrodla_i_wpisy():
    """Pełny przebieg: dane/zrodla.csv (ostatni wiersz na stronę) i dane/wpisy.jsonl."""
    import datetime as dt
    from zrodla import ostatnie_zrodla
    from sygnaly import ocena
    z, w = os.path.join(DANE, "zrodla.csv"), os.path.join(DANE, "wpisy.jsonl")
    if not (os.path.exists(z) and os.path.exists(w)):
        return ""
    zr = ostatnie_zrodla(z)
    st = Counter(x["status"].split(":")[0] for x in zr.values())
    ze_zrodlem = sum(1 for x in zr.values() if x["status"] == "ok" and (x["rss"] or x["aktualnosci"]))
    wp = [json.loads(l) for l in open(w, encoding="utf-8")]
    szkoly = {x["zrodlo_id"] for x in wp}
    od = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    pkt = [ocena(x["tytul"] + " " + x["tekst"][:3000])[0] for x in wp]
    return "\n".join([f"## Strony szkół: pełny przebieg ({fmt(len(zr))} stron, jedna na domenę)",
                      f"- strona odpowiada: {fmt(st['ok'])}; ma RSS albo podstronę aktualności: {fmt(ze_zrodlem)}; "
                      f"błąd (domena nie istnieje, 404, certyfikat): {fmt(st['błąd'])}; zakaz w robots.txt: {fmt(st['robots'])}; "
                      f"domena przejęta przez obcą stronę: {fmt(st['obca domena'])}",
                      f"- wpisy (maks. 10 na stronę): {fmt(len(wp))} z {fmt(len(szkoly))} szkół; z datą publikacji: {fmt(sum(bool(x['data']) for x in wp))}; "
                      f"z ostatnich 30 dni: {fmt(sum(x['data'] >= od for x in wp))}",
                      f"- wstępny sygnał inicjatywy ≥ 3 pkt: {fmt(sum(p >= 3 for p in pkt))} wpisów, ≥ 5 pkt: {fmt(sum(p >= 5 for p in pkt))} (dopasowanie słów, nie ocena)",
                      "Źródło: `radar-innowacji/dane/zrodla.csv`, `wpisy.jsonl`."])


def main():
    fe, _, _ = fe_2014_2020()
    tekst = "\n\n".join(["# Liczby: Podkarpacie (wygenerowane przez `radar/liczby.py`)", fe, mapa_dotacji(), rspo(), zrodla_i_wpisy()])
    open(os.path.join(TU, "..", "liczby.md"), "w", encoding="utf-8").write(tekst + "\n")
    print(tekst)


if __name__ == "__main__":
    assert typ_beneficjenta("GMINA MIASTO RZESZÓW") == "samorząd (gmina, powiat, województwo)"
    assert typ_beneficjenta("Zespół Szkół Ekonomicznych w Rzeszowie") == "szkoła / przedszkole"
    assert typ_beneficjenta("Politechnika Rzeszowska im. Ignacego Łukasiewicza") == "uczelnia"
    assert typ_beneficjenta("ABC Sp. z o.o.") == "firma" and typ_beneficjenta("Fundacja Dobro") == "NGO, Caritas, parafie"
    assert typ_beneficjenta("CARITAS DIECEZJI RZESZOWSKIEJ") == "NGO, Caritas, parafie" and typ_beneficjenta("WOJEWÓDZKI URZĄD PRACY") == "inna instytucja publiczna"
    assert fmt(1234567) == "1 234 567"
    assert typ_beneficjenta("NIEPUBLICZNE PRZEDSZKOLE - AKADEMIA MAŁEGO GENIUSZA") == "szkoła / przedszkole"
    assert typ_beneficjenta("WYŻSZA SZKOŁA INFORMATYKI I ZARZĄDZANIA") == "uczelnia"
    assert typ_beneficjenta("POWIAT MIELECKI/POWIATOWE CENTRUM POMOCY RODZINIE") == "inna instytucja publiczna"
    assert typ_beneficjenta("CENTRUM UBEZPIECZEŃ I TURYSTYKI") .startswith("inne")
    main()
