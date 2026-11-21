"""Grzeczne pobieranie: robots.txt per host, 1 zapytanie/s na host, identyfikujący User-Agent, ponowienia."""
import threading
import time
import urllib.robotparser
from urllib.parse import urlsplit

import httpx

from . import config


class Zablokowane(Exception):
    """Adres zakazany przez robots.txt."""


_klient = httpx.Client(headers={"User-Agent": config.USER_AGENT}, follow_redirects=True, timeout=30, verify=True)
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_ostatnio: dict[str, float] = {}
_blokada = threading.Lock()
ODSTEP_S = 1.0


def ustaw_robots(host: str, tekst: str) -> None:
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(tekst.splitlines())
    _robots[host] = rp


def _czekaj(host: str) -> None:
    with _blokada:
        teraz = time.monotonic()
        czekaj = _ostatnio.get(host, 0) + ODSTEP_S - teraz
        _ostatnio[host] = max(teraz, _ostatnio.get(host, 0) + ODSTEP_S)
    if czekaj > 0:
        time.sleep(czekaj)


def _dozwolone(url: str) -> bool:
    cz = urlsplit(url)
    host = cz.netloc
    if host not in _robots:
        try:
            _czekaj(host)
            r = _klient.get(f"{cz.scheme}://{host}/robots.txt", timeout=15)
            if r.status_code in (401, 403):
                ustaw_robots(host, "User-agent: *\nDisallow: /")   # ostrożniej niż RFC 9309
            elif r.status_code >= 400 or "html" in r.headers.get("content-type", ""):
                _robots[host] = None                                # brak pliku = zgoda
            else:
                ustaw_robots(host, r.text)
        except httpx.HTTPError:
            _robots[host] = None
    rp = _robots[host]
    return rp is None or rp.can_fetch(config.USER_AGENT, url)


def pobierz(url: str, *, params: dict | None = None, headers: dict | None = None, metoda: str = "GET",
            dane=None, timeout: float = 30) -> httpx.Response:
    if not _dozwolone(url):
        raise Zablokowane(url)
    host = urlsplit(url).netloc
    for proba, pauza in enumerate((2, 4, 8, None)):
        _czekaj(host)
        try:
            r = _klient.request(metoda, url, params=params, headers=headers, data=dane, timeout=timeout)
        except httpx.TransportError:
            if pauza is None:
                raise
            time.sleep(pauza)
            continue
        if (r.status_code == 429 or r.status_code >= 500) and pauza is not None:
            time.sleep(pauza)
            continue
        return r
    return r
