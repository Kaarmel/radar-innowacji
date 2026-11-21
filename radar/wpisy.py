"""Pobiera wpisy (aktualności) ze źródeł wykrytych przez zrodla.py → dane/wpisy.jsonl

Użycie:  python3 radar/wpisy.py dane/zrodla.csv dane/wpisy.jsonl [maks_na_zrodlo=20]
RSS: tytuł, data, link z kanału. Podstrona aktualności: linki do artykułów (ta sama domena, tytuł ≥ 25 znaków).
Tekst każdego artykułu pobieramy z jego strony (akapity <p>). Wznawialne: pomija linki już zapisane.
Uwaga: wpisy szkół zawierają imiona uczniów; to surowy tekst lokalnie, karty inicjatyw nie przenoszą nazwisk.
"""
import csv
import datetime as dt
import email.utils
import json
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape
from html.parser import HTMLParser

from zrodla import Linki, ostatnie_zrodla, pobierz

MIESIACE = {m: i for i, m in enumerate("stycznia lutego marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia".split(), 1)}
DATA_SLOWNIE = re.compile(r"\b(\d{1,2}) (" + "|".join(MIESIACE) + r") (20\d\d)\b", re.I)
DATA = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b|\b(\d{1,2})[./](\d{1,2})[./](20\d\d)\b")
POMIN = re.compile(r"((?<![a-z])(kontakt|polityka|cookie|deklaracja|rodo|logowanie|mapa-strony)|galeria$|/tag/|/category/|/kategoria/|\.(pdf|jpe?g|png|docx?)$)", re.I)


class Tekst(HTMLParser):
    """Zbiera akapity <p> (bez skryptów, nawigacji, nagłówka, stopki, paska bocznego) i kandydatów na datę publikacji:
    meta article:published_time / itemprop datePublished, <time datetime>, krótkie elementy z samą datą („21.11.2026”)."""
    BEZ_TEKSTU = ("script", "style", "nav", "footer", "header", "aside")
    BEZ_DATY = ("script", "style", "nav", "footer", "aside")  # data artykułu bywa w jego <header>

    def __init__(self):
        super().__init__()
        self.akapity, self._p = [], None
        self.daty = {"meta": [], "time": [], "strona": []}
        self._ile = Counter()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.BEZ_TEKSTU:
            self._ile[tag] += 1
        elif tag == "p" and not self._w(self.BEZ_TEKSTU):
            self._p = ""
        if tag == "meta" and (a.get("property") == "article:published_time" or a.get("itemprop") == "datePublished"):
            self.daty["meta"].append((a.get("content") or "")[:10])
        elif tag == "time" and a.get("datetime") and not self._w(self.BEZ_DATY):
            self.daty["time"].append(a["datetime"][:10])

    def handle_endtag(self, tag):
        if tag in self.BEZ_TEKSTU:
            self._ile[tag] = max(0, self._ile[tag] - 1)
        elif tag == "p" and self._p is not None:
            t = re.sub(r"\s+", " ", self._p).strip()
            if len(t) >= 40:
                self.akapity.append(t)
            self._p = None

    def handle_data(self, data):
        if self._p is not None:
            self._p += data
        t = data.strip()
        if 6 <= len(t) <= 40 and not self._w(self.BEZ_DATY):
            d = data_z(t)
            if d:
                self.daty["strona"].append(d)

    def _w(self, tagi):
        return any(self._ile[t] for t in tagi)


def data_z(tekst):
    m = DATA.search(tekst or "")
    if not m:
        s = DATA_SLOWNIE.search(tekst or "")
        return f"{s.group(3)}-{MIESIACE[s.group(2).lower()]:02d}-{int(s.group(1)):02d}" if s else ""
    if m.group(1):
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return f"{m.group(6)}-{int(m.group(5)):02d}-{int(m.group(4)):02d}"


def poprawna(d):
    """Data publikacji nie może być z przyszłości ani sprzed 2000 r. (to zwykle terminy wydarzeń)."""
    try:
        return dt.date(2000, 1, 1) <= dt.date.fromisoformat(d) <= dt.date.today()
    except (TypeError, ValueError):
        return False


def wybierz_date(kandydaci):
    """kandydaci: lista (źródło, data) od najpewniejszego; zwraca (data, źródło) pierwszej poprawnej."""
    return next(((d, z) for z, d in kandydaci if poprawna(d)), ("", ""))


def artykul(url):
    _, _, html = pobierz(url)
    p = Tekst()
    p.feed(html)
    kandydaci = [("meta", d) for d in re.findall(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)', html)]  # JSON-LD
    kandydaci += [(z, d) for z in ("meta", "time", "strona") for d in p.daty[z]]
    kandydaci += [("tekst", data_z(a)) for a in p.akapity[:3]]
    return p.akapity, kandydaci


def data_iso(d):
    """Data z RSS (RFC 822) albo ISO → RRRR-MM-DD."""
    try:
        return email.utils.parsedate_to_datetime(d).date().isoformat()
    except (TypeError, ValueError):
        return d[:10] if re.match(r"20\d\d-\d\d-\d\d", d or "") else ""


def czysty_tytul(t):
    """Usuwa z tytułu doklejki z listy wpisów: „czytaj dalej... na temat:”, „» ”, sklejone cyfry daty („2310Wielkie”)."""
    t = re.sub(r"^\s*(czytaj (dalej|więcej)\W*(na temat:)?|»)\s*", "", t, flags=re.I)
    return re.sub(r"^\d{3,4}(?=[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż])", "", t).strip()


def wspolna_data(wpisy):
    """≥ 3 wpisy jednego źródła z identyczną datą: to data szablonu (stopka, data kanału), nie publikacji → usuwamy."""
    if len(wpisy) >= 3 and len({w["data"] for w in wpisy}) == 1 and wpisy[0]["data"]:
        for w in wpisy:
            w["data"], w["data_zrodlo"] = "", "odrzucona: ta sama we wszystkich wpisach"
    return wpisy


def bez_szablonu(wpisy):
    """Usuwa akapity powtarzające się w ≥ 3 wpisach jednego źródła (stopki, „Lorem ipsum” z szablonu strony)."""
    ile = Counter(a for w in wpisy for a in set(w["akapity"]))
    for w in wpisy:
        w["tekst"] = " ".join(a for a in w.pop("akapity") if ile[a] < 3 and not a.startswith("Lorem ipsum"))[:20000]
        opis = w.pop("opis", "")
        if len(w["tekst"]) < 200 and len(opis) > len(w["tekst"]):
            w["tekst"] = opis[:20000]  # np. EduPage: link artykułu otwiera całą listę, pełna treść jest w opisie RSS
    return [w for w in wpisy if len(w["tekst"]) >= 200]


def z_rss(url):
    xml = pobierz(url)[2].lstrip()
    if "<!ENTITY" in xml:
        raise ValueError("kanał z deklaracją encji: pomijamy")  # obcy XML, bez ryzyka XXE / billion laughs
    root = ET.fromstring(xml.encode("utf-8"))
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        pole = {c.tag.split("}")[-1]: (c.text or c.get("href") or "") for c in it}
        yield {"tytul": unescape(pole.get("title", "")).strip(), "link": pole.get("link", "").strip(),
               "data": pole.get("pubDate") or pole.get("published") or pole.get("updated") or "",
               "opis": czysty(pole.get("description") or pole.get("content") or pole.get("summary") or "")}


def czysty(html):
    """HTML z opisu RSS → zwykły tekst."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def linki_artykulow(baza, linki):
    """Z linków podstrony aktualności wybiera artykuły: ta sama domena, tytuł ≥ 25 znaków, nie strona główna.
    Jeśli ≥ 3 linki leżą pod ścieżką podstrony aktualności (np. /aktualnosci/...), bierzemy tylko je."""
    host, sciezka = urllib.parse.urlparse(baza).netloc, urllib.parse.urlparse(baza).path.rstrip("/")
    wynik, widziane = [], set()
    for h, t in linki:
        u = urllib.parse.urljoin(baza, h or "").split("#")[0]
        pu = urllib.parse.urlparse(u)
        if (len(t) >= 25 and pu.netloc == host and pu.path.strip("/") and u.rstrip("/") != baza.rstrip("/")
                and not POMIN.search(u) and u not in widziane):
            widziane.add(u)
            wynik.append((u, re.sub(r"\s+", " ", t)))
    pod = [w for w in wynik if sciezka and urllib.parse.urlparse(w[0]).path.startswith(sciezka + "/")]
    return pod if len(pod) >= 3 else wynik


def z_aktualnosci(url):
    baza, _, html = pobierz(url)
    p, pelne = Linki(tylko_tresc=True, url=baza), Linki(url=baza)
    p.feed(html)
    pelne.feed(html)
    tytul = {}  # w treści link bywa „Czytaj więcej”, a tytuł jest linkiem w nagłówku karty: bierzemy najdłuższy tekst
    for h, t in pelne.a:
        t = re.sub(r"\s+", " ", t)
        if len(t) > len(tytul.get(h, "")):
            tytul[h] = t
    linki = [(h, tytul.get(h, t) if len(tytul.get(h, t)) >= 25 else (p.przed.get(h) or tytul.get(h, t))) for h, t in p.a]
    for u, t in linki_artykulow(baza, linki):
        yield {"tytul": t, "link": u, "data": ""}


def wpisy_zrodla(z, maks):
    """Kandydaci na wpisy: najpierw RSS, a gdy zawiedzie albo jest pusty, podstrona aktualności."""
    for rodzaj, url, fn in (("rss", z["rss"], z_rss), ("aktualnosci", z["aktualnosci"], z_aktualnosci)):
        if not url:
            continue
        try:
            k = [w for w in fn(url) if w["link"].startswith(("http://", "https://"))][:maks]
        except Exception as e:
            print(z["id"], rodzaj, "błąd:", type(e).__name__, flush=True)
            continue
        if k:
            return k
    return []


def main(we, wy, maks=20):
    maks = int(maks)
    juz = {json.loads(l)["link"] for l in open(wy, encoding="utf-8")} if os.path.exists(wy) else set()
    with open(wy, "a", encoding="utf-8") as f:
        for z in ostatnie_zrodla(we).values():
            if z["status"] != "ok" or not (z["rss"] or z["aktualnosci"]):
                continue
            nowe = []
            for w in wpisy_zrodla(z, maks):
                if w["link"] in juz:
                    continue
                time.sleep(1)
                try:
                    akapity, daty = artykul(w["link"])
                except Exception:
                    continue
                data, skad = wybierz_date([("rss", data_iso(w["data"]))] + daty)
                nowe.append({"zrodlo_id": z["id"], "www": z["www"], **w, "data": data, "data_zrodlo": skad, "akapity": akapity})
            nowe = wspolna_data(bez_szablonu(nowe))  # krótkie = strona listy, galeria albo pusty wpis
            for w in nowe:
                w["tytul"] = czysty_tytul(w["tytul"])
            for w in nowe:
                f.write(json.dumps(w, ensure_ascii=False) + "\n")
                juz.add(w["link"])
            f.flush()
            print(z["id"], z["www"], "wpisów:", len(nowe), flush=True)


if __name__ == "__main__":
    assert czysty_tytul("czytaj dalej... na temat: Akademia z okazji") == "Akademia z okazji"
    assert czysty_tytul("» Regulamin klas") == "Regulamin klas" and czysty_tytul("2310Wielkie serca") == "Wielkie serca"
    assert czysty_tytul("1000 Gwiazd") == "1000 Gwiazd" and czysty_tytul("XX Konkurs") == "XX Konkurs"
    d = wspolna_data([{"data": "2026-11-06", "data_zrodlo": "strona"} for _ in range(3)])
    assert d[0]["data"] == "" and wspolna_data([{"data": "2026-11-06", "data_zrodlo": "rss"}, {"data": "2026-11-05", "data_zrodlo": "rss"}, {"data": "2026-11-06", "data_zrodlo": "rss"}])[0]["data"] == "2026-11-06"
    e = [{"akapity": ["Cała lista aktualności szkoły, ten sam tekst w każdym wpisie i bez treści artykułu."], "opis": "Uczniowie zbudowali stację. " * 10} for _ in range(3)]
    e = bez_szablonu(e)
    assert len(e) == 3 and all(w["tekst"].startswith("Uczniowie") and "opis" not in w for w in e)
    assert czysty("<p>A&amp;B</p>\n<br/>C") == "A&B C"
    t = Tekst()
    t.feed("<nav><p>" + "menu " * 20 + "</p></nav><p>" + "Uczniowie zbudowali stację pogodową. " * 2 + "</p><time datetime='2026-10-05T10:00'>")
    assert len(t.akapity) == 1 and t.daty["time"] == ["2026-10-05"]
    assert data_z("Dodano 5.10.2026 r.") == "2026-10-05" and data_z("2026-11-01") == "2026-11-01"
    assert data_z("W dniu 4 listopada 2026 r. odbyły się") == "2026-11-04"
    L = [("/", "Strona główna naszej szkoły podstawowej")] + [(f"/aktualnosci/wpis-{i}", f"Uczniowie zbudowali robota numer {i}") for i in range(3)] + [("/kierunki/technik-informatyk", "Technik informatyk – opis kierunku")]
    assert [u for u, _ in linki_artykulow("https://s.pl/aktualnosci", L)] == [f"https://s.pl/aktualnosci/wpis-{i}" for i in range(3)]
    t = Tekst()
    t.feed('<aside><span>01.01.2026</span></aside><header><span class="small">21.11.2026</span></header><p>' + "x" * 50 + " termin do 30.09.2099 r.</p>")
    assert t.daty["strona"] == ["2026-11-21"] and wybierz_date([("rss", ""), ("tekst", "2099-09-30"), ("strona", "2026-11-21")]) == ("2026-11-21", "strona")
    z = {"id": "1", "rss": "x", "aktualnosci": "y"}
    oryginalne = z_rss, z_aktualnosci
    globals()["z_rss"] = lambda u: iter([])  # pusty RSS → przejście na aktualności
    globals()["z_aktualnosci"] = lambda u: iter([{"tytul": "t", "link": "https://s.pl/a", "data": ""}, {"tytul": "t", "link": "javascript:x", "data": ""}])
    assert [w["link"] for w in wpisy_zrodla(z, 10)] == ["https://s.pl/a"]
    z_rss, z_aktualnosci = oryginalne  # przywrócenie prawdziwych funkcji przed main()
    assert data_iso("Wed, 04 Nov 2026 10:00:00 +0000") == "2026-11-04" and data_iso("") == ""
    b = bez_szablonu([{"akapity": ["stopka " * 10, f"treść {i} " * 40]} for i in range(3)])
    assert len(b) == 3 and "stopka" not in b[0]["tekst"]
    main(*sys.argv[1:4])
