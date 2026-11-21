"""Radar WWW: kanały RSS/Atom szkół, uczelni i instytucji Podkarpacia. Lejek: wpisy z ostatnich dni → sygnał słów
(kod) → AI potwierdza, że to nowe rozwiązanie (z cytatem) → karta → zgłoszenie z wejściem „radar” → pełna ocena."""
import csv
import datetime
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from .. import ai, config, db, siec
from ..model import Zgloszenie
from ..sprawdz import sprawdz
from ..tekst import bez_diakrytykow, bez_html

ZRODLA = config.KONFIGURACJA / "zrodla_www.csv"
STATYSTYKI = config.DANE / "radar_statystyki.json"
PLUS2 = re.compile(r"zbudowal|skonstruowal|zaprojektowal|stworzyl|opracowal|wynalaz|prototyp|aplikacj|robot|patent|innowac|autorsk|startup")
PLUS1 = re.compile(r"laureat|nagrod|finali|grant")
MINUS3 = re.compile(r"jadlospis|wycieczk|akademi[ai]? (?:z okazji|szkoln|swiateczn|pierwszomajow)|rekolekc|zebrani|dyzur")
PROG = 3
MAX_AI = 60          # bezpiecznik kosztu: tyle wpisów na uruchomienie może trafić do AI
TYPY = {"uczelnia": ("uczelnia", "mieszany"), "szkola_ponadpodstawowa": ("szkola_ponadpodstawowa", "16_30"),
        "jst": ("jst", "powyzej_30"), "instytucja": ("inna_publiczna", "mieszany")}


# Bez danych osobowych: z WWW zapisujemy instytucje, nie osoby (uczniowie bywają niepełnoletni).
IMIONA = set("""adam adrian agata agnieszka aleksander aleksandra alicja amelia anna antoni antonina artur barbara bartosz beata
bogdan dariusz dawid dominik dominika dorota edyta elżbieta emilia ewa filip franciszek gabriela grzegorz hanna helena
henryk igor iwona jacek jakub jan janina janusz jerzy joanna jolanta julia julian justyna kacper kamil kamila karol karolina
katarzyna kinga krystyna krzysztof laura lena leon magdalena maja maciej małgorzata marcin marek maria marian mariusz marta
martyna mateusz michał mikołaj milena monika natalia nikola nikodem oliwer oliwia patryk paulina paweł piotr przemysław
rafał renata robert roksana ryszard sebastian stanisław szymon sylwia tadeusz teresa tomasz urszula weronika wiktor wiktoria
witold wojciech zbigniew zofia zuzanna łukasz""".split())
INSTYTUCJE = set("""politechnika politechniki uniwersytet uniwersytetu akademia akademii szkoła szkoły szkół zespół zespołu gmina gminy
powiat powiatu województwo województwa urząd urzędu centrum instytut instytutu fundacja fundacji stowarzyszenie miasto miasta
liceum technikum ochotnicza państwowa wyższa wyższej podkarpackie podkarpackiego podkarpacka""".split())
_SLOWO = r"[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+"
_NAZWISKO = re.compile(r"(?:ski|ska|skiego|skiej|skim|ską|cki|cka|ckiego|ckiej|dzki|dzka|ński|ńska|ńskiego|ńskiej|wicz|wicza|owicz|"
                       r"ak|aka|akiem|ek|ka|czyk|czyka|uk|uka|yk|yka|ik|ika|ło|ła|łą)$")


def _imie(w: str) -> bool:
    w = w.lower()
    return w in IMIONA or any(w.endswith(e) and (w[: -len(e)] in IMIONA or w[: -len(e)] + "a" in IMIONA)
                              for e in ("a", "y", "i", "owi", "em", "ie", "ą", "ę", "u"))


def bez_osob(tekst: str) -> str:
    """Usuwa imiona i nazwiska (heurystyka: tytuł + nazwa, znane imię + słowo, dwa słowa z końcówką nazwiska)."""
    if not tekst:
        return tekst
    t = re.sub(rf"\b(?:p\.|pani|pana|pan|prof\.|dr|mgr|inż\.)\s+(?:{_SLOWO}\s+){{0,1}}{_SLOWO}", "[osoba]", tekst)

    def zamien(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        if a.lower() in INSTYTUCJE:
            return m.group(0)
        if _imie(a) or (_NAZWISKO.search(b) and not b.lower() in INSTYTUCJE):
            return "[osoba]"
        return m.group(0)
    t = re.sub(rf"\b({_SLOWO})\s+({_SLOWO})\b", zamien, t)
    return re.sub(r"\[osoba\](?:(?:,\s*|\s+i\s+)\[osoba\])+", "[osoby]", t)


def wstepny_sygnal(tekst: str) -> tuple[int, list[str]]:
    t = bez_diakrytykow(tekst or "").lower()
    plus2 = sorted(set(PLUS2.findall(t)))
    plus1 = sorted(set(PLUS1.findall(t)))
    minus = sorted(set(MINUS3.findall(t)))
    return 2 * len(plus2) + len(plus1) - 3 * len(minus), plus2 + plus1 + [f"-{m}" for m in minus]


def znajdz_kanal(html: str, url: str) -> str | None:
    for tag in re.findall(r"<link\b[^>]*>", html or "", re.I):
        if re.search(r"rel=[\"']?alternate", tag, re.I) and re.search(r"type=[\"']?application/(rss|atom)\+xml", tag, re.I):
            m = re.search(r"href=[\"']([^\"']+)", tag, re.I)
            if m:
                return urljoin(url, m.group(1))
    return None


def _data(s: str | None) -> datetime.datetime | None:
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s.strip())
    except (TypeError, ValueError):
        try:
            d = datetime.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def wpisy_z_kanalu(xml: str) -> list[dict]:
    """RSS 2.0 i Atom. XML z deklaracjami encji odrzucany (ochrona przed „billion laughs”)."""
    if not xml or "<!ENTITY" in xml.upper():
        return []
    xml = xml.lstrip("\ufeff \t\r\n")  # część stron szkół wysyła puste linie przed <?xml
    try:
        root = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except ET.ParseError:
        return []
    out = []
    for it in root.iter():
        nazwa = it.tag.rsplit("}", 1)[-1]
        if nazwa not in ("item", "entry"):
            continue
        pola = {c.tag.rsplit("}", 1)[-1]: c for c in it}
        link = (pola["link"].text or pola["link"].get("href") or "").strip() if "link" in pola else ""
        tekst = ""
        for k in ("encoded", "description", "content", "summary"):
            if k in pola and (pola[k].text or "").strip():
                tekst = bez_html(pola[k].text)
                break
        el_daty = next((pola[k] for k in ("pubDate", "updated", "published", "date") if k in pola), None)  # Element bez dzieci jest „fałszywy”
        data = _data(el_daty.text if el_daty is not None else None)
        tytul = bez_html((pola["title"].text or "") if "title" in pola else "")
        if tytul and link:
            out.append({"tytul": tytul, "link": link, "data": data, "tekst": tekst})
    return out


def _widziane(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS radar_widziane(link TEXT PRIMARY KEY, sygnal INTEGER, ai TEXT, kiedy REAL)")


def przetworz_wpisy(con: sqlite3.Connection, zrodlo: dict, wpisy: list[dict], dni: int = 180, organizacja: str = "pci",
                    stat: dict | None = None) -> int:
    stat = stat if stat is not None else {}
    _widziane(con)
    granica = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=dni)
    nowe = 0
    for w in wpisy:
        if w["data"] and w["data"] < granica:
            continue
        stat["wpisow"] = stat.get("wpisow", 0) + 1
        if con.execute("SELECT 1 FROM radar_widziane WHERE link=?", (w["link"],)).fetchone() or \
                con.execute("SELECT 1 FROM zgloszenie WHERE link=?", (w["link"],)).fetchone():
            continue
        sygnal, slowa = wstepny_sygnal(f"{w['tytul']} {w['tekst']}")
        if sygnal < PROG:
            with con:
                con.execute("INSERT OR REPLACE INTO radar_widziane VALUES(?,?,?,?)", (w["link"], sygnal, None, time.time()))
            continue
        if stat.get("do_ai", 0) >= MAX_AI:
            stat["poza_limitem"] = stat.get("poza_limitem", 0) + 1  # bez wyroku: wróci w następnym przebiegu
            continue
        stat["sygnal"] = stat.get("sygnal", 0) + 1
        stat["do_ai"] = stat.get("do_ai", 0) + 1
        ocena, _ = ai.czy_innowacja(w["tytul"], w["tekst"])
        if ocena["czy"] == "niepewne":
            continue  # np. awaria AI albo brak klucza: bez wyroku, wróci w następnym przebiegu
        with con:
            con.execute("INSERT OR REPLACE INTO radar_widziane VALUES(?,?,?,?)", (w["link"], sygnal, ocena["czy"], time.time()))
        if ocena["czy"] != "tak":
            continue
        stat["innowacje"] = stat.get("innowacje", 0) + 1
        karta, _ = ai.karta_z_tekstu(w["tytul"], w["tekst"])
        typ_inst, wiek = TYPY.get(zrodlo.get("typ", ""), ("inna_publiczna", "mieszany"))
        # tylko streszczenie AI (polecenie: bez nazwisk) przepuszczone przez bez_osob; surowy tekst zostaje na stronie źródła
        opis = bez_osob((karta.get("opis") or karta.get("co") or w["tytul"]).strip())[:1500]
        zid = db.zapisz_zgloszenie(con, Zgloszenie(
            id=None, wejscie="radar", tytul=bez_osob(w["tytul"])[:200], opis=opis, link=w["link"], instytucja=zrodlo["nazwa"],
            typ_instytucji=typ_inst, typ_innowacji=karta.get("typ_innowacji") or "techniczna",
            etap=karta.get("etap") or "pomysl", wiek_przedzial=wiek, cytat=bez_osob(karta.get("cytat") or ocena.get("cytat") or "") or None,
            organizacja=organizacja))
        nowe += 1
        try:
            sprawdz(con, zid)
        except Exception as e:  # jedno nieudane sprawdzenie nie zatrzymuje radaru; karta ma status „blad”
            stat.setdefault("bledy", []).append(f"{w['link']}: {type(e).__name__}")
    stat["zgloszen"] = stat.get("zgloszen", 0) + nowe
    return nowe


def _kanal(zrodlo: dict) -> str | None:
    if zrodlo.get("kanal"):
        return zrodlo["kanal"]
    url = zrodlo["url"]
    try:
        r = siec.pobierz(url, timeout=20)
        k = znajdz_kanal(r.text, str(r.url)) if r.status_code == 200 else None
        if k:
            return k
        for sciezka in ("feed", "rss"):
            r = siec.pobierz(urljoin(url if url.endswith("/") else url + "/", sciezka), timeout=20)
            if r.status_code == 200 and "<rss" in r.text[:2000] or (r.status_code == 200 and "<feed" in r.text[:2000]):
                return str(r.url)
    except Exception:
        return None
    return None


def uruchom(con: sqlite3.Connection, limit_zrodel: int = 300, dni: int = 180, organizacja: str = "pci", log=print) -> dict:
    with open(ZRODLA, encoding="utf-8") as f:
        zrodla = list(csv.DictReader(f))[:limit_zrodel]
    stat: dict = {"start": time.time(), "zrodel": len(zrodla), "kanalow": 0}
    for i, z in enumerate(zrodla, 1):
        kanal = _kanal(z)
        if not kanal:
            continue
        try:
            r = siec.pobierz(kanal, timeout=30)
            wpisy = wpisy_z_kanalu(r.text) if r.status_code == 200 else []
        except Exception:
            continue
        stat["kanalow"] += 1
        try:
            przetworz_wpisy(con, z, wpisy, dni=dni, organizacja=organizacja, stat=stat)
        except Exception as e:  # jedno źródło nie zatrzymuje przebiegu
            stat.setdefault("bledy", []).append(f"{z.get('url')}: {type(e).__name__}")
        if i % 10 == 0:
            log(f"radar: {i}/{len(zrodla)} źródeł, {json.dumps({k: v for k, v in stat.items() if k != 'bledy'})}")
    stat["koniec"] = time.time()
    config.DANE.mkdir(parents=True, exist_ok=True)
    STATYSTYKI.write_text(json.dumps(stat, ensure_ascii=False, indent=1), encoding="utf-8")
    return stat
