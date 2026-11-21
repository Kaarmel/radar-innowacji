"""Biuletyn Urzędu Patentowego (UPRP): zgłoszenia wynalazków (A1) i wzorów użytkowych (U1) z ostatnich numerów.
PDF numeru → pdftotext -layout → lewa, potem prawa kolumna każdej strony → rekordy (21), (22), (54), (57), (71).
Bez twórców (72) i bez zgłaszających osób fizycznych: zostają uczelnie, instytuty i spółki kapitałowe."""
import re
import sqlite3
import subprocess
from collections import Counter
from urllib.parse import urljoin

from .. import config, db, siec
from ..model import Dokument

LISTA = "https://uprp.gov.pl/pl/publikacje/biuletyn-i-wiadomosci-uprp"
NAGLOWEK = re.compile(r"^(A1|U1)\s+\(21\)\s+(\d+)\s+\(22\)\s+(\d{4})\s+\d\d\s+\d\d")
POLE = re.compile(r"^\((\d\d)\)\s*(.*)")
KONIEC = re.compile(r"\(\d+\s+zastrze")
STOPKA = re.compile(r"BIULETYN URZĘDU PATENTOWEGO")
ORGANIZACJA = re.compile(r"UNIWERSYTET|POLITECHNIK|AKADEMI|INSTYTUT|SIEĆ BADAWCZA|CENTRUM|SPÓŁKA|SP\. Z O\. ?O|S\.A\.|SPÓŁDZIELNIA|"
                         r"FUNDACJA|STOWARZYSZENIE|SZPITAL|GMINA|POWIAT|URZĄD|AGENCJA|PAŃSTWOW|UNIVERSIT|INSTITUT|GMBH|"
                         r"\bAG\b|\bLTD\b|LIMITED|\bINC\b|CORPORATION|\bLLC\b|B\.V\.|S\.R\.L|S\.P\.A")
OSOBOWA = re.compile(r"JAWNA|CYWILNA|KOMANDYTOWA|SP\. ?J\.|\bS\.C\.|SP\. ?K\.")  # nazwy spółek osobowych zawierają nazwiska
NUMER = re.compile(r'href="([^"]*/bup(\d{1,2})_(\d{4})(?:_\d+)?\.pdf)"', re.I)


def _kolumna(strona: list[str]) -> int | None:
    """Początek prawej kolumny: najczęstsza pozycja tekstu po przerwie co najmniej 2 spacji, w środku strony."""
    poz = Counter()
    for linia in strona:
        c = next((m.end() - 1 for m in re.finditer(r" {2,}\S", linia) if 45 <= m.end() - 1 <= 100), None)
        if c is not None:
            poz[c] += 1
    return poz.most_common(1)[0][0] if poz else None


def _podziel(linia: str, kol: int | None) -> tuple[str, str]:
    if kol is None or len(linia) <= kol:
        return linia, ""
    kand = [m.end() - 1 for m in re.finditer(r" {2,}\S", linia) if m.end() - 1 >= kol - 6]
    if not kand:
        return linia, ""
    c = min(kand, key=lambda x: abs(x - kol))
    return linia[:c], linia[c:]


def kolumny(tekst: str) -> list[str]:
    linie = []
    for strona in tekst.split("\f"):
        wiersze = [w.replace("\t", " ") for w in strona.split("\n") if not STOPKA.search(w)]
        kol = _kolumna(wiersze)
        pary = [_podziel(w, kol) for w in wiersze]
        linie += [l.strip() for l, _ in pary] + [p.strip() for _, p in pary]
    return linie


def _zlacz(linie: list[str]) -> str:
    tekst = ""
    for l in linie:
        if not l:
            continue
        if tekst.endswith("-") and l[:1].islower():
            tekst = tekst[:-1] + l
        else:
            tekst = f"{tekst} {l}".strip()
    return tekst


def _instytucje(pole71: str) -> list[str]:
    out = []
    for wpis in pole71.split(";"):
        czesci = [c.strip() for c in wpis.split(",")]
        if len(czesci) > 2 and re.fullmatch(r"[A-Z]{2}", czesci[-1]):  # zagraniczny: „nazwa, miasto, kraj”
            czesci = czesci[:-1]
        nazwa = ", ".join(czesci[:-1] if len(czesci) > 1 else czesci)
        if nazwa and ORGANIZACJA.search(nazwa.upper()) and not OSOBOWA.search(nazwa.upper()):
            out.append(nazwa)
    return list(dict.fromkeys(out))


def parsuj_tekst(tekst: str, link: str, numer: str) -> list[Dokument]:
    rekordy, rek = [], None
    for l in kolumny(tekst):
        m = NAGLOWEK.match(l)
        if m:
            rek = {"rodzaj": m.group(1), "nr": m.group(2), "rok": int(m.group(3)), "pola": {}, "pole": None, "koniec": False}
            rekordy.append(rek)
            continue
        if not rek or rek["koniec"] or not l:
            continue
        k = KONIEC.search(l)
        if k:
            l, rek["koniec"] = l[: k.start()].strip(), True
        p = POLE.match(l)
        if p:
            rek["pole"] = p.group(1)
            rek["pola"][rek["pole"]] = [p.group(2)]
        elif rek["pole"] and l:
            rek["pola"][rek["pole"]].append(l)
    out = []
    for r in rekordy:
        tytul, streszczenie = _zlacz(r["pola"].get("54", [])), _zlacz(r["pola"].get("57", []))
        if not tytul:
            continue
        wynalazek = r["rodzaj"] == "A1"
        opis = (f"Zgłoszenie {'wynalazku' if wynalazek else 'wzoru użytkowego'} {'P' if wynalazek else 'W'}.{r['nr']}"
                f" (BUP {numer}). {streszczenie}").strip()
        out.append(Dokument(id=f"uprp:{r['nr']}", zrodlo="uprp", typ="patent", tytul=tytul[:300], opis=opis, link=link,
                            rok=r["rok"], instytucje=_instytucje(_zlacz(r["pola"].get("71", []))), status="zgloszenie",
                            jezyk="pl"))
    return out


def linki_numerow(html: str, ile: int = 52) -> list[tuple[str, str]]:
    numery = {}
    for href, nr, rok in NUMER.findall(html):
        numery.setdefault((int(rok), int(nr)), urljoin("https://uprp.gov.pl", href))
    return [(f"{nr}/{rok}", url) for (rok, nr), url in sorted(numery.items())[-ile:]]


def pobierz_wszystko(con: sqlite3.Connection, ile: int = 52, katalog=None, log=print) -> int:
    katalog = katalog or config.DANE / "bup"
    katalog.mkdir(parents=True, exist_ok=True)
    r = siec.pobierz(LISTA, timeout=120)
    if r.status_code != 200:
        log(f"uprp: lista numerów HTTP {r.status_code}, przerywam")
        return 0
    razem = 0
    for numer, url in linki_numerow(r.text, ile):
        plik = katalog / url.rsplit("/", 1)[1]
        if not plik.exists() or plik.stat().st_size == 0:
            p = siec.pobierz(url, timeout=300)
            if p.status_code != 200 or not p.content.startswith(b"%PDF"):
                log(f"uprp: {numer} HTTP {p.status_code}, pomijam")
                continue
            plik.write_bytes(p.content)
        tekst = subprocess.run(["pdftotext", "-layout", str(plik), "-"], capture_output=True, text=True, timeout=300).stdout
        n = db.zapisz_dokumenty(con, parsuj_tekst(tekst, url, numer))
        log(f"uprp: BUP {numer}: {n} zgłoszeń")
        razem += n
    return razem
