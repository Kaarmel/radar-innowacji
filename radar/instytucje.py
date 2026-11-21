"""Szkoły i placówki z Podkarpacia (RSPO) → dane/instytucje.jsonl

Lista RSPO (zebrana wcześniej) nie ma województwa, więc dla kandydatów (kody pocztowe 33, 35–39)
pobieramy szczegóły (rspo.gov.pl/api/Institution/<id>) i zostawiamy te z TERYT gminy 18… (podkarpackie).
Zapisujemy tylko pola z białej listy: bez dyrektora, telefonów, e-maili i osób prowadzących.
Placówki prowadzone przez osobę fizyczną pomijamy w całości (ich nazwa to często imię i nazwisko).
Wznawialne: już pobrane id są pomijane.  Użycie: python3 radar/instytucje.py
"""
import gzip
import json
import os
import time
import urllib.request

TU = os.path.dirname(os.path.abspath(__file__))
LISTA = os.path.join(TU, "..", "..", "HackNation 2026", "dane_przygotowane", "rspo", "placowki.jsonl.gz")
WY = os.path.join(TU, "..", "dane", "instytucje.jsonl")
POMINIETE = os.path.join(TU, "..", "dane", "instytucje_pominiete.txt")  # id spoza Podkarpacia / prowadzone przez osoby


def szczegoly(id_):
    for i in range(4):
        try:
            req = urllib.request.Request(f"https://rspo.gov.pl/api/Institution/{id_}", headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            print("  ponawiam", id_, e, flush=True)
            time.sleep(10 * (i + 1))
    return None


def wybierz(d):
    """Biała lista pól; None, gdy spoza Podkarpacia albo prowadzona przez osobę fizyczną."""
    teryt = d.get("hqAddressCommuneTerytCode") or ""
    if not teryt.startswith("18"):
        return None
    prowadzacy = d.get("leadAuthorities") or []
    if any(a.get("firstName") or a.get("surname") for a in prowadzacy):
        return None
    loc = d.get("hqAddressLocality") or {}
    gm = loc.get("commune") or {}
    geo = d.get("hqAddressGeotag") or {}
    return {
        "rspo": d["rspo"], "nazwa": d["name"], "regon": d.get("regon"),
        "typ": (d.get("institutionType") or {}).get("name"),
        "publiczna": (d.get("publicStatus") or {}).get("name"),
        "etapy": [e["name"] for e in d.get("educationStageList") or []],
        "prowadzacy": [a["name"] for a in prowadzacy],
        "teryt_gminy": teryt, "simc": d.get("hqSimc"),
        "miejscowosc": loc.get("name"), "gmina": gm.get("name"), "powiat": (gm.get("district") or {}).get("name"),
        "lat": geo.get("latitude"), "lon": geo.get("longitude"),
        "www": (d.get("website") or "").strip(), "uczniowie": d.get("studentsNr"),
        "utworzona": (d.get("creationDate") or "")[:10],
    }


def main():
    os.makedirs(os.path.dirname(WY), exist_ok=True)
    gotowe = set()
    for p in (WY, POMINIETE):
        if os.path.exists(p):
            gotowe |= {json.loads(l)["rspo"] if p == WY else int(l) for l in open(p, encoding="utf-8") if l.strip()}
    kandydaci = [r["id"] for r in map(json.loads, gzip.open(LISTA, "rt", encoding="utf-8"))
                 if r["hqAddressZipCode"][:2] in ("33", "35", "36", "37", "38", "39") and not r.get("liquidationDate")]
    todo = [i for i in kandydaci if i not in gotowe]
    print(f"kandydaci {len(kandydaci)}, do pobrania {len(todo)}", flush=True)
    with open(WY, "a", encoding="utf-8") as f, open(POMINIETE, "a", encoding="utf-8") as fp:
        for n, id_ in enumerate(todo, 1):
            d = szczegoly(id_)
            if d is None:
                continue  # spróbuje przy następnym uruchomieniu
            w = wybierz(d)
            if w:
                f.write(json.dumps(w, ensure_ascii=False) + "\n")
                f.flush()
            else:
                fp.write(f"{id_}\n")
                fp.flush()
            if n % 200 == 0:
                print(f"{n}/{len(todo)}", flush=True)
            time.sleep(1)
    print("gotowe", flush=True)


if __name__ == "__main__":
    assert wybierz({"hqAddressCommuneTerytCode": "1008021"}) is None
    w = wybierz({"rspo": 1, "name": "SP 1", "hqAddressCommuneTerytCode": "1863011", "telephone": "1", "email": "a@b",
                 "directorName": "Jan", "leadAuthorities": [{"name": "Gmina Rzeszów", "firstName": ""}]})
    assert w["prowadzacy"] == ["Gmina Rzeszów"] and "telephone" not in w and "directorName" not in w
    assert wybierz({"hqAddressCommuneTerytCode": "1863011", "leadAuthorities": [{"name": "Jan K", "firstName": "Jan"}]}) is None
    main()
