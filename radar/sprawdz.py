"""Sprawdzenie jednego zgłoszenia: wyszukiwanie w bazie i źródłach na żądanie, cztery filtry, werdykt, karta."""
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, wait

from . import ai, config, db, filtry, instytucje, organizacje, potencjal, slowniki, tekst, termin, werdykt
from .model import Dokument, WynikFiltra, Zgloszenie
from .zrodla import BrakDostepu, crossref, epo, mapadotacji, openalex

ZRODLA_NA_ZADANIE = {"epo": epo.szukaj, "openalex": openalex.szukaj, "crossref": crossref.szukaj}
ZRODLA_PATENTOWE = {"epo"}
MAX_BENEFICJENTOW = 5  # strona projektu Mapy Dotacji ładuje się kilka sekund
TEMAT_MAX = 30  # tyle najbliższych dokumentów AI sprawdza pod kątem tematu (partnerzy, zapotrzebowanie, finansowanie)


def _poprzednie_zgloszenia(con: sqlite3.Connection, zgl_id: int, limit: int = 2000) -> list[Dokument]:
    wiersze = con.execute("SELECT id, tytul, opis, instytucja, utworzono_at FROM zgloszenie WHERE id < ? ORDER BY id DESC LIMIT ?",
                          (zgl_id, limit))
    return [Dokument(id=f"zgloszenie:{r['id']}", zrodlo="zgloszenie", typ="zgloszenie", tytul=r["tytul"] or "", opis=r["opis"] or "",
                     link=f"/karta/{r['id']}", rok=time.localtime(r["utworzono_at"] or 0).tm_year,
                     instytucje=[r["instytucja"]] if r["instytucja"] else []) for r in wiersze]


def _na_zadanie(terminy_en: list[str]) -> tuple[list[Dokument], list[str], list[str]]:
    """Źródła zewnętrzne równolegle; niedostępne nie przerywają sprawdzenia."""
    if not ZRODLA_NA_ZADANIE:
        return [], [], []
    if not terminy_en:
        return [], [], list(ZRODLA_NA_ZADANIE)
    docs, ok, nie = [], [], []
    limit = max(0.0, min(40.0, termin.zostalo() - 60))  # zostaw minutę na filtry i AI
    pula = ThreadPoolExecutor(max_workers=len(ZRODLA_NA_ZADANIE))
    zadania = {n: pula.submit(f, terminy_en) for n, f in ZRODLA_NA_ZADANIE.items()}
    wait(zadania.values(), timeout=limit)
    for nazwa, zad in zadania.items():
        if not zad.done():
            nie.append(nazwa)
            termin.notuj(f"źródło {nazwa} (nie odpowiedziało w {limit:.0f} s)")
            continue
        try:
            docs += zad.result()
            ok.append(nazwa)
        except BrakDostepu:
            nie.append(nazwa)
        except Exception:  # nieprzewidziany błąd źródła = źródło niedostępne, nie awaria sprawdzenia
            nie.append(nazwa)
    pula.shutdown(wait=False, cancel_futures=True)  # wolne źródło kończy się w tle, karta nie czeka
    return docs, ok, nie


def _lokalne(con: sqlite3.Connection, z: Zgloszenie, terminy_en: list[str], df, N) -> list[Dokument]:
    terminy = tekst.terminy(f"{z.tytul}. {z.opis}", n=15, df=df, N=N)
    wyniki = db.szukaj(con, terminy, limit=50) + db.szukaj(con, terminy, limit=20, typ="patent")
    if terminy_en:
        wyniki += db.szukaj(con, terminy_en, limit=20)
    return list({d.id: d for d, _ in wyniki}.values())


def _uzupelnij_beneficjentow(con: sqlite3.Connection, z: Zgloszenie, ranking: list[tuple[float, Dokument]]) -> None:
    """Mapa Dotacji podaje beneficjenta tylko na stronie projektu: pobieramy go dla kilku najbliższych (reguła własnej pracy)."""
    bez = [(s, d) for s, d in ranking if d.zrodlo == "mapadotacji" and not d.instytucje]
    trafienia = [d for s, d in bez if tekst.pokrycie_ngramow(z.opis, f"{d.tytul}. {d.opis}")[0] > 0]
    prog = config.PROGI["kopia"]["zolte"]  # poniżej progu kopii instytucja nie zmienia wyniku filtrów
    brakujace = trafienia + [d for s, d in bez if s >= prog and d not in trafienia][:3]
    do_pobrania = brakujace[:MAX_BENEFICJENTOW]
    if not do_pobrania:
        return
    budzet = max(0.0, min(30.0, termin.zostalo() - 75))  # reszta na filtry z AI
    pula = ThreadPoolExecutor(max_workers=1)  # kolejno: 1 zapytanie na sekundę do jednego hosta
    zadania = [(d, pula.submit(mapadotacji.beneficjent, d.link)) for d in do_pobrania]
    wait([z for _, z in zadania], timeout=budzet)
    pula.shutdown(wait=False, cancel_futures=True)
    zmienione = []
    for d, zad in zadania:
        if not zad.done() or zad.cancelled():
            termin.notuj(f"beneficjenci Mapy Dotacji (strona nie odpowiedziała w {budzet:.0f} s)")
            continue
        try:
            nazwa = zad.result()
        except Exception:
            nazwa = None
        if nazwa:
            d.instytucje = [nazwa]
            zmienione.append(d)
    if zmienione and con is not None:
        db.zapisz_dokumenty(con, zmienione)


def _tematyczne(z: Zgloszenie, ranking: list[tuple[float, Dokument]], koszt: list[float]) -> tuple[list[tuple[float, Dokument]], dict]:
    """Zapotrzebowanie, finansowanie (R4) i partnerzy mają sens tylko dla dokumentów o tym samym problemie. Podobieństwo słów
    myli przedmiot (np. bezdomne zwierzęta i bezdomność ludzi), więc AI potwierdza temat najbliższych dokumentów, tak jak
    przy kopii. Bez odpowiedzi AI ranking zostaje bez zmian, a pokrycie karty to zapisuje."""
    wlasny = lambda d: instytucje.ta_sama(z.instytucja, d.instytucje)
    do_ai = [d for i, (s, d) in enumerate(ranking)
             if ((i < 20 and s > 0) or s >= potencjal.PROG_PODOBNY) and not wlasny(d)][:TEMAT_MAX]
    if not do_ai:
        return ranking, {"sprawdzono": False, "odrzucone": []}
    oceny, k = ai.ten_sam_problem(z.opis, do_ai)
    koszt.append(k)
    if not oceny:
        return ranking, {"sprawdzono": False, "odrzucone": []}
    wyslane = {d.id for d in do_ai}
    odrzucone = [d for d in do_ai if not oceny.get(d.id, {"ten_sam": True})["ten_sam"]]
    usun = {d.id for d in odrzucone} | {d.id for s, d in ranking if d.id not in wyslane and not wlasny(d)}
    return [(s, d) for s, d in ranking if d.id not in usun], {
        "sprawdzono": True, "sprawdzonych": len(do_ai),
        "odrzucone": [{"tytul": d.tytul, "link": d.link, "zrodlo": d.zrodlo, "uzasadnienie": oceny[d.id]["uzasadnienie"]}
                      for d in odrzucone]}


def _podobne(ranking: list[tuple[float, Dokument]], czolowka: int = 20, prog_finansowane: float = 0.15) -> list[Dokument]:
    """Czołówka rankingu + do 3 projektów sfinansowanych spoza niej (żeby ścieżka R4 nie ginęła pod patentami EPO)."""
    podobne = [d for s, d in ranking[:czolowka] if s > 0]
    finansowane = [d for s, d in ranking[czolowka:] if d.zrodlo in {"mapadotacji", "interreg"} and s >= prog_finansowane]
    return podobne + finansowane[:3]


def sprawdz(con: sqlite3.Connection, zgl_id: int) -> dict:
    t0 = time.time()
    z = db.zgloszenie(con, zgl_id)
    if z is None:
        raise KeyError(f"brak zgłoszenia {zgl_id}")
    db.ustaw_status(con, zgl_id, "w_toku")
    koszt: list[float] = []
    termin.ustaw(config.LIMIT_SPRAWDZENIA_S)
    ai.zacznij_rejestr()
    try:
        tl, k = ai.tlumacz_zapytanie(z.opis)
        koszt.append(k)
        z.opis_en = tl.get("opis_en") or z.opis_en
        db.zapisz_zgloszenie(con, z)
        terminy_en = tl.get("terminy_en") or []

        df, N = db.funkcja_df(con)
        lokalne = _lokalne(con, z, terminy_en, df, N)
        zewnetrzne, ok, niedostepne = _na_zadanie(terminy_en)
        if zewnetrzne:
            db.zapisz_dokumenty(con, zewnetrzne)  # pamięć podręczna: dowody i radar zostają w bazie
        # ocena projektu z bazy: dokument źródłowy to ten sam projekt, nie dowód przeciwko niemu
        kandydaci = [d for d in {d.id: d for d in lokalne + zewnetrzne}.values() if d.id != z.zrodlo_dok]
        poprzednie = _poprzednie_zgloszenia(con, zgl_id)

        ranking = filtry.ranking(z, kandydaci, df, N)
        _uzupelnij_beneficjentow(con, z, ranking)
        obce = [(s, d) for s, d in ranking if not instytucje.ta_sama(z.instytucja, d.instytucje)]

        patenty_dostepne = any(n in ok for n in ZRODLA_PATENTOWE)
        wyniki = [
            filtry.plagiat(z, kandydaci + poprzednie),
            filtry.kopia(z, kandydaci + poprzednie, df, N, koszt=koszt),
            filtry.patent(z, kandydaci, df, N, dostepne=patenty_dostepne, koszt=koszt),
            filtry.nowosc(z, [d for s, d in obce[:10] if s > 0], koszt=koszt),
        ]
        profil = organizacje.wczytaj(z.organizacja)
        ranking_tem, tematy = _tematyczne(z, ranking, koszt)
        db.zapisz_ocene(con, zgl_id, potencjal.ocen(z, wyniki, ranking_tem, profil))
        podobne = _podobne(ranking_tem)
        lokalne_liczby = db.liczba_dokumentow(con)
        pokrycie = {"zrodla": sorted(set(lokalne_liczby) - {"zgloszenie"} | set(ok)),
                    "lokalne": lokalne_liczby, "dokumentow": sum(lokalne_liczby.values()),
                    "kandydatow": len(kandydaci), "zgloszen_porownanych": len(poprzednie), "niedostepne": niedostepne,
                    "stan_danych": {k: slowniki.czas_pl(slowniki.stan_na(k, v), "%Y-%m-%d")
                                    for k, v in db.stan_zrodel(con).items() if v["pobrano_do"] and k in slowniki.HARMONOGRAM
                                    and slowniki.HARMONOGRAM[k]["tryb"] != "na żywo"},
                    "na_zywo": slowniki.czas_pl(time.time()), "limit_czasu": termin.przekroczenia(),
                    "ai": ai.rejestr(), "tematy": tematy}
        db.zapisz_wyniki(con, zgl_id, wyniki, werdykt.werdykt(wyniki), werdykt.komorka(z, profil),
                         werdykt.sciezka(z, wyniki, podobne, profil), werdykt.partnerzy(z, podobne),
                         round(time.time() - t0, 1), round(sum(koszt), 5), pokrycie=pokrycie)
    except Exception:
        db.ustaw_status(con, zgl_id, "blad")
        raise
    finally:
        termin.ustaw(None)
    return db.karta(con, zgl_id)


def przelicz_podobne(con: sqlite3.Connection, zgl_id: int, zapisz: bool = True) -> dict:
    """Ponownie liczy tylko to, co zależy od podobnych projektów (zapotrzebowanie, finansowanie, ścieżka R4, partnerzy),
    z potwierdzeniem tematu przez AI. Wyniki czterech filtrów, werdykt, komórka i czas sprawdzenia zostają bez zmian."""
    z, k = db.zgloszenie(con, zgl_id), db.karta(con, zgl_id)
    if z is None or not k or k["status"] != "gotowe":
        raise KeyError(f"brak gotowej karty {zgl_id}")
    wyniki = [WynikFiltra(w["filtr"], w["procent"], w["pasmo"], w["dowody"], w["uwaga"] or "", w["wlasna_praca"])
              for w in k["wyniki"]]
    koszt: list[float] = []
    termin.ustaw(config.LIMIT_SPRAWDZENIA_S)
    try:
        df, N = db.funkcja_df(con)
        terminy_en = tekst.terminy(z.opis_en, n=10, df=df, N=N) if z.opis_en else []
        kandydaci = [d for d in _lokalne(con, z, terminy_en, df, N) if d.id != z.zrodlo_dok]
        ranking_tem, tematy = _tematyczne(z, filtry.ranking(z, kandydaci, df, N), koszt)
        profil = organizacje.wczytaj(z.organizacja)
        ocena = potencjal.ocen(z, wyniki, ranking_tem, profil)
        podobne = _podobne(ranking_tem)
        rekomendacje, partnerzy = werdykt.sciezka(z, wyniki, podobne, profil), werdykt.partnerzy(z, podobne)
    finally:
        termin.ustaw(None)
    if zapisz:
        pokrycie = {**k["pokrycie"], "tematy": tematy, "przeliczono_podobne": slowniki.czas_pl(time.time())}
        db.zapisz_ocene(con, zgl_id, ocena)
        db.zapisz_wyniki(con, zgl_id, wyniki, k["werdykt"], k["komorka"], rekomendacje, partnerzy, k["czas_s"],
                         round((k["koszt_usd"] or 0) + sum(koszt), 5), pokrycie=pokrycie)
    return {"wynik": ocena["wynik"], "rekomendacje": rekomendacje, "partnerzy": partnerzy, "tematy": tematy, "ocena": ocena}
