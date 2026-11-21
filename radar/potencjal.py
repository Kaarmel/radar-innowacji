"""Ocena potencjału 0–100 według jawnego wzoru. Kryteria i wagi są w profilu organizacji (JSON).
Każde kryterium podaje punkty, źródło (kod / AI / formularz), uzasadnienie i dowody. AI nie wystawia liczby:
jej odpowiedzi „tak/nie” z rubryki nowości są tylko wejściem do wzoru.

wynik = 100 × Σ punkty / Σ maksimum, liczone po kryteriach, dla których są dane."""
from . import config, instytucje
from .model import Dokument, WynikFiltra, Zgloszenie
from .tekst import bez_diakrytykow, tokeny

NAZWY = {
    "nowosc": "Nowość wobec znalezionych dokumentów",
    "dojrzalosc": "Dojrzałość (etap)",
    "przewaga": "Mierzalna przewaga",
    "zapotrzebowanie": "Zapotrzebowanie i transfer: inne instytucje z podobnym problemem",
    "ochrona": "Możliwość ochrony (brak kolidującego patentu)",
    "finansowanie": "Precedens finansowania podobnych projektów",
    "specjalizacje": "Zgodność ze specjalizacjami organizacji",
}
DOJRZALOSC = {"pomysl": 0.25, "prototyp": 0.6, "wdrozone": 1.0, "zakonczone": 0.8}
FINANSOWANE = {"mapadotacji", "interreg"}
PROG_PODOBNY = 0.15


def _rubryka(wyniki: list[WynikFiltra]) -> dict[str, dict]:
    w = next((x for x in wyniki if x.filtr == "nowosc"), None)
    if not w or w.pasmo == "brak_danych":
        return {}
    return {o["pytanie"]: o for o in w.dowody if o.get("pytanie")}


def _nowosc(z, wyniki, ranking, profil):
    r = _rubryka(wyniki)
    if not r:
        return None, "AI nie oceniło nowości (brak danych).", [], "AI"
    pyt = ["Q1", "Q2", "Q3", "Q5"]
    tak = [q for q in pyt if r.get(q, {}).get("odpowiedz") == "tak"]
    dowody = [{"pytanie": q, "odpowiedz": r.get(q, {}).get("odpowiedz"), "link": r.get(q, {}).get("link"),
               "tytul": r.get(q, {}).get("tytul")} for q in pyt]
    return len(tak) / 4, f"{len(tak)} z 4 pytań rubryki nowości z odpowiedzią „tak” (Q1–Q3, Q5).", dowody, "AI"


def _przewaga(z, wyniki, ranking, profil):
    r = _rubryka(wyniki)
    if "Q4" not in r:
        return None, "Brak odpowiedzi na Q4 (brak danych).", [], "AI"
    odp = r["Q4"]["odpowiedz"]
    return (1.0 if odp == "tak" else 0.0), f"Q4 (mierzalna przewaga: koszt, czas, skala): {odp.replace('_', ' ')}. {r['Q4'].get('uzasadnienie', '')}", [], "AI"


def _dojrzalosc(z, wyniki, ranking, profil):
    u = DOJRZALOSC.get(z.etap)
    if u is None:
        return None, "Nie podano etapu.", [], "formularz"
    return u, f"Etap „{z.etap}” = {int(u * 100)}% punktów (pomysł 25, prototyp 60, zakończone 80, wdrożone 100).", [], "formularz"


def _zapotrzebowanie(z, wyniki, ranking, profil):
    prog_kopii = config.PROGI["kopia"]["czerwone"]
    dowody, widziane = [], set()
    lokalne = {"mapadotacji", "interreg", "radon", "radon_patenty", "www"}
    for s, d in sorted(ranking, key=lambda x: x[1].zrodlo not in lokalne):  # najpierw polskie instytucje (realny transfer)
        if not (PROG_PODOBNY <= s < prog_kopii) or d.zrodlo == "zgloszenie":
            continue
        for nazwa in d.instytucje[:1]:
            klucz = instytucje.normalizuj(nazwa)
            if not klucz or klucz in widziane or instytucje.ta_sama(z.instytucja, [nazwa]):
                continue
            widziane.add(klucz)
            dowody.append({"instytucja": nazwa, "tytul": d.tytul, "link": d.link, "zrodlo": d.zrodlo,
                           "podobienstwo": round(s * 100, 1)})
    n = len(dowody)
    return min(n, 5) / 5, (f"{_instytucje(n)} podobne (ale nie skopiowane) projekty: jest problem do rozwiązania "
                           f"i odbiorcy transferu. Pełne punkty od 5." if n else "Nie znaleziono innych instytucji z podobnym problemem."), dowody[:5], "kod"


def _ochrona(z, wyniki, ranking, profil):
    w = next((x for x in wyniki if x.filtr == "patent"), None)
    if not w or w.pasmo == "brak_danych":
        return None, "Źródła patentowe niedostępne (brak danych).", [], "kod"
    if w.wlasna_praca and w.pasmo != "czerwone":
        return 1.0, "Podobne patenty należą do tej samej instytucji: kontynuacja, możliwa ochrona lub licencja.", [], "kod"
    u = {"zielone": 1.0, "zolte": 0.5, "czerwone": 0.0}[w.pasmo]
    return u, f"Filtr patentowy: {w.pasmo} (najbliższy patent {w.procent or 0:.0f}% podobieństwa).", [], "kod"


def _instytucje(n: int) -> str:
    if n == 1:
        return "1 inna instytucja ma"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} inne instytucje mają"
    return f"{n} innych instytucji ma"


def _finansowanie(z, wyniki, ranking, profil):
    dowody = [{"tytul": d.tytul, "link": d.link, "zrodlo": d.zrodlo, "podobienstwo": round(s * 100, 1)}
              for s, d in ranking if d.zrodlo in FINANSOWANE and PROG_PODOBNY <= s < config.PROGI["kopia"]["czerwone"]][:3]
    n = len(dowody)
    return min(n, 2) / 2, (f"{n} podobnych projektów dostało dofinansowanie publiczne: są programy, które to finansują."
                           if n else "Brak podobnych projektów sfinansowanych w bazie (Mapa Dotacji, Interreg)."), dowody, "kod"


def _specjalizacje(z, wyniki, ranking, profil):
    spec = (profil.get("potencjal") or {}).get("specjalizacje") or {}
    slowa = set(tokeny(bez_diakrytykow(f"{z.tytul} {z.opis} {z.opis_en or ''}")))
    trafione = {nazwa: sorted({w for w in slowa for p in prefiksy if w.startswith(p)})[:5] for nazwa, prefiksy in spec.items()}
    trafione = {k: v for k, v in trafione.items() if v}
    if not trafione:
        return 0.0, "Nie pasuje do specjalizacji: " + ", ".join(spec) + ".", [], "kod"
    return 1.0, "Pasuje do: " + "; ".join(f"{k} ({', '.join(v)})" for k, v in trafione.items()) + ".", [], "kod"


KRYTERIA = {"nowosc": _nowosc, "dojrzalosc": _dojrzalosc, "przewaga": _przewaga, "zapotrzebowanie": _zapotrzebowanie,
            "ochrona": _ochrona, "finansowanie": _finansowanie, "specjalizacje": _specjalizacje}


def ocen(z: Zgloszenie, wyniki: list[WynikFiltra], ranking: list[tuple[float, Dokument]], profil: dict) -> dict:
    wagi = (profil.get("potencjal") or {}).get("wagi") or {}
    kryteria = []
    for kid, waga in wagi.items():
        if kid not in KRYTERIA or not waga:
            continue
        udzial, uzas, dowody, zrodlo = KRYTERIA[kid](z, wyniki, ranking, profil)
        kryteria.append({"id": kid, "nazwa": NAZWY[kid], "max": waga, "zrodlo": zrodlo, "uzasadnienie": uzas, "dowody": dowody,
                         "punkty": None if udzial is None else round(waga * udzial, 2)})
    dostepne = [k for k in kryteria if k["punkty"] is not None]
    suma_max = sum(k["max"] for k in dostepne)
    wynik = round(100 * sum(k["punkty"] for k in dostepne) / suma_max) if suma_max else None
    brak = [k["nazwa"] for k in kryteria if k["punkty"] is None]
    return {"wynik": wynik, "kryteria": kryteria, "suma_max": suma_max,
            "uwaga": ("Brak danych dla: " + ", ".join(brak) + "; wynik liczony z pozostałych kryteriów.") if brak else "",
            "formula": "100 × suma punktów / suma maksimów kryteriów z danymi; wagi z profilu organizacji"}
