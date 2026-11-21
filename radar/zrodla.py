"""Dla listy stron WWW wykrywa źródło wpisów: kanał RSS/Atom albo podstronę z aktualnościami.

Użycie:  python3 radar/zrodla.py wejscie.csv dane/zrodla.csv   (wejście: kolumny id, www)
Szanuje robots.txt, 1 zapytanie na sekundę, timeout 20 s. Wynik: id, www, rss, aktualnosci, status.
"""
import csv
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.robotparser
from html.parser import HTMLParser

UA = "Mozilla/5.0 (radar-innowacji; badanie danych publicznych)"
# Adres z RSPO wygasł i domenę przejął ktoś inny (handel domenami, blogi, portale): sprawdzone ręcznie 16.11.
# ponytail: ręczna lista; przy kolejnych regionach wykrywać „domena na sprzedaż” po treści strony.
OBCE_HOSTY = {"nicsell.com", "dbv.pl", "mojainwestycja.pl", "n122.domenomania.pl", "flagman-kasyno.co.pl", "wp.pl",
              "facebook.com", "webd.pl", "prokris.com"}
SLOWA_AKT = re.compile(r"aktualno|wiadomo|news|ogłoszen|wydarzen|z życia", re.I)
SCIEZKI_RSS = ["/feed/", "/rss", "/rss.xml", "/?format=feed&type=rss", "/index.php?format=feed&type=rss"]


class Linki(HTMLParser):
    """Linki <a> i kanały RSS. tylko_tresc=True pomija linki w menu, nagłówku, stopce i pasku bocznym."""
    POZA_TRESCIA = ("nav", "header", "footer", "aside")

    def __init__(self, tylko_tresc=False, url=""):
        super().__init__()
        self.url = url  # adresy względne → pełne, z uwzględnieniem <base href>
        self.naglowek, self._h, self.przed = "", None, {}  # nagłówek tuż przed linkiem (tytuł karty z „Czytaj więcej”)
        self.rss, self.a, self._href, self._tekst = [], [], None, ""
        self.tylko_tresc, self._poza = tylko_tresc, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.POZA_TRESCIA:
            self._poza += 1
        if tag in ("h1", "h2", "h3", "h4"):
            self._h = ""
        if tag == "base" and a.get("href"):
            self.url = urllib.parse.urljoin(self.url, a["href"])
        if tag == "link" and "alternate" in (a.get("rel") or "") and re.search(r"rss|atom", a.get("type") or ""):
            self.rss.append(urllib.parse.urljoin(self.url, a["href"]) if a.get("href") else None)
        if tag == "a" and not (self.tylko_tresc and self._poza):
            self._href, self._tekst = a.get("href"), ""

    def handle_data(self, data):
        if self._h is not None:
            self._h += data
        if self._href is not None:
            self._tekst += data

    def handle_endtag(self, tag):
        if tag in self.POZA_TRESCIA:
            self._poza = max(0, self._poza - 1)
        if tag in ("h1", "h2", "h3", "h4") and self._h is not None:
            self.naglowek, self._h = re.sub(r"\s+", " ", self._h).strip(), None
        if tag == "a" and self._href:
            u = urllib.parse.urljoin(self.url, self._href)
            self.a.append((u, self._tekst.strip()))
            self.przed.setdefault(u, self.naglowek)
            self.naglowek = ""  # nagłówek należy tylko do najbliższego linku za nim
            self._href = None


class Zablokowane(IOError):
    """Adres zabroniony w robots.txt."""


def pobierz(url, sprawdz_robots=True):
    # Systemowy curl zamiast urllib: wiele stron szkół ma niepełny łańcuch certyfikatów, który curl (macOS) uzupełnia,
    # a Python nie. Weryfikacja TLS zostaje włączona. Każdy adres (poza samym robots.txt) przechodzi przez robots.txt.
    if sprawdz_robots and not wolno(url):
        raise Zablokowane(f"robots.txt: {url}")
    r = subprocess.run(["curl", "-sSL", "--max-time", "20", "--max-filesize", "5000000", "-A", UA,
                        "-w", "\n%{url_effective}\n%{http_code}", url], capture_output=True)
    if r.returncode:
        raise IOError(r.stderr.decode("utf-8", "replace").strip()[:100])
    tresc, adres, kod = r.stdout.decode("utf-8", "replace").rsplit("\n", 2)
    if not kod.startswith("2"):
        raise IOError(f"HTTP {kod}")
    return adres, "", tresc


_ROBOTS = {}


def wolno(url):
    """robots.txt, jeden parser na host (pamięć podręczna). 401/403 na robots.txt = zakaz; brak pliku = zgoda."""
    p = urllib.parse.urlparse(url if "://" in url else "http://" + url)
    klucz = (p.scheme, p.netloc)
    if klucz not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.parse(pobierz(f"{p.scheme}://{p.netloc}/robots.txt", sprawdz_robots=False)[2].splitlines())
        except IOError as e:
            if re.search(r"HTTP 40[13]", str(e)):
                rp.disallow_all = True
            else:
                rp.allow_all = True
        _ROBOTS[klucz] = rp
    return _ROBOTS[klucz].can_fetch(UA, url)


def to_kanal(tresc):
    return bool(re.search(r"<(rss|feed)[\s>]", tresc[:3000]))


def obca(url):
    h = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    return (h[4:] if h.startswith("www.") else h) in OBCE_HOSTY  # dokładnie: szkoły mają strony np. na *.webd.pl


def wykryj(www):
    url = www if www.startswith("http") else "http://" + www
    try:
        baza, _, html = pobierz(url)
    except IOError:
        if "://www." not in url:
            raise
        url = url.replace("://www.", "://", 1)  # certyfikat często jest tylko na domenę bez www
        baza, _, html = pobierz(url)
    if obca(baza):
        return {"status": "obca domena", "www": baza}
    p = Linki(url=baza)
    p.feed(html)
    rss = next((urllib.parse.urljoin(baza, h) for h in p.rss if h), "")
    if not rss:
        for s in SCIEZKI_RSS:
            u = urllib.parse.urljoin(baza, s)
            time.sleep(1)
            try:
                if to_kanal(pobierz(u)[2]):
                    rss = u
                    break
            except Exception:
                pass
    host = urllib.parse.urlparse(baza).netloc
    akt = next((urllib.parse.urljoin(baza, h) for h, t in p.a
                if SLOWA_AKT.search(t or "") and urllib.parse.urlparse(urllib.parse.urljoin(baza, h)).netloc == host), "")
    return {"status": "ok", "www": baza, "rss": rss, "aktualnosci": akt}


def ostatnie_zrodla(plik):
    """id → ostatni wiersz z pliku źródeł."""
    if not os.path.exists(plik):
        return {}
    return {r["id"]: r for r in csv.DictReader(open(plik, encoding="utf-8"))}


def main(we, wy):
    wiersze = list(csv.DictReader(open(we, encoding="utf-8")))
    # wznawianie: pomijamy id z wynikiem ok/robots; wiersze z błędem (np. chwilowy brak sieci) ponawiamy.
    # Plik może mieć kilka wierszy dla id: obowiązuje ostatni (patrz ostatnie_zrodla).
    juz = {i for i, r in ostatnie_zrodla(wy).items() if not r["status"].startswith("błąd")}
    nowy = not (os.path.exists(wy) and os.path.getsize(wy))
    with open(wy, "a", newline="", encoding="utf-8") as f:  # wznawialne: dopisuje, pomija gotowe id
        w = csv.DictWriter(f, fieldnames=["id", "www", "rss", "aktualnosci", "status"])
        if nowy:
            w.writeheader()
        for r in wiersze:
            if r["id"] in juz:
                continue
            try:
                wynik = wykryj(r["www"])
            except Zablokowane:
                wynik = {"status": "robots"}
            except Exception as e:
                wynik = {"status": f"błąd: {type(e).__name__}"}
            w.writerow({"id": r["id"], "www": r["www"], **wynik})
            f.flush()
            print(r["id"], wynik.get("status"), bool(wynik.get("rss")), bool(wynik.get("aktualnosci")), flush=True)
            time.sleep(1)


if __name__ == "__main__":
    p = Linki()
    p.feed('<link rel="alternate" type="application/rss+xml" href="/feed/"><a href="/akt">Aktualności</a>')
    assert p.rss == ["/feed/"] and p.a == [("/akt", "Aktualności")]
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /prywatne/"])
    _ROBOTS[("https", "t.pl")] = rp
    blok = urllib.robotparser.RobotFileParser()
    blok.disallow_all = True
    _ROBOTS[("https", "b.pl")] = blok
    assert wolno("https://t.pl/aktualnosci") and not wolno("https://t.pl/prywatne/x") and not wolno("https://b.pl/")
    try:
        pobierz("https://b.pl/x")
        raise AssertionError("powinno zablokować")
    except Zablokowane:
        pass
    p = Linki(tylko_tresc=True)
    p.feed('<nav><a href="/kontakt">Kontakt ze szkołą</a></nav><main><a href="/aktualnosci/x">Wpis</a></main>')
    assert p.a == [("/aktualnosci/x", "Wpis")]
    p = Linki(url="https://s.pl/aktualności/")
    p.feed('<base href="https://s.pl/"><a href="wpis.html">Wpis</a>')
    assert p.a == [("https://s.pl/wpis.html", "Wpis")]
    p = Linki()
    p.feed('<h3>Kwesta koła Caritas</h3><p>…</p><a href="/a">Czytaj więcej</a><a href="/b">Czytaj więcej</a>')
    assert p.przed == {"/a": "Kwesta koła Caritas", "/b": ""}
    assert obca("https://nicsell.com/en/domain/pp14.pl") and obca("https://n122.domenomania.pl/") and not obca("https://zsp1nisko.pl/") and not obca("http://www.kopkipsp.webd.pl/")
    assert to_kanal('<?xml version="1.0"?><rss version="2.0">')
    main(*sys.argv[1:3])
