"""dane/instytucje.jsonl → dane/wejscie.csv (id, www): jedna strona na domenę.

Kilka placówek z zespołu szkół ma zwykle tę samą stronę, więc bierzemy jedną (najwięcej uczniów).
"""
import csv
import json
import re
import os
import urllib.parse

DANE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dane")


WSPOLNE_HOSTY = {"gov.pl", "samorzad.gov.pl"}  # wiele szkół pod jedną domeną, różne ścieżki /web/<szkoła>


def pierwszy_adres(www):
    """Pole WWW bywa listą („a.pl, https://b.edupage.org”): bierzemy pierwszy adres."""
    return re.split(r"[,;\s]+", www.strip())[0]


def klucz(www):
    """Klucz strony: domena, a na wspólnych hostach domena + ścieżka."""
    u = pierwszy_adres(www).lower()
    u = u if "://" in u else "http://" + u
    d = domena(u)
    return d + "/" + urllib.parse.urlparse(u).path.strip("/") if d in WSPOLNE_HOSTY else d


def domena(www):
    u = www.strip().lower()
    u = u if "://" in u else "http://" + u
    h = urllib.parse.urlparse(u).netloc.split(":")[0]
    return h[4:] if h.startswith("www.") else h


def main():
    najlepsze = {}
    for x in map(json.loads, open(os.path.join(DANE, "instytucje.jsonl"), encoding="utf-8")):
        d = klucz(x["www"]) if x["www"].strip() else ""
        if "." not in d:
            continue
        if d not in najlepsze or (x["uczniowie"] or 0) > (najlepsze[d]["uczniowie"] or 0):
            najlepsze[d] = x
    with open(os.path.join(DANE, "wejscie.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "www"])
        for x in najlepsze.values():
            w.writerow([x["rspo"], pierwszy_adres(x["www"])])
    print("domen:", len(najlepsze))


if __name__ == "__main__":
    assert klucz("https://www.gov.pl/web/psmmielec") == "gov.pl/web/psmmielec" and klucz("sp1.pl/szkola") == "sp1.pl"
    assert pierwszy_adres("sp15krosno.pl, https://2lokrosno.edupage.org") == "sp15krosno.pl"
    assert domena("www.SP1.resman.pl/") == "sp1.resman.pl" and domena("https://www.a.pl:443/x") == "a.pl" and domena("brak") == "brak"
    main()
