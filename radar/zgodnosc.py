"""Zgodność ocen na próbie 50: DeepSeek (karty.jsonl) vs sędzia (karty_sedzia.jsonl) vs ręczne (etykiety_wyniki.json, jeśli jest).

Numery wpisów = numery na stronie dane/etykiety.html (ta sama kolejność co etykiety_proba.json).
Użycie: python3 radar/zgodnosc.py [ścieżka do etykiety_wyniki.json]
"""
import json
import os
import sys

DANE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dane")


def wczytaj(plik):
    p = os.path.join(DANE, plik)
    return {k["link"]: k for k in map(json.loads, open(p, encoding="utf-8"))} if os.path.exists(p) else {}


def zgodnosc(a, b):
    wspolne = [k for k in a if k in b]
    return sum(a[k] == b[k] for k in wspolne), len(wspolne)


def main(reczne_plik=os.path.expanduser("~/Downloads/etykiety_wyniki.json")):
    proba = json.load(open(os.path.join(DANE, "etykiety_proba.json"), encoding="utf-8"))
    ds, sd = wczytaj("karty.jsonl"), wczytaj("karty_sedzia.jsonl")
    oc = {"DeepSeek": {}, "sędzia": {}, "ręczne": {}}
    for x in proba:
        l = x["link"]
        oc["DeepSeek"][l] = ds.get(l, {}).get("czy_inicjatywa")
        oc["sędzia"][l] = sd.get(l, {}).get("czy_inicjatywa")
    if os.path.exists(reczne_plik):
        oc["ręczne"] = {l: v.get("o") for l, v in json.load(open(reczne_plik, encoding="utf-8")).items() if v.get("o")}
    nazwy = [n for n in oc if oc[n]]
    for i, a in enumerate(nazwy):
        for b in nazwy[i + 1:]:
            z, n = zgodnosc(oc[a], oc[b])
            print(f"{a} vs {b}: {z}/{n} zgodnych")
    print("\nRozbieżności (nr na stronie etykiety.html):")
    for i, x in enumerate(proba, 1):
        w = {n: oc[n].get(x["link"]) for n in nazwy}
        if len(set(w.values())) > 1:
            print(f"  nr {i:2} (pkt {x['pkt']}): " + ", ".join(f"{n}={v}" for n, v in w.items()),
                  "|", sd.get(x["link"], ds.get(x["link"], {})).get("uzasadnienie", "")[:110])


if __name__ == "__main__":
    assert zgodnosc({"a": "tak", "b": "nie"}, {"a": "tak", "b": "tak", "c": "nie"}) == (1, 2)
    main(*sys.argv[1:2])
