"""Walidacja: zestaw przypadków ze znaną prawdą (plagiat, parafraza, patent, własna praca, duplikat) i projekty z bazy
do ręcznej etykiety „rutyna / nowość”. Raport: czułość każdego filtra, zgodność oceny z człowiekiem, czas, koszt."""
import csv
import json
import random
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from . import ai, config, db
from .model import Zgloszenie
from .sprawdz import sprawdz

KATALOG = config.KORZEN / "walidacja"
ETYKIETY = KATALOG / "etykiety.csv"
KONTROLNE = KATALOG / "kontrolne.csv"  # zestaw kontrolny: projekty, których nie widziała żadna poprawka rubryki
RAPORT_MD = KATALOG / "raport.md"
RAPORT_JSON = config.DANE / "zestaw_raport.json"
OPISY = {
    "plagiat": "Plagiat: połowa zdań z projektu A + połowa z projektu B (inne instytucje); oczekiwane: plagiat czerwone",
    "parafraza": "Kopia: projekt przepisany innymi słowami przez AI; oczekiwane: kopia żółta lub czerwona",
    "patent": "Patent: opis patentu polskiej uczelni przepisany innymi słowami; oczekiwane: patent żółty lub czerwony",
    "wlasna": "Własna praca: tekst projektu zgłoszony przez tę samą instytucję; oczekiwane: bez czerwonego plagiatu, oznaczone jako kontynuacja",
    "duplikat": "Duplikat: to samo zgłoszenie wysłane drugi raz; oczekiwane: plagiat czerwony z uwagą „duplikat zgłoszenia”",
}


def _w(k: dict, filtr: str) -> dict:
    return next((w for w in k["wyniki"] if w["filtr"] == filtr), {})


def trafione(rodzaj: str, k: dict) -> bool:
    if rodzaj == "plagiat":
        return _w(k, "plagiat").get("pasmo") == "czerwone"
    if rodzaj == "parafraza":
        return _w(k, "kopia").get("pasmo") in ("zolte", "czerwone")
    if rodzaj == "patent":
        return _w(k, "patent").get("pasmo") in ("zolte", "czerwone")
    if rodzaj == "wlasna":
        p = _w(k, "plagiat")
        return p.get("pasmo") != "czerwone" and bool(p.get("wlasna_praca"))
    if rodzaj == "duplikat":
        p = _w(k, "plagiat")
        return p.get("pasmo") == "czerwone" and p.get("uwaga") == "duplikat zgłoszenia"
    raise ValueError(rodzaj)


def _zgodnosc(wiersze: list[tuple[str, dict]], przedrostek: str, etykiety: dict[str, str]) -> dict | None:
    zgodne, pot, werdykty = [], {"nowosc": [], "rutyna": []}, {"nowosc": {}, "rutyna": {}}
    for r, k in wiersze:
        if not r.startswith(przedrostek + ":") or etykiety.get(r.split(":", 1)[1]) not in ("nowosc", "rutyna"):
            continue
        czlowiek = etykiety[r.split(":", 1)[1]]
        pasmo = _w(k, "nowosc").get("pasmo")
        if pasmo in ("zielone", "zolte", "czerwone"):
            zgodne.append(("nowosc" if pasmo in ("zielone", "zolte") else "rutyna") == czlowiek)
        if (k.get("potencjal") or {}).get("wynik") is not None:
            pot[czlowiek].append(k["potencjal"]["wynik"])
        if k.get("werdykt"):
            werdykty[czlowiek][k["werdykt"]] = werdykty[czlowiek].get(k["werdykt"], 0) + 1
    if not zgodne:
        return None
    pary = [(a > b) + 0.5 * (a == b) for a in pot["nowosc"] for b in pot["rutyna"]]
    return {"n": len(zgodne), "zgodnosc": round(sum(zgodne) / len(zgodne), 2),
            "auc_potencjalu": round(sum(pary) / len(pary), 2) if pary else None,
            "werdykty": {e: w for e, w in werdykty.items() if w},
            "potencjal_nowosc": round(statistics.mean(pot["nowosc"]), 1) if pot["nowosc"] else None,
            "potencjal_rutyna": round(statistics.mean(pot["rutyna"]), 1) if pot["rutyna"] else None}


def miary(wiersze: list[tuple[str, dict]], etykiety: dict[str, str], kontrolne: dict[str, str] | None = None) -> dict:
    out: dict = {}
    for rodzaj in OPISY:
        karty = [k for r, k in wiersze if r == rodzaj]
        if karty:
            t = sum(trafione(rodzaj, k) for k in karty)
            out[rodzaj] = {"trafione": t, "wszystkie": len(karty), "czulosc": round(t / len(karty), 2)}
    for klucz, przedrostek, et in (("etykiety", "etykieta", etykiety), ("kontrolny", "kontrolny", kontrolne or {})):
        z = _zgodnosc(wiersze, przedrostek, et)
        if z:
            out[klucz] = z
    czasy = [k["czas_s"] for _, k in wiersze if k.get("czas_s") is not None]
    koszty = [k.get("koszt_usd") or 0 for _, k in wiersze]
    out["czas_mediana_s"] = round(statistics.median(czasy), 1) if czasy else None
    out["koszt_sredni_usd"] = round(statistics.mean(koszty), 5) if koszty else None
    out["przypadkow"] = len(wiersze)
    return out


# ---------- budowa zestawu ----------
def _zdania(t: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t or "") if len(s.split()) >= 6]


def _dokumenty(con, sql: str, args=()) -> list:
    return [db.dokument(con, r[0]) for r in con.execute(sql, args)]


def _zgl(con, tytul, opis, instytucja, typ_inst="inna_publiczna", zrodlo_dok=None, etap="prototyp") -> int:
    return db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="baza" if zrodlo_dok else "formularz", tytul=tytul[:200],
                                               opis=opis[:8000], link=None, instytucja=instytucja, typ_instytucji=typ_inst,
                                               typ_innowacji="techniczna", etap=etap, wiek_przedzial="mieszany",
                                               organizacja="pci", zrodlo_dok=zrodlo_dok))


def _sprawdz_osobno(zid: int) -> None:
    c = db.polacz()
    try:
        sprawdz(c, zid)
    except Exception as e:
        print(f"zestaw: sprawdzenie {zid} nie powiodło się: {type(e).__name__}", flush=True)
    finally:
        c.close()


def zbuduj(con, n: int = 10, ziarno: int = 7, log=print) -> list[int]:
    with con:
        con.execute("CREATE TABLE IF NOT EXISTS test(zgl_id INTEGER, rodzaj TEXT, filtr TEXT, oczekiwane TEXT)")
    los = random.Random(ziarno)
    pula = _dokumenty(con, """SELECT id FROM dokument WHERE zrodlo='radon' AND jezyk='pl' AND length(opis) BETWEEN 900 AND 4000
                              AND instytucje != '[]' ORDER BY id LIMIT 600""")
    los.shuffle(pula)
    patenty = _dokumenty(con, "SELECT id FROM dokument WHERE zrodlo='radon_patenty' AND length(opis) > 500 ORDER BY id LIMIT 300")
    los.shuffle(patenty)
    wpisy: list[tuple[int, str, str, str]] = []
    # plagiat: pary dokumentów różnych instytucji
    i = 0
    for _ in range(n):
        a, b = pula[i], pula[i + 1]
        i += 2
        za, zb = _zdania(a.opis), _zdania(b.opis)
        if len(za) < 2 or len(zb) < 2 or a.instytucje[0] == b.instytucje[0]:
            continue
        opis = " ".join(za[: max(2, len(za) // 2)] + zb[: max(2, len(zb) // 2)])
        wpisy.append((_zgl(con, f"Test plagiatu: {a.tytul}", opis, f"Zespół testowy P{i}"), "plagiat", "plagiat", "czerwone"))
    # parafraza (AI przepisuje), patent (opis patentu przepisany)
    for _ in range(n):
        a = pula[i]
        i += 1
        tekst, _k = ai.parafrazuj(a.opis[:2000])
        if len(tekst) >= 300:
            wpisy.append((_zgl(con, f"Test kopii: {a.tytul}", tekst, f"Zespół testowy K{i}"), "parafraza", "kopia", "zolte+"))
    for p in patenty[: max(1, n // 2)]:
        tekst, _k = ai.parafrazuj(p.opis[:2000])
        if len(tekst) >= 300:
            wpisy.append((_zgl(con, f"Test patentu: {p.tytul}", tekst, "Zespół testowy patentów", typ_inst="firma"),
                          "patent", "patent", "zolte+"))
    # własna praca: ten sam tekst, ta sama instytucja
    for _ in range(max(1, n // 2)):
        a = pula[i]
        i += 1
        wpisy.append((_zgl(con, f"Test własnej pracy: {a.tytul}", a.opis, a.instytucje[0], typ_inst="uczelnia"),
                      "wlasna", "plagiat", "nie_czerwone"))
    # etykiety ręczne: projekty z bazy oceniane jak przez analityka (dokument źródłowy wykluczony)
    rutyna = _dokumenty(con, """SELECT id FROM dokument WHERE zrodlo='mapadotacji' AND length(opis) > 300 AND
                                (tytul LIKE '%zakup%' OR tytul LIKE '%remont%' OR tytul LIKE '%termomoderniz%' OR tytul LIKE '%szkole%'
                                 OR tytul LIKE '%wyposaż%' OR tytul LIKE '%przebudow%') ORDER BY id LIMIT 200""")
    badawcze = _dokumenty(con, """SELECT id FROM dokument WHERE zrodlo='mapadotacji' AND length(opis) > 300 AND
                                  (opis LIKE '%prac B+R%' OR opis LIKE '%badawczo-rozwojow%' OR tytul LIKE '%innowacyjn%') ORDER BY id LIMIT 200""")
    los.shuffle(rutyna)
    los.shuffle(badawcze)
    etyk = []
    for d in rutyna[: n] + badawcze[: n]:
        zid = _zgl(con, d.tytul, d.opis, (d.instytucje or ["Beneficjent projektu"])[0], typ_inst="firma", zrodlo_dok=d.id,
                   etap="zakonczone")
        wpisy.append((zid, "etykieta", "nowosc", "etykieta"))
        etyk.append({"zgl_id": zid, "etykieta": "", "tytul": d.tytul, "link": d.link})
    with con:
        con.executemany("INSERT INTO test VALUES(?,?,?,?)", wpisy)
    KATALOG.mkdir(exist_ok=True)
    with open(ETYKIETY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["zgl_id", "etykieta", "tytul", "link"])
        w.writeheader()
        w.writerows(etyk)
    log(f"zestaw: {len(wpisy)} przypadków, sprawdzam…")
    with ThreadPoolExecutor(max_workers=4) as pula_w:
        list(pula_w.map(_sprawdz_osobno, [z for z, *_ in wpisy]))
    # duplikaty: drugie zgłoszenie po pierwszym (kolejność ma znaczenie)
    for _ in range(3):
        a = pula[i]
        i += 1
        pierwsze = _zgl(con, f"Test duplikatu: {a.tytul}", a.opis, f"Zespół testowy D{i}")
        _sprawdz_osobno(pierwsze)
        drugie = _zgl(con, f"Test duplikatu: {a.tytul}", a.opis, f"Zespół testowy D{i}")
        _sprawdz_osobno(drugie)
        with con:
            con.execute("INSERT INTO test VALUES(?,?,?,?)", (drugie, "duplikat", "plagiat", "czerwone"))
    return [z for z, *_ in wpisy]


def zbuduj_kontrolny(con, n_losowe: int = 30, n_br: int = 20, ziarno: int = 11, log=print) -> list[int]:
    """Zestaw kontrolny: losowe projekty Mapy Dotacji (n_losowe) + losowe ze słowami B+R / innowacja / technologia (n_br),
    z pominięciem projektów użytych wcześniej. Etykiety nadaje się po budowie (walidacja/kontrolne.csv), rubryki już się nie zmienia."""
    with con:
        con.execute("CREATE TABLE IF NOT EXISTS test(zgl_id INTEGER, rodzaj TEXT, filtr TEXT, oczekiwane TEXT)")
    uzyte = {r[0] for r in con.execute("SELECT z.zrodlo_dok FROM zgloszenie z WHERE z.zrodlo_dok IS NOT NULL")}
    los = random.Random(ziarno)
    wszystkie = [r[0] for r in con.execute("SELECT id FROM dokument WHERE zrodlo='mapadotacji' AND length(opis) > 300 ORDER BY id")]
    br = [r[0] for r in con.execute("""SELECT id FROM dokument WHERE zrodlo='mapadotacji' AND length(opis) > 300 AND
                                       (opis LIKE '%B+R%' OR opis LIKE '%badawczo-rozwojow%' OR tytul LIKE '%innowac%'
                                        OR tytul LIKE '%technologi%' OR tytul LIKE '%wdroż%') ORDER BY id""")]
    los.shuffle(wszystkie)
    los.shuffle(br)
    wybrane: list[tuple[str, str]] = []
    for pula, ile, wybor in ((wszystkie, n_losowe, "losowy"), (br, n_br, "losowy ze słowami B+R, innowacja, technologia")):
        for did in pula:
            if sum(w == wybor for _, w in wybrane) >= ile:
                break
            if did not in uzyte and did not in {d for d, _ in wybrane}:
                wybrane.append((did, wybor))
    wiersze, ids = [], []
    for did, wybor in wybrane:
        d = db.dokument(con, did)
        zid = _zgl(con, d.tytul, d.opis, (d.instytucje or ["Beneficjent projektu"])[0], typ_inst="firma", zrodlo_dok=d.id,
                   etap="zakonczone")
        ids.append(zid)
        wiersze.append({"zgl_id": zid, "etykieta": "", "tytul": d.tytul, "link": d.link, "wybor": wybor, "zrodlo": ""})
    with con:
        con.executemany("INSERT INTO test VALUES(?,?,?,?)", [(z, "kontrolny", "nowosc", "etykieta") for z in ids])
    KATALOG.mkdir(exist_ok=True)
    with open(KONTROLNE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["zgl_id", "etykieta", "tytul", "link", "wybor", "zrodlo"])
        w.writeheader()
        w.writerows(wiersze)
    log(f"zestaw kontrolny: {len(ids)} projektów → {KONTROLNE}")
    return ids


def _czytaj_etykiety(plik) -> tuple[dict[str, str], str]:
    if not plik.exists():
        return {}, "człowiek"
    with open(plik, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return ({r["zgl_id"]: (r.get("etykieta") or "").strip().lower() for r in rows},
            next((r["zrodlo"].strip() for r in rows if (r.get("zrodlo") or "").strip()), "człowiek"))


def opis_etykiet(zrodlo: str, policzone: bool) -> str:
    """Zdanie raportu o pochodzeniu etykiet: człowiek albo głosowanie modeli (wtedy mówimy to wprost)."""
    if not policzone:
        return ". Etykiety „rutyna / nowość” w walidacja/etykiety.csv nie zostały jeszcze wypełnione: zgodność nie jest policzona."
    if zrodlo == "człowiek":
        return ". Etykiety „rutyna / nowość” nadał człowiek w walidacja/etykiety.csv."
    return (f". Etykiety „rutyna / nowość” w walidacja/etykiety.csv to {zrodlo}, nie ocena człowieka;"
            " głosy każdego modelu: walidacja/etykiety_glosy.csv.")


def raport(con, log=print) -> dict:
    etykiety, zrodlo = _czytaj_etykiety(ETYKIETY)
    kontrolne, zrodlo_k = _czytaj_etykiety(KONTROLNE)
    kto = "człowiek" if zrodlo == "człowiek" else "głosowanie modeli"
    kto_k = "człowiek" if zrodlo_k == "człowiek" else "głosowanie modeli"
    wiersze = []
    for zid, rodzaj in con.execute("SELECT zgl_id, rodzaj FROM test"):
        k = db.karta(con, zid)
        if k and k["status"] == "gotowe":
            wiersze.append((f"{rodzaj}:{zid}" if rodzaj in ("etykieta", "kontrolny") else rodzaj, k))
    m = miary(wiersze, etykiety, kontrolne)
    czytelne = {}
    for rodzaj, opis in OPISY.items():
        if rodzaj in m:
            x = m[rodzaj]
            czytelne[opis.split(":")[0] + ": czułość"] = f"{x['trafione']}/{x['wszystkie']} ({x['czulosc']:.2f})"
    if "etykiety" in m:
        e = m["etykiety"]
        czytelne[f"Nowość: zgodność z etykietą ({kto})"] = f"{e['zgodnosc']:.2f} (n={e['n']})"
        czytelne[f"Średni potencjał: nowość / rutyna ({kto})"] = f"{e['potencjal_nowosc']} / {e['potencjal_rutyna']}"
    if "kontrolny" in m:
        e = m["kontrolny"]
        czytelne[f"Zestaw kontrolny, niezależny pomiar: zgodność nowości ({kto_k})"] = f"{e['zgodnosc']:.2f} (n={e['n']})"
        czytelne[f"Zestaw kontrolny: średni potencjał nowość / rutyna ({kto_k})"] = f"{e['potencjal_nowosc']} / {e['potencjal_rutyna']}"
        if e.get("auc_potencjalu") is not None:
            czytelne["Zestaw kontrolny: potencjał nowości wyżej niż rutyny (AUC, bez progu)"] = f"{e['auc_potencjalu']:.2f}"
        wn, wr = e["werdykty"].get("nowosc", {}), e["werdykty"].get("rutyna", {})
        if wn or wr:
            czytelne["Zestaw kontrolny: nowości odrzucone przez lejek"] = f"{wn.get('odrzucone_do_przegladu', 0)}/{sum(wn.values())}"
            czytelne["Zestaw kontrolny: rutyny zatrzymane (odrzucone lub do przeglądu)"] = (
                f"{wr.get('odrzucone_do_przegladu', 0) + wr.get('do_przegladu', 0)}/{sum(wr.values())}")
    czytelne["Mediana czasu sprawdzenia"] = f"{m['czas_mediana_s']} s"
    czytelne["Średni koszt AI na sprawdzenie"] = f"{m['koszt_sredni_usd']} $"
    wynik = {"kiedy": time.strftime("%Y-%m-%d %H:%M"), "miary": czytelne, "szczegoly": m,
             "opis": "Przypadki ze znaną prawdą zbudowane z dzisiejszych danych (RAD-on, Mapa Dotacji): " + "; ".join(OPISY.values())
                     + opis_etykiet(zrodlo, "etykiety" in m)
                     + (f" Zestaw kontrolny (walidacja/kontrolne.csv): projekty wylosowane po zamrożeniu rubryki, etykiety: {zrodlo_k}."
                        if "kontrolny" in m else "")}
    RAPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RAPORT_JSON.write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    KATALOG.mkdir(exist_ok=True)
    RAPORT_MD.write_text("# Raport walidacji\n\n" + f"Uruchomienie: {wynik['kiedy']}, przypadków: {m['przypadkow']}.\n\n"
                         + "| Miara | Wartość |\n|---|---|\n" + "".join(f"| {a} | {b} |\n" for a, b in czytelne.items())
                         + "\n" + wynik["opis"] + "\n", encoding="utf-8")
    log(json.dumps(czytelne, ensure_ascii=False, indent=1))
    return wynik
