"""Aplikacja WWW i API: zgłoszenia, kolejki organizacji, karta z dowodami, decyzje człowieka, wyszukiwarka, miary."""
import json
import logging
import os
import re
import statistics
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape
from pydantic import BaseModel, Field, ValidationError, field_validator

from . import ai, config, db, organizacje, siec, slowniki, tekst
from .model import Zgloszenie
from .sprawdz import sprawdz

log = logging.getLogger("radar")
KATALOG = Path(__file__).parent
LIMIT_IP_GODZ = 20       # sprawdzeń na adres IP na godzinę (koszt jednego to ok. 0,001 $)
LIMIT_DZIEN = 200        # sprawdzeń na dobę dla całego demo
MAX_ROWNOLEGLYCH = 3


# ---------- połączenie, praca w tle ----------
def polaczenie():
    con = db.polacz()
    try:
        yield con
    finally:
        con.close()


_semafor = threading.Semaphore(MAX_ROWNOLEGLYCH)


def sprawdz_w_tle(zid: int) -> None:
    """Osobne połączenie na zadanie w tle: sprawdzenie trwa 15–60 s i pisze w transakcjach."""
    with _semafor:
        con = db.polacz()
        try:
            sprawdz(con, zid)
        except Exception:
            log.exception("sprawdzenie %s nie powiodło się", zid)
            db.ustaw_status(con, zid, "blad")
        finally:
            con.close()


def napraw_przerwane(con) -> None:
    """Po restarcie serwera sprawdzenia „w toku” już nie wrócą: oznaczamy je jako błąd (karta pozwala ponowić)."""
    with con:
        con.execute("UPDATE zgloszenie SET status='blad' WHERE status IN ('nowe', 'w_toku')")


@asynccontextmanager
async def cykl(app):
    con = db.polacz()
    napraw_przerwane(con)
    con.close()
    yield


app = FastAPI(title="Radar Innowacji", version="0.1", lifespan=cykl,
              description="Wyszukiwanie i ocena innowacji: plagiat, kopia, patent, nowość, z dowodami. Decyzję podejmuje człowiek.")
app.mount("/static", StaticFiles(directory=KATALOG / "static"), name="static")


# ---------- limit zapytań ----------
class Limiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.wyczysc()

    def wyczysc(self):
        self.ip: dict[str, deque] = defaultdict(deque)
        self.dzien: deque = deque()

    def zuzyj(self, ip: str) -> str | None:
        teraz = time.time()
        with self.lock:
            q = self.ip[ip]
            while q and q[0] < teraz - 3600:
                q.popleft()
            while self.dzien and self.dzien[0] < teraz - 86400:
                self.dzien.popleft()
            if len(self.dzien) >= LIMIT_DZIEN:
                return f"Dzienny limit sprawdzeń w wersji demo ({LIMIT_DZIEN}) został wyczerpany. Wróć jutro."
            if len(q) >= LIMIT_IP_GODZ:
                return f"Limit {LIMIT_IP_GODZ} sprawdzeń na godzinę z jednego adresu. Spróbuj za kilkadziesiąt minut."
            q.append(teraz)
            self.dzien.append(teraz)
        return None


limiter = Limiter()


def ip_klienta(request: Request) -> str:
    host = request.client.host if request.client else "?"
    if host in ("127.0.0.1", "::1"):  # za Caddy: ufamy nagłówkowi tylko od lokalnego proxy
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
    return host


def pilnuj_limitu(request: Request) -> None:
    komunikat = limiter.zuzyj(ip_klienta(request))
    if komunikat:
        raise HTTPException(429, komunikat)


# ---------- szablony ----------
def bezpieczny_link(url) -> str | None:
    """Do href trafiają tylko adresy http(s) i ścieżki tej samej witryny (np. /karta/3)."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if re.fullmatch(r"https?://[^\s\"'<>\\]+", url, re.I):
        return url
    if re.fullmatch(r"/(?![/\\])[^\s\"'<>\\]*", url):
        return url
    return None


def podswietl(t: str | None, fragmenty: list[str] | None) -> Markup:
    """Tekst z <mark> na fragmentach (dopasowanie słowo po słowie, bez względu na wielkość liter i interpunkcję)."""
    t = t or ""
    zakresy = []
    for f in fragmenty or []:
        slowa = re.findall(r"\w+", f)
        if len(slowa) < 3:
            continue
        for m in re.finditer(r"\W+".join(re.escape(s) for s in slowa), t, re.I):
            zakresy.append([m.start(), m.end()])
    zakresy.sort()
    scalone: list[list[int]] = []
    for a, b in zakresy:
        if scalone and a <= scalone[-1][1]:
            scalone[-1][1] = max(scalone[-1][1], b)
        else:
            scalone.append([a, b])
    wynik, poz = [], 0
    for a, b in scalone:
        wynik += [escape(t[poz:a]), Markup("<mark>"), escape(t[a:b]), Markup("</mark>")]
        poz = b
    wynik.append(escape(t[poz:]))
    return Markup("").join(wynik)


def _data(ts) -> str:
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts)) if ts else ""


def _liczba(x, miejsca=1) -> str:
    if x is None:
        return "—"
    return f"{x:,.{miejsca}f}".replace(",", " ").replace(".", ",")


srodowisko = Environment(loader=FileSystemLoader(KATALOG / "templates"), autoescape=select_autoescape(["html"]))
srodowisko.filters.update(link=bezpieczny_link, podswietl=podswietl, data=_data, liczba=_liczba)
srodowisko.globals.update(s=slowniki, organizacje=organizacje.lista)
szablony = Jinja2Templates(env=srodowisko)


def strona(request: Request, nazwa: str, status: int = 200, **ctx) -> HTMLResponse:
    return szablony.TemplateResponse(request, nazwa, ctx, status_code=status)


@app.exception_handler(HTTPException)
async def _blad_http(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api") or request.url.path.startswith("/docs"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return strona(request, "blad.html", exc.status_code, kod=exc.status_code, komunikat=exc.detail)


# ---------- zgłoszenie: walidacja wspólna dla formularza i API ----------
class ZgloszenieWe(BaseModel):
    zrodlo_dok: str | None = Field(None, max_length=200, description="Ocena projektu z bazy: id dokumentu (np. radon:…)")
    tytul: str = Field(min_length=5, max_length=200, description="Tytuł, 5–200 znaków")
    opis: str = Field(min_length=80, max_length=8000, description="Opis, 300–8000 znaków (80 dla projektu z bazy)")
    link: str | None = Field(None, description="Strona z opisem (opcjonalnie), tylko http(s)")
    instytucja: str = Field(min_length=2, max_length=200)
    typ_instytucji: Literal[tuple(slowniki.TYPY_INSTYTUCJI)]
    typ_innowacji: Literal[tuple(slowniki.TYPY_INNOWACJI)]
    etap: Literal[tuple(slowniki.ETAPY)]
    wiek_przedzial: Literal[tuple(slowniki.WIEK)]
    organizacja: str = Field("ogolny", description="Organizacja, do której kierowane jest zgłoszenie (slug profilu)")

    @field_validator("tytul", "opis", "instytucja", mode="before")
    @classmethod
    def _przytnij(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("zrodlo_dok", mode="before")
    @classmethod
    def _zrodlo(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        if not re.fullmatch(r"[a-z_]+:\S{1,150}", v):
            raise ValueError("nieprawidłowy identyfikator dokumentu")
        return v

    @field_validator("opis")
    @classmethod
    def _opis_min(cls, v, info):
        if len(v) < 300 and not info.data.get("zrodlo_dok"):
            raise ValueError("za krótki (min. 300 znaków)")
        return v

    @field_validator("link", mode="before")
    @classmethod
    def _link(cls, v):
        v = (v or "").strip()
        if not v:
            return None
        if not re.fullmatch(r"https?://\S+", v, re.I) or len(v) > 500:
            raise ValueError("link musi zaczynać się od http:// lub https://")
        return v

    @field_validator("organizacja")
    @classmethod
    def _organizacja(cls, v):
        if v not in {o["slug"] for o in organizacje.lista()}:
            raise ValueError("nieznana organizacja")
        return v


NAZWY_POL = {"tytul": "Tytuł", "opis": "Opis", "link": "Link", "instytucja": "Instytucja", "typ_instytucji": "Typ instytucji",
             "typ_innowacji": "Typ innowacji", "etap": "Etap", "wiek_przedzial": "Wiek twórców", "organizacja": "Organizacja"}


def _bledy_po_polsku(e: ValidationError) -> dict[str, str]:
    out = {}
    for b in e.errors():
        pole = str(b["loc"][-1]) if b["loc"] else "?"
        if b["type"] == "string_too_short" and pole == "opis":
            out[pole] = "Opis: za krótki (min. 300 znaków; 80 dla projektu z bazy)."
        elif b["type"] == "string_too_short":
            out[pole] = f"{NAZWY_POL.get(pole, pole)}: za krótkie (min. {b['ctx']['min_length']} znaków)."
        elif b["type"] == "string_too_long":
            out[pole] = f"{NAZWY_POL.get(pole, pole)}: za długie (maks. {b['ctx']['max_length']} znaków)."
        elif b["type"] == "literal_error":
            out[pole] = f"{NAZWY_POL.get(pole, pole)}: wybierz wartość z listy."
        else:
            out[pole] = f"{NAZWY_POL.get(pole, pole)}: {b['msg'].removeprefix('Value error, ')}."
    return out


def _zapisz(con, we: ZgloszenieWe, wejscie: str = "formularz") -> int:
    zrodlo = we.zrodlo_dok if we.zrodlo_dok and db.dokument(con, we.zrodlo_dok) else None
    wejscie = "baza" if zrodlo else wejscie
    return db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie=wejscie, zrodlo_dok=zrodlo, tytul=we.tytul, opis=we.opis, link=we.link,
                                                instytucja=we.instytucja, typ_instytucji=we.typ_instytucji,
                                                typ_innowacji=we.typ_innowacji, etap=we.etap,
                                                wiek_przedzial=we.wiek_przedzial, organizacja=we.organizacja))


# ---------- strony ----------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def start(request: Request, con=Depends(polaczenie)):
    liczby = db.liczba_dokumentow(con)
    zgl = con.execute("SELECT count(*) FROM zgloszenie").fetchone()[0]
    stan = {k: time.strftime("%d.%m.%Y", time.localtime(v["pobrano_do"])) for k, v in db.stan_zrodel(con).items() if v["pobrano_do"]}
    return strona(request, "start.html", liczby=liczby, razem=sum(v for k, v in liczby.items()), zgloszen=zgl, stan=stan)


@app.get("/zglos", response_class=HTMLResponse, include_in_schema=False)
def zglos_formularz(request: Request, organizacja: str = "pci", z_dokumentu: str = "", con=Depends(polaczenie)):
    """Pusty formularz albo wypełniony projektem z bazy (analityk ocenia znaleziony projekt)."""
    pola = {"organizacja": organizacja}
    dok = db.dokument(con, z_dokumentu) if z_dokumentu else None
    if dok:
        instytucja = dok.instytucje[0] if dok.instytucje else ""
        if not instytucja and dok.zrodlo == "mapadotacji":
            from .zrodla import mapadotacji
            try:
                instytucja = mapadotacji.beneficjent(dok.link) or ""
            except Exception:
                instytucja = ""
        pola.update(tytul=dok.tytul[:200], opis=dok.opis[:8000], link=bezpieczny_link(dok.link) or "", instytucja=instytucja[:200],
                    zrodlo_dok=dok.id, etap="zakonczone" if dok.zrodlo in {"mapadotacji", "interreg"} else "")
    return strona(request, "zglos.html", pola=pola, bledy={}, dokument=dok)


@app.post("/zglos", include_in_schema=False)
async def zglos(request: Request, tlo: BackgroundTasks, con=Depends(polaczenie)):
    pola = {k: (v if isinstance(v, str) else "") for k, v in (await request.form()).items()}
    try:
        we = ZgloszenieWe(**pola)
    except ValidationError as e:
        return strona(request, "zglos.html", 422, pola=pola, bledy=_bledy_po_polsku(e))
    pilnuj_limitu(request)
    zid = _zapisz(con, we)
    tlo.add_task(sprawdz_w_tle, zid)
    return RedirectResponse(f"/karta/{zid}", status_code=303)


@app.post("/zglos/z-linku", response_class=HTMLResponse, include_in_schema=False)
def zglos_z_linku(request: Request, link: str = Form(...), organizacja: str = Form("pci")):
    pilnuj_limitu(request)
    pola = {"link": link, "organizacja": organizacja}
    try:
        adres, html = siec.pobierz_publiczna(link.strip())
    except siec.Zablokowane:
        return strona(request, "zglos.html", 422, pola=pola, bledy={"link": "Robots.txt tej strony nie pozwala na pobranie."})
    except ValueError as e:
        return strona(request, "zglos.html", 422, pola=pola, bledy={"link": str(e)})
    except httpx.HTTPError:
        return strona(request, "zglos.html", 422, pola=pola, bledy={"link": "Nie udało się pobrać strony."})
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    tytul = tekst.bez_html(m.group(1))[:200] if m else ""
    tresc = tekst.bez_html(re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html))
    karta, _ = ai.karta_z_tekstu(tytul, tresc)
    srodek = tresc.find(karta["cytat"]) if karta.get("cytat") else -1
    fragment = tresc[max(0, srodek - 600): max(0, srodek - 600) + 2000] if srodek >= 0 else tresc[:2000]
    pola.update(tytul=tytul, opis=(karta["co"] + "\n\n" + fragment).strip(), instytucja=karta["instytucja"],
                typ_innowacji=karta["typ_innowacji"], etap=karta["etap"], link=adres)
    return strona(request, "zglos.html", pola=pola, bledy={}, z_linku=True, cytat=karta.get("cytat"))


def _kolejka(con, organizacja=None, werdykt=None, komorka=None, wejscie=None) -> list[dict]:
    sql = """SELECT z.id, z.tytul, z.instytucja, z.komorka, z.wejscie, z.werdykt, z.status, z.organizacja, z.utworzono_at, z.demo,
                    z.czas_s, (SELECT group_concat(filtr || ':' || pasmo) FROM wynik w WHERE w.zgl_id = z.id) AS pasma,
                    (SELECT wynik FROM ocena o WHERE o.zgl_id = z.id) AS potencjal,
                    (SELECT decyzja FROM decyzja d WHERE d.zgl_id = z.id ORDER BY kiedy DESC LIMIT 1) AS decyzja
             FROM zgloszenie z WHERE 1=1"""
    args = []
    for pole, wartosc in (("organizacja", organizacja), ("werdykt", werdykt), ("komorka", komorka), ("wejscie", wejscie)):
        if wartosc:
            sql += f" AND z.{pole} = ?"
            args.append(wartosc)
    sql += """ ORDER BY (decyzja IS NOT NULL), CASE z.werdykt WHEN 'odrzucone_do_przegladu' THEN 0 WHEN 'do_przegladu' THEN 1
              WHEN 'dalej' THEN 2 ELSE 3 END, potencjal DESC NULLS LAST, z.id DESC LIMIT 500"""
    out = []
    for r in con.execute(sql, args):
        d = dict(r)
        d["pasma"] = dict(p.split(":", 1) for p in (d["pasma"] or "").split(",") if ":" in p)
        out.append(d)
    return out


@app.get("/kolejka", response_class=HTMLResponse, include_in_schema=False)
def kolejka(request: Request, werdykt: str = "", komorka: str = "", wejscie: str = "", con=Depends(polaczenie)):
    wiersze = _kolejka(con, None, werdykt, komorka, wejscie)
    return strona(request, "kolejka.html", wiersze=wiersze, profil=None, filtr={"werdykt": werdykt, "komorka": komorka,
                                                                               "wejscie": wejscie})


@app.get("/o/{slug}/kolejka", response_class=HTMLResponse, include_in_schema=False)
def kolejka_organizacji(request: Request, slug: str, werdykt: str = "", komorka: str = "", wejscie: str = "",
                        con=Depends(polaczenie)):
    if slug not in {o["slug"] for o in organizacje.lista()}:
        raise HTTPException(404, "Nie ma takiej organizacji.")
    profil = organizacje.wczytaj(slug)
    wszystkie = _kolejka(con, slug)
    licznik = defaultdict(int)
    for w in wszystkie:
        licznik[w["komorka"]] += 1
    wiersze = _kolejka(con, slug, werdykt, komorka, wejscie)
    return strona(request, "kolejka.html", wiersze=wiersze, profil=profil, licznik=licznik,
                  filtr={"werdykt": werdykt, "komorka": komorka, "wejscie": wejscie})


def _teksty_dowodow(con, k: dict) -> dict[str, str]:
    """Pełne teksty dokumentów z dowodów plagiatu (do porównania obok siebie)."""
    out = {}
    for w in k["wyniki"]:
        if w["filtr"] != "plagiat":
            continue
        for d in w["dowody"]:
            did = d.get("dokument_id") or ""
            if did.startswith("zgloszenie:"):
                z = db.zgloszenie(con, int(did.split(":")[1]))
                out[did] = z.opis if z else ""
            else:
                dok = db.dokument(con, did)
                out[did] = f"{dok.tytul}. {dok.opis}" if dok else ""
    return out


@app.get("/karta/{zid}", response_class=HTMLResponse, include_in_schema=False)
def karta(request: Request, zid: int, con=Depends(polaczenie)):
    k = db.karta(con, zid)
    if not k:
        raise HTTPException(404, "Nie ma takiego zgłoszenia.")
    profil = organizacje.wczytaj(k["organizacja"])
    return strona(request, "karta.html", k=k, profil=profil, teksty=_teksty_dowodow(con, k),
                  komorka=organizacje.nazwa_komorki(profil, k["komorka"] or ""))


@app.post("/karta/{zid}/decyzja", response_class=HTMLResponse, include_in_schema=False)
def decyzja(request: Request, zid: int, decyzja: str = Form(...), powod: str = Form(""), con=Depends(polaczenie)):
    if not db.zgloszenie(con, zid):
        raise HTTPException(404, "Nie ma takiego zgłoszenia.")
    if decyzja not in slowniki.DECYZJE or len(powod.strip()) < 3 or len(powod) > 1000:
        raise HTTPException(422, "Wybierz decyzję i wpisz powód (min. 3 znaki).")
    db.zapisz_decyzje(con, zid, decyzja, powod.strip())
    return karta(request, zid, con)


@app.post("/karta/{zid}/ponow", include_in_schema=False)
def ponow(request: Request, zid: int, tlo: BackgroundTasks, con=Depends(polaczenie)):
    if not db.zgloszenie(con, zid):
        raise HTTPException(404, "Nie ma takiego zgłoszenia.")
    pilnuj_limitu(request)
    db.ustaw_status(con, zid, "nowe")
    tlo.add_task(sprawdz_w_tle, zid)
    return RedirectResponse(f"/karta/{zid}", status_code=303)


def wyszukaj(con, q: str) -> dict:
    df, n = db.funkcja_df(con)
    terminy = tekst.terminy(q, n=12, df=df, N=n)
    dokumenty: dict[str, list] = defaultdict(list)
    for d, wynik in db.szukaj(con, terminy, limit=40):
        dokumenty[d.typ].append({"id": d.id, "tytul": d.tytul, "opis": d.opis[:300], "link": d.link, "zrodlo": d.zrodlo,
                                 "rok": d.rok, "instytucje": d.instytucje[:3], "status": d.status, "wynik": round(wynik, 2)})
    zgl = []
    for r in con.execute("""SELECT z.id, z.tytul, z.opis, z.instytucja, z.werdykt, z.komorka, z.organizacja, z.status,
                            (SELECT group_concat(filtr || ':' || pasmo) FROM wynik w WHERE w.zgl_id = z.id) AS pasma
                            FROM zgloszenie z WHERE z.status != 'blad'"""):
        s = tekst.podobienstwo(q, f"{r['tytul']}. {r['tytul']}. {r['opis']}", df, n)
        if s > 0.05:
            zgl.append({"id": r["id"], "tytul": r["tytul"], "opis": r["opis"][:300], "instytucja": r["instytucja"],
                        "werdykt": r["werdykt"], "organizacja": r["organizacja"], "podobienstwo": round(s * 100, 1),
                        "pasma": dict(p.split(":", 1) for p in (r["pasma"] or "").split(",") if ":" in p),
                        "link": f"/karta/{r['id']}"})
    zgl.sort(key=lambda x: -x["podobienstwo"])
    return {"zapytanie": q, "terminy": terminy, "zgloszenia": zgl[:15], "dokumenty": dict(dokumenty)}


@app.get("/szukaj", response_class=HTMLResponse, include_in_schema=False)
def szukaj_strona(request: Request, q: str = "", con=Depends(polaczenie)):
    wynik = wyszukaj(con, q) if len(q.strip()) >= 3 else None
    return strona(request, "szukaj.html", q=q, wynik=wynik)


def _miary(con) -> dict:
    zgl = [dict(r) for r in con.execute("SELECT werdykt, wejscie, czas_s, koszt_usd, status, organizacja FROM zgloszenie")]
    gotowe = [z for z in zgl if z["status"] == "gotowe"]
    czasy = [z["czas_s"] for z in gotowe if z["czas_s"] is not None]
    koszty = [z["koszt_usd"] or 0 for z in gotowe]
    decyzje = [dict(r) for r in con.execute("""SELECT d.decyzja, z.werdykt FROM decyzja d JOIN zgloszenie z ON z.id = d.zgl_id
                                               WHERE d.id IN (SELECT max(id) FROM decyzja GROUP BY zgl_id)""")]
    flagowane = [d for d in decyzje if d["werdykt"] in ("odrzucone_do_przegladu", "do_przegladu")]
    potwierdzone = sum(d["decyzja"] == "potwierdz_odrzucenie" for d in flagowane if d["werdykt"] == "odrzucone_do_przegladu")
    odrzucone = sum(d["werdykt"] == "odrzucone_do_przegladu" for d in flagowane)
    raport = config.DANE / "zestaw_raport.json"
    return {"zgloszen": len(zgl), "gotowych": len(gotowe),
            "werdykty": {w: sum(z["werdykt"] == w for z in gotowe) for w in slowniki.WERDYKTY},
            "wejscia": {w: sum(z["wejscie"] == w for z in zgl) for w in slowniki.WEJSCIA},
            "czas_mediana_s": statistics.median(czasy) if czasy else None, "czas_max_s": max(czasy) if czasy else None,
            "koszt_sredni_usd": sum(koszty) / len(koszty) if koszty else None, "koszt_razem_usd": sum(koszty),
            "decyzji": len(decyzje), "odrzucen_z_decyzja": odrzucone, "odrzucen_potwierdzonych": potwierdzone,
            "korpus": db.liczba_dokumentow(con),
            "zestaw": json.loads(raport.read_text(encoding="utf-8")) if raport.exists() else None}


def _zrodla_stan(con) -> list[dict]:
    stan = db.stan_zrodel(con)
    out = []
    for klucz, h in slowniki.HARMONOGRAM.items():
        s = stan.get(klucz) or {}
        do = s.get("pobrano_do")
        out.append({"zrodlo": klucz, "nazwa": slowniki.ZRODLA[klucz][0], "adres": slowniki.ZRODLA[klucz][1],
                    "dokumentow": s.get("dokumentow", 0), "stan_na": time.strftime("%Y-%m-%d %H:%M", time.localtime(do)) if do else None,
                    "najnowszy_rok": s.get("najnowszy_rok"), **h})
    return out


def _sciezka_ai() -> dict:
    url = os.environ.get("AI_URL") or ai.URL
    if "openrouter.ai" in url:
        return {"sciezka": "A: API (OpenRouter)" if os.environ.get("OPENROUTER_API_KEY") else "C: bez AI (brak klucza)",
                "model": os.environ.get("MODEL") or config.MODEL}
    return {"sciezka": "B: model lokalny", "model": os.environ.get("MODEL") or config.MODEL}


@app.get("/warunki", response_class=HTMLResponse, include_in_schema=False)
def warunki(request: Request, con=Depends(polaczenie)):
    return strona(request, "warunki.html", zrodla=_zrodla_stan(con), ai_teraz=_sciezka_ai())


@app.get("/api/zrodla", tags=["źródła"], summary="Źródła: liczba dokumentów, stan danych, harmonogram aktualizacji")
def api_zrodla(con=Depends(polaczenie)):
    return _zrodla_stan(con)


@app.get("/miary", response_class=HTMLResponse, include_in_schema=False)
def miary(request: Request, con=Depends(polaczenie)):
    return strona(request, "miary.html", m=_miary(con))


# ---------- API ----------
@app.get("/api/zgloszenia", tags=["zgłoszenia"], summary="Lista zgłoszeń (najpierw z flagą)")
def api_lista(organizacja: str = "", werdykt: str = "", komorka: str = "", con=Depends(polaczenie)):
    return _kolejka(con, organizacja or None, werdykt or None, komorka or None)


@app.post("/api/zgloszenia", status_code=202, tags=["zgłoszenia"], summary="Nowe zgłoszenie; sprawdzenie rusza w tle")
def api_zglos(we: ZgloszenieWe, request: Request, tlo: BackgroundTasks, con=Depends(polaczenie)):
    pilnuj_limitu(request)
    zid = _zapisz(con, we)
    tlo.add_task(sprawdz_w_tle, zid)
    return {"id": zid, "status": "nowe", "karta": f"/karta/{zid}", "api": f"/api/karta/{zid}"}


app.post("/api/sprawdz", status_code=202, tags=["zgłoszenia"], summary="To samo co POST /api/zgloszenia")(api_zglos)


@app.get("/api/karta/{zid}", tags=["zgłoszenia"], summary="Karta: wyniki 4 filtrów z dowodami, werdykt, komórka, ścieżka")
def api_karta(zid: int, con=Depends(polaczenie)):
    k = db.karta(con, zid)
    if not k:
        raise HTTPException(404, "Nie ma takiego zgłoszenia.")
    return k


@app.get("/api/szukaj", tags=["wyszukiwanie"], summary="Szukam rozwiązania: zgłoszenia i dokumenty z korpusu (bez AI)")
def api_szukaj(q: str, con=Depends(polaczenie)):
    if len(q.strip()) < 3:
        raise HTTPException(422, "Zapytanie musi mieć co najmniej 3 znaki.")
    return wyszukaj(con, q)


@app.get("/api/miary", tags=["miary"], summary="Miary: czas, koszt, werdykty, decyzje, korpus, zestaw testowy")
def api_miary(con=Depends(polaczenie)):
    return _miary(con)


@app.get("/api/organizacje", tags=["organizacje"], summary="Profile organizacji oceniających")
def api_organizacje():
    return organizacje.lista()
