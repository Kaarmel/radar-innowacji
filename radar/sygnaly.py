"""Wstępna, wyjaśnialna ocena wpisu: czy może opisywać oddolną inicjatywę (bez LLM).

Wynik = suma wag dopasowanych grup słów; każda grupa zwraca słowo, które ją uruchomiło (dowód).
To filtr przed ekstrakcją LLM (mniej tekstów, niższy koszt), a nie ocena potencjału.
Użycie: python3 radar/sygnaly.py dane/wpisy.jsonl   → wypisuje ranking
"""
import json
import re
import sys

GRUPY = [  # (nazwa, waga, wzorzec); wzorce na małych literach
    ("tworzenie", 3, r"\b(zbudowal|skonstruowal|zaprojektowal|stworzyl|opracowal|wymyslil|przygotowal\w* (wlasn|autorsk)|autorski)\w*"),
    ("technologia", 2, r"\b(robot|programowan|kodowan|steam|stem|druk\w* 3d|drukark\w* 3d|dron|aplikacj|sztuczn\w* inteligencj|arduino|micro:?bit|lego|mbot|vr\b|ar\b|elektronik)\w*"),
    ("projekt i finansowanie", 2, r"\b(projekt\w*|grant\w*|erasmus|dofinansowan\w*|fundusz\w*|program\w* (unijn|rządow|ministerialn)\w*|eTwinning|laboratori\w* przyszłości)"),
    ("nagroda i skala", 2, r"\b(laureat\w*|finali\w*|zwycięz\w*|wyróżnieni\w*|nagrod\w*|ogólnopolsk\w*|wojewódzk\w*|międzynarodow\w*|krajow\w*)"),
    ("społeczność i wpływ", 1, r"\b(wolontariat\w*|wolontariusz\w*|inicjatyw\w*|akcj\w* (charytatywn|ekologiczn)\w*|ekolog\w*|klimat\w*|seniorów|mieszkańc\w*|lokaln\w* społeczn\w*|integracj\w*)"),
    ("nauka", 1, r"\b(eksperyment\w*|badani\w*|naukow\w*|koło (naukowe|zainteresowań)|innowac\w*|startup\w*|start-up\w*|przedsiębiorczoś\w*)"),
    ("rutyna", -3, r"\b(jadłospis\w*|zebrani\w* z rodzicami|wywiadówk\w*|dni wolne|kalendarz roku|harmonogram\w*|odpłatnoś\w*|odpis\w* za obiady|godziny pracy|dyżur\w*|rekolekcj\w*|żegnamy|kondolencj\w*|ślubowani\w*|bezpłatne przejazdy)"),
    ("uroczystość", -1, r"\b(akademi\w* z okazji|apel\w*|święt\w* niepodległości|dzień (dyni|postaci z bajek|chłopaka|kobiet|babci|dziadka)|andrzejk\w*|mikołajk\w*|wigili\w*)"),
]
WZORCE = [(n, w, re.compile(p, re.I)) for n, w, p in GRUPY]


def bez_ogonkow(t):
    return t.translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))


def ocena(tekst):
    """→ (punkty, {grupa: przykładowe słowo}). Grupa liczy się raz, niezależnie od liczby powtórzeń."""
    t = (tekst or "").lower()
    trafienia = {}
    for nazwa, waga, wz in WZORCE:
        m = wz.search(t) or wz.search(bez_ogonkow(t))
        if m:
            trafienia[nazwa] = m.group(0)
    return sum(w for n, w, _ in WZORCE if n in trafienia), trafienia


def main(plik):
    w = [json.loads(l) for l in open(plik, encoding="utf-8")]
    for x in w:
        x["punkty"], x["sygnaly"] = ocena(x["tytul"] + " " + x["tekst"][:3000])
    w.sort(key=lambda x: -x["punkty"])
    for x in w:
        print(f"{x['punkty']:3d} | {x['tytul'][:60]:60s} | {', '.join(f'{k}: {v}' for k, v in x['sygnaly'].items())}")


if __name__ == "__main__":
    p, t = ocena("Uczniowie zbudowali robota i zostali laureatami ogólnopolskiego konkursu")
    assert p == 7 and t["tworzenie"].startswith("zbudowal") and "nagroda i skala" in t, (p, t)
    assert ocena("Jadłospis na listopad")[0] < 0
    assert ocena("")[0] == 0
    main(sys.argv[1])
