"""Grzeczne pobieranie: robots.txt per host, 1 zapytanie/s na host, identyfikujący User-Agent, ponowienia."""
import ipaddress
import socket
import threading
import time
import urllib.robotparser
from urllib.parse import urljoin, urlsplit

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


# --- Pobieranie adresu podanego przez użytkownika (formularz „z linku”): ochrona przed SSRF ---
_klient_publiczny = httpx.Client(headers={"User-Agent": config.USER_AGENT}, follow_redirects=False, timeout=20, verify=True)


def adres_publiczny(url: str) -> bool:
    """Tylko http(s), porty 80/443 i adresy publiczne (bez sieci prywatnych, loopback, link-local, metadanych chmury)."""
    try:
        cz = urlsplit(url)
        port = cz.port
    except ValueError:
        return False
    if cz.scheme not in ("http", "https") or not cz.hostname or port not in (None, 80, 443):
        return False
    try:
        adresy = socket.getaddrinfo(cz.hostname, port or (443 if cz.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return False
    for *_, adr in adresy:
        ip = ipaddress.ip_address(adr[0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return False
    return bool(adresy)


def pobierz_publiczna(url: str, max_bajtow: int = 2_000_000) -> tuple[str, str]:
    """Strona HTML spod adresu użytkownika: (adres końcowy, treść). Każde przekierowanie sprawdzane osobno."""
    for _ in range(4):
        if not adres_publiczny(url):
            raise ValueError("Adres niedozwolony: tylko publiczne strony http(s).")
        if not _dozwolone(url):
            raise Zablokowane(url)
        _czekaj(urlsplit(url).netloc)
        with _klient_publiczny.stream("GET", url) as r:
            if r.is_redirect:
                url = urljoin(url, r.headers.get("location", ""))
                continue
            r.raise_for_status()
            typ = r.headers.get("content-type", "")
            if "html" not in typ and "text" not in typ:
                raise ValueError("Pod tym adresem nie ma strony HTML.")
            dane = b""
            for kawalek in r.iter_bytes():
                dane += kawalek
                if len(dane) > max_bajtow:
                    break
            return url, dane[:max_bajtow].decode(r.encoding or "utf-8", errors="replace")
    raise ValueError("Za dużo przekierowań.")
