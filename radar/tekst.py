"""Tekst: tokeny, rdzenie (reszta w zadaniu 2)."""
import re
import unicodedata

_PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def bez_diakrytykow(t: str) -> str:
    t = (t or "").translate(_PL)
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def tokeny(t: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", bez_diakrytykow(t).lower())


def rdzen(token: str) -> str:
    return token[:6] if len(token) > 6 else token
