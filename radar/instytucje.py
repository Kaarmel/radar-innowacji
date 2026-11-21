"""Porównanie nazw instytucji: reguła „własnej pracy” (dopasowanie do dokumentów tej samej instytucji nie odrzuca)."""
from .tekst import tokeny

POMIJANE = {"sp", "z", "o", "oo", "im", "w", "i", "we", "na", "s", "a", "sa", "spolka", "the", "of", "and", "ul"}
OGOLNE = {"szkola", "szkol", "podstawowa", "zespol", "gmina", "miasto", "powiat", "uniwersytet", "politechnika", "instytut",
          "akademia", "liceum", "technikum", "ogolnoksztalcace", "nr", "panstwowa", "wyzsza", "publiczna", "centrum",
          "fundacja", "stowarzyszenie", "urzad", "miejski", "gminny", "wojewodztwo", "przedszkole", "university", "institute"}


def normalizuj(n: str) -> frozenset[str]:
    return frozenset(t for t in tokeny(n) if t not in POMIJANE)


def _ta_sama(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    if len(a & b) / len(a | b) >= 0.6:
        return True
    mniejszy, wiekszy = (a, b) if len(a) <= len(b) else (b, a)
    return len(mniejszy) >= 2 and mniejszy <= wiekszy and bool(mniejszy - OGOLNE)


def ta_sama(a: str, b: list[str]) -> bool:
    na = normalizuj(a)
    return any(_ta_sama(na, normalizuj(x)) for x in b or [])
