"""Tekst: normalizacja, tokeny, rdzenie, TF-IDF, n-gramy i fragmenty wspólne (plagiat)."""
import html
import math
import re
import unicodedata
from collections import Counter
from typing import Callable

_PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")

STOP = frozenset("""
a aby ach acz aczkolwiek aj albo ale ani az bardziej bardzo bez bo bowiem by byc byl byla byli bylo byly bedzie beda
cala cali caly ci cie ciebie co cos czy czyli dla do dzis dzieki gdy gdyz gdzie go ich ile im inne ja jak jaki jakie
jako je jego jej jemu jesli jest jestem jeszcze jezeli juz ktora ktore ktory ktorych ktorym kto ku lub ma maja moze
mozna mu my na nad nam nas nasz nasza nasze nawet nia nic nich nie niego niej niemu nigdy nim nimi niz no o obok od
okolo on ona one oni ono oraz oto pan po pod podczas pomimo poniewaz poza przed przez przy roku sa sie skad soba sobie
swoje ta tak takie takze tam te tego tej ten teraz tez to toba tobie totez tu tutaj twoj ty tych tylko tym u w wam
was we wiec wiele wielu wszyscy wszystkich wszystko wtedy wy z za zawsze ze zeby zostal zostala zostaly zostalo
about after all also an and any are as at be been but by can could do for from had has have he her his how if in
into is it its may more most no not of on or other our out over she so some such than that the their them then there
these they this those through to under up was we were what when where which while who will with would you
""".split())


def bez_diakrytykow(t: str) -> str:
    t = (t or "").translate(_PL)
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def tokeny(t: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", bez_diakrytykow(t).lower())


def rdzen(token: str) -> str:
    return token[:6] if len(token) > 6 else token


def bez_html(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _rdzenie(t: str) -> list[str]:
    return [rdzen(x) for x in tokeny(t) if x not in STOP and len(x) > 1]


def _idf(termin: str, df: Callable[[str], int] | None, n: int) -> float:
    return math.log((n + 1) / ((df(termin) if df else 0) + 1)) + 1


def terminy(t: str, n: int = 15, df: Callable[[str], int] | None = None, N: int = 1) -> list[str]:
    """Najważniejsze rdzenie tekstu wg tf·idf (bez słów funkcyjnych)."""
    tf = Counter(_rdzenie(t))
    return [k for k, _ in sorted(tf.items(), key=lambda kv: (-kv[1] * _idf(kv[0], df, N), kv[0]))[:n]]


def _wektor(t: str, df: Callable[[str], int], n: int) -> dict[str, float]:
    return {k: v * _idf(k, df, n) for k, v in Counter(_rdzenie(t)).items()}


def podobienstwo(a: str, b: str, df: Callable[[str], int], N: int) -> float:
    """Cosinus TF-IDF na rdzeniach (0..1)."""
    va, vb = _wektor(a, df, N), _wektor(b, df, N)
    if not va or not vb:
        return 0.0
    il = sum(w * vb.get(k, 0.0) for k, w in va.items())
    return il / (math.sqrt(sum(w * w for w in va.values())) * math.sqrt(sum(w * w for w in vb.values())))


def _slowa(t: str) -> list[tuple[str, int, int]]:
    """(słowo znormalizowane, początek, koniec) w oryginalnym tekście."""
    out = []
    for m in re.finditer(r"\w+", t or ""):
        norm = "".join(tokeny(m.group(0)))
        if norm:
            out.append((norm, m.start(), m.end()))
    return out


def pokrycie_ngramow(zgl: str, dok: str, n: int = 8) -> tuple[float, list[str]]:
    """Udział n-gramów słów zgłoszenia obecnych dosłownie w dokumencie + scalone fragmenty (oryginalna pisownia)."""
    sz = _slowa(zgl)
    if len(sz) < n:
        return 0.0, []
    sd = [s for s, _, _ in _slowa(dok)]
    w_dok = {tuple(sd[i:i + n]) for i in range(len(sd) - n + 1)}
    wszystkie = len(sz) - n + 1
    trafione = [i for i in range(wszystkie) if tuple(s for s, _, _ in sz[i:i + n]) in w_dok]
    if not trafione:
        return 0.0, []
    zaznaczone = sorted({j for i in trafione for j in range(i, i + n)})
    fragmenty, start, prev = [], zaznaczone[0], zaznaczone[0]
    for j in zaznaczone[1:] + [None]:
        if j is not None and j == prev + 1:
            prev = j
            continue
        fragmenty.append(zgl[sz[start][1]:sz[prev][2]])
        if j is not None:
            start = prev = j
    return len(trafione) / wszystkie, fragmenty
