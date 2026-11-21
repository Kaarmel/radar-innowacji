import pytest
from fastapi.testclient import TestClient

from radar import app as A
from radar import config, db, siec
from radar.model import WynikFiltra, Zgloszenie

OPIS = ("Uczniowie technikum zbudowali filtr wody inspirowany skrzelami ryb. Urządzenie zatrzymuje drobiny mikroplastiku "
        "bez użycia wymiennych wkładów. Prototyp przetestowano w szkolnym laboratorium na próbkach z pobliskiej rzeki. "
        "Konstrukcja składa się z pochylonych blaszek kierujących cząstki do komory osadowej, dzięki czemu filtr się nie zatyka.")
POLA = dict(tytul="Filtr mikroplastiku", opis=OPIS, link="", instytucja="Zespół Szkół Technicznych w Jaśle",
            typ_instytucji="szkola_ponadpodstawowa", typ_innowacji="techniczna", etap="prototyp", wiek_przedzial="16_30",
            organizacja="pci")


def _udawane_sprawdzenie(con, zid):
    db.zapisz_ocene(con, zid, {"wynik": 71, "kryteria": [{"id": "dojrzalosc", "nazwa": "Dojrzałość (etap)", "max": 15, "punkty": 9.0,
                                                         "zrodlo": "formularz", "uzasadnienie": "Etap prototyp", "dowody": []}],
                               "uwaga": "", "formula": "wzór"})
    db.zapisz_wyniki(con, zid, [WynikFiltra("plagiat", 0.0, "zielone", []),
                                WynikFiltra("kopia", 45.0, "zolte", [{"dokument_id": "x", "tytul": "Inny", "link": "javascript:alert(1)",
                                                                       "podobienstwo": 45.0, "zrodlo": "radon"},
                                                                      {"dokument_id": "zgloszenie:1", "tytul": "Własne", "link": "/karta/1",
                                                                       "podobienstwo": 41.0, "zrodlo": "zgloszenie"}]),
                                WynikFiltra("patent", None, "brak_danych", []),
                                WynikFiltra("nowosc", 80.0, "zielone", [])],
                     "do_przegladu", "mlodzi_16_30", [], [], 1.0, 0.001, pokrycie={"zrodla": ["radon"], "dokumentow": 10, "niedostepne": ["epo"]})
    return db.karta(con, zid)


@pytest.fixture
def klient(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BAZA", tmp_path / "t.sqlite")
    monkeypatch.setattr(A, "sprawdz", _udawane_sprawdzenie)
    A.limiter.wyczysc()
    return TestClient(A.app)


def _liczba(tmp=None):
    con = db.polacz()
    return con.execute("SELECT count(*) FROM zgloszenie").fetchone()[0]


def test_krotki_opis_422_bez_zapisu(klient):
    r = klient.post("/zglos", data={**POLA, "opis": "Za krótki opis tekstu"})
    assert r.status_code == 422 and "opis" in r.text.lower()
    assert _liczba() == 0


def test_link_nie_http_odrzucony(klient):
    r = klient.post("/zglos", data={**POLA, "link": "javascript:alert(1)"})
    assert r.status_code == 422 and _liczba() == 0


def test_script_w_tytule_escapowany(klient):
    r = klient.post("/zglos", data={**POLA, "tytul": "<script>alert(1)</script> Filtr"})
    assert r.status_code == 200 and "/karta/" in str(r.url)
    assert "&lt;script&gt;" in r.text and "<script>alert(1)" not in r.text


def test_link_javascript_bez_href_a_wlasny_z_href(klient):
    r = klient.post("/zglos", data=POLA)
    assert 'href="javascript:' not in r.text
    assert 'href="/karta/1"' in r.text


def test_limit_ip(klient, monkeypatch):
    monkeypatch.setattr(A, "LIMIT_IP_GODZ", 5)
    kody = [klient.post("/zglos", data=POLA, headers={"X-Forwarded-For": f"10.0.0.{i}"}, follow_redirects=False).status_code
            for i in range(6)]
    assert kody[:5] == [303] * 5 and kody[5] == 429


def test_api_karta(klient):
    r = klient.post("/api/zgloszenia", json=POLA)
    assert r.status_code == 202
    k = klient.get(f"/api/karta/{r.json()['id']}").json()
    assert {"wyniki", "werdykt", "komorka", "rekomendacje", "partnerzy", "pokrycie"} <= set(k)


def test_api_walidacja_422(klient):
    assert klient.post("/api/zgloszenia", json={**POLA, "typ_innowacji": "magiczna"}).status_code == 422


def test_kolejka_organizacji_i_katalog(klient):
    klient.post("/zglos", data=POLA)
    klient.post("/zglos", data={**POLA, "organizacja": "ogolny", "tytul": "Inne zgłoszenie"})
    pci = klient.get("/o/pci/kolejka").text
    assert "Filtr mikroplastiku" in pci and "Inne zgłoszenie" not in pci
    assert "Inne zgłoszenie" in klient.get("/kolejka").text
    assert klient.get("/o/nie-ma/kolejka").status_code == 404


def test_szukaj_zwraca_zgloszenie_pierwsze(klient):
    klient.post("/zglos", data=POLA)
    klient.post("/zglos", data={**POLA, "tytul": "Rejestr awarii oświetlenia", "opis": "Gmina uruchomiła rejestr awarii oświetlenia "
                                "ulicznego z mapą i automatycznym przydziałem ekip serwisowych. " * 5})
    wyn = klient.get("/api/szukaj", params={"q": "Rejestr awarii oświetlenia"}).json()
    assert wyn["zgloszenia"][0]["tytul"] == "Rejestr awarii oświetlenia"
    assert klient.get("/szukaj", params={"q": "filtr mikroplastiku"}).status_code == 200


def test_decyzja_zapisana(klient):
    klient.post("/zglos", data=POLA)
    r = klient.post("/karta/1/decyzja", data={"decyzja": "przywroc", "powod": "Kopia dotyczy innego zastosowania"})
    assert r.status_code == 200 and "Kopia dotyczy innego zastosowania" in r.text
    assert klient.post("/karta/1/decyzja", data={"decyzja": "usun", "powod": "x"}).status_code == 422


def test_przerwane_sprawdzenie_oznaczone(klient):
    con = db.polacz()
    zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="formularz", tytul="T", opis="O", link=None, instytucja="I",
                                               typ_instytucji="firma", typ_innowacji="techniczna", etap="pomysl",
                                               wiek_przedzial="powyzej_30"))
    db.ustaw_status(con, zid, "w_toku")
    A.napraw_przerwane(con)
    assert db.karta(con, zid)["status"] == "blad"


def test_strony_dzialaja(klient):
    for u in ["/", "/zglos", "/kolejka", "/o/pci/kolejka", "/miary", "/szukaj", "/docs"]:
        assert klient.get(u).status_code == 200, u


@pytest.mark.parametrize("url,ok", [
    ("http://169.254.169.254/latest/meta-data", False), ("http://127.0.0.1:8000/", False), ("http://10.1.2.3/", False),
    ("http://[::1]/", False), ("ftp://8.8.8.8/", False), ("http://8.8.8.8:22/", False), ("https://8.8.8.8/", True),
])
def test_adres_publiczny(url, ok):
    assert siec.adres_publiczny(url) is ok


def test_ocena_potencjalu_na_karcie_i_w_kolejce(klient):
    r = klient.post("/zglos", data=POLA)
    assert "Ocena potencjału" in r.text and "71" in r.text and "Dojrzałość (etap)" in r.text
    assert "71" in klient.get("/o/pci/kolejka").text


def test_ocen_projekt_z_bazy(klient):
    from radar.model import Dokument
    con = db.polacz()
    db.zapisz_dokumenty(con, [Dokument(id="radon:abc", zrodlo="radon", typ="projekt", tytul="Projekt z bazy RAD-on",
                                       opis=OPIS, link="https://radon.nauka.gov.pl/x", instytucje=["Politechnika Rzeszowska"])])
    f = klient.get("/zglos", params={"z_dokumentu": "radon:abc"}).text
    assert "Projekt z bazy RAD-on" in f and 'value="radon:abc"' in f and "Politechnika Rzeszowska" in f
    r = klient.post("/zglos", data={**POLA, "zrodlo_dok": "radon:abc"}, follow_redirects=False)
    zid = int(r.headers["location"].rsplit("/", 1)[1])
    k = db.karta(db.polacz(), zid)
    assert k["wejscie"] == "baza" and k["zrodlo_dok"] == "radon:abc"
    assert "Oceń ten projekt" in klient.get("/szukaj", params={"q": "filtr mikroplastiku skrzela"}).text
