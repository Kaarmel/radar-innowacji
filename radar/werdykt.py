"""Werdykt, komórka organizacji, ścieżka dalej i partnerzy: same reguły, każda rekomendacja z nazwą reguły."""
from . import instytucje
from .model import Dokument, Rekomendacja, WynikFiltra, Zgloszenie

DOMYSLNE = {
    "R1": "Akceleracja i prototypowanie",
    "R2": "Ochrona: rozważ zgłoszenie patentowe (UPRP) lub licencję",
    "R3": "Transfer do instytucji tego samego typu",
    "R4": "Finansowanie: programy podobnych projektów",
    "R5": "Współpraca zamiast dublowania: skontaktuj się z autorem podobnego projektu",
}


def werdykt(wyniki: list[WynikFiltra]) -> str:
    pasma = {w.pasmo for w in wyniki}
    return "odrzucone_do_przegladu" if "czerwone" in pasma else "do_przegladu" if "zolte" in pasma else "dalej"


def komorka(z: Zgloszenie, profil: dict) -> str:
    for k in profil.get("komorki", []):
        if all(getattr(z, pole, None) in wartosci for pole, wartosci in k.get("gdy", {}).items()):
            return k["id"]
    return profil.get("komorka_domyslna", "ogolne")


def _w(wyniki: list[WynikFiltra], filtr: str) -> WynikFiltra | None:
    return next((w for w in wyniki if w.filtr == filtr), None)


def sciezka(z: Zgloszenie, wyniki: list[WynikFiltra], podobne: list[Dokument], profil: dict) -> list[Rekomendacja]:
    nazwa = lambda r: profil.get("sciezki", {}).get(r) or DOMYSLNE[r]
    if werdykt(wyniki) == "odrzucone_do_przegladu":
        powody = [f"{w.filtr}: {w.procent:.0f}%" if w.procent is not None else w.filtr for w in wyniki if w.pasmo == "czerwone"]
        return [Rekomendacja("Do przeglądu analityka: powody odrzucenia z linkami do dowodów",
                             "Czerwone filtry: " + ", ".join(powody) + ". Decyzję podejmuje człowiek.", ["ODRZUCENIE"])]
    nowosc, patent, kopia = _w(wyniki, "nowosc"), _w(wyniki, "patent"), _w(wyniki, "kopia")
    czerwone = any(w.pasmo == "czerwone" for w in wyniki)
    out = []
    zolte = [w for w in wyniki if w.pasmo == "zolte"]
    if zolte:
        nazwy = {"plagiat": "plagiat", "kopia": "kopia", "patent": "patent", "nowosc": "nowość"}
        opis = ", ".join(f"{nazwy[w.filtr]} {w.procent:.0f}%" if w.procent is not None else nazwy[w.filtr] for w in zolte)
        out.append(Rekomendacja("Do przeglądu analityka: sprawdź żółte filtry",
                                f"Żółte: {opis}. Dowody i uzasadnienia są niżej na karcie.", ["PRZEGLAD"]))
    if z.typ_innowacji == "techniczna" and z.etap in {"prototyp", "wdrozone"} and nowosc and nowosc.pasmo == "zielone":
        out.append(Rekomendacja(nazwa("R1"), "Rozwiązanie techniczne na etapie prototypu lub wdrożenia, nowość wysoka.", ["R1"]))
    if nowosc and (nowosc.procent or 0) >= 80 and patent and (patent.pasmo == "zielone" or patent.wlasna_praca):
        out.append(Rekomendacja(nazwa("R2"), "Nowość ≥ 80% i brak kolidującego cudzego patentu"
                                + (" (podobne patenty to własna praca)." if patent.wlasna_praca else "."), ["R2"]))
    if z.typ_innowacji in {"organizacyjna", "edukacyjna", "spoleczna", "procesowa"} and not czerwone:
        out.append(Rekomendacja(nazwa("R3"), f"Innowacja {z.typ_innowacji}: da się ją przenieść bez nowej technologii.", ["R3"]))
    finansowane = [d for d in podobne if d.zrodlo in {"mapadotacji", "interreg"}][:3]
    if finansowane:
        lista = "; ".join(f"{d.tytul} ({d.link})" for d in finansowane)
        out.append(Rekomendacja(nazwa("R4"), f"Podobne projekty sfinansowane ze środków publicznych: {lista}", ["R4"]))
    if kopia and kopia.pasmo == "zolte" and not kopia.wlasna_praca:
        out.append(Rekomendacja(nazwa("R5"), "Istnieje podobne rozwiązanie innej instytucji (kopia: żółte).", ["R5"]))
    return out


LOKALNE = {"mapadotacji", "interreg", "radon", "radon_patenty", "uprp", "www"}


def partnerzy(z: Zgloszenie, podobne: list[Dokument], limit: int = 5) -> list[dict]:
    """Instytucje, które już działają w temacie (z najbardziej podobnych dokumentów), bez własnej instytucji.
    Najpierw polskie i regionalne źródła (realny kontakt), potem zagraniczne patenty i publikacje."""
    out, widziane = [], set()
    for d in sorted(podobne, key=lambda d: d.zrodlo not in LOKALNE):
        for nazwa in d.instytucje:
            klucz = frozenset(instytucje.normalizuj(nazwa))
            if not klucz or klucz in widziane or instytucje.ta_sama(z.instytucja, [nazwa]):
                continue
            widziane.add(klucz)
            out.append({"nazwa": nazwa, "dokument": d.tytul, "link": d.link, "zrodlo": d.zrodlo})
            break
        if len(out) >= limit:
            break
    return out
