from radar.zrodla import www

HTML = """<html><head><link rel="alternate" type="application/rss+xml" title="Aktualności" href="/aktualnosci/feed/">
</head><body>x</body></html>"""
RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>Szkoła</title>
<item><title>Uczniowie zbudowali robota</title><link>https://szkola.pl/robot</link><pubDate>Mon, 16 Nov 2026 10:00:00 +0100</pubDate>
<description><![CDATA[<p>Nasi uczniowie skonstruowali robota sortującego odpady. Laureaci konkursu.</p>]]></description></item>
<item><title>Jadłospis</title><link>https://szkola.pl/jadlospis</link><pubDate>Mon, 16 Nov 2026 10:00:00 +0100</pubDate>
<description>Zupa</description></item></channel></rss>"""
ATOM = """<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>U</title>
<entry><title>Prototyp drona</title><link href="https://u.pl/dron"/><updated>2026-11-10T10:00:00Z</updated><summary>Opracowali prototyp</summary></entry></feed>"""


def test_znajdz_kanal():
    assert www.znajdz_kanal(HTML, "https://szkola.pl/") == "https://szkola.pl/aktualnosci/feed/"
    assert www.znajdz_kanal("<html></html>", "https://szkola.pl/") is None


def test_wpisy_rss_i_atom():
    w = www.wpisy_z_kanalu(RSS)
    assert w[0]["tytul"] == "Uczniowie zbudowali robota" and w[0]["link"] == "https://szkola.pl/robot"
    assert "robota sortującego" in w[0]["tekst"] and "<p>" not in w[0]["tekst"] and w[0]["data"].year == 2026
    assert www.wpisy_z_kanalu(ATOM)[0]["link"] == "https://u.pl/dron"


def test_entity_odrzucone():
    zly = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "y">]><rss><channel><item><title>&x;</title></item></channel></rss>'
    assert www.wpisy_z_kanalu(zly) == []


def test_wstepny_sygnal():
    assert www.wstepny_sygnal("Uczniowie zbudowali robota, laureaci konkursu")[0] >= 3
    assert www.wstepny_sygnal("Jadłospis na tydzień")[0] < 0
    assert www.wstepny_sygnal("Zebranie z rodzicami w czwartek")[0] < 3


def test_link_juz_byl_nie_tworzy_drugiego_zgloszenia(tmp_path, monkeypatch):
    from radar import ai, db
    con = db.polacz(tmp_path / "t.sqlite")
    monkeypatch.setattr(ai, "czy_innowacja", lambda t, x: ({"czy": "tak", "cytat": None}, 0.0))
    monkeypatch.setattr(ai, "karta_z_tekstu", lambda t, x: ({"co": "Robot sortujący odpady zbudowany przez uczniów.", "instytucja": "",
                                                            "typ_innowacji": "techniczna", "etap": "prototyp", "cytat": None}, 0.0))
    sprawdzone = []
    monkeypatch.setattr(www, "sprawdz", lambda c, zid: sprawdzone.append(zid))
    zrodlo = {"nazwa": "ZST", "typ": "szkola_ponadpodstawowa", "url": "https://szkola.pl/", "kanal": "https://szkola.pl/feed"}
    for _ in range(2):
        www.przetworz_wpisy(con, zrodlo, www.wpisy_z_kanalu(RSS), dni=100000)
    assert len(sprawdzone) == 1
    z = db.zgloszenie(con, sprawdzone[0])
    assert z.wejscie == "radar" and z.link == "https://szkola.pl/robot" and z.instytucja == "ZST" and z.wiek_przedzial == "16_30"


def test_kanal_ze_spacjami_przed_deklaracja():
    assert www.wpisy_z_kanalu("\n  " + RSS)[0]["link"] == "https://szkola.pl/robot"


def test_bez_osob_usuwa_imiona_i_nazwiska():
    t = www.bez_osob("Projekt przygotowali Jan Kowalski i Anna Nowak pod opieką p. Marka Wiśniewskiego z Zespołu Szkół Technicznych.")
    assert "Kowalski" not in t and "Nowak" not in t and "Wiśniewskiego" not in t
    assert "Zespołu Szkół Technicznych" in t


def test_radar_nie_zapisuje_surowego_tekstu(tmp_path, monkeypatch):
    from radar import ai, db
    con = db.polacz(tmp_path / "t.sqlite")
    monkeypatch.setattr(ai, "czy_innowacja", lambda t, x: ({"czy": "tak", "cytat": "zbudowali robota, Jan Kowalski"}, 0.0))
    monkeypatch.setattr(ai, "karta_z_tekstu", lambda t, x: ({"co": "Robot sortujący odpady.", "opis": "Uczniowie (Jan Kowalski) zbudowali robota sortującego odpady.",
                                                            "instytucja": "", "typ_innowacji": "techniczna", "etap": "prototyp",
                                                            "cytat": "Jan Kowalski zbudował robota"}, 0.0))
    monkeypatch.setattr(www, "sprawdz", lambda c, zid: None)
    wpis = {"tytul": "Robot", "link": "https://szkola.pl/r", "data": None,
            "tekst": "Jan Kowalski i Anna Nowak z klasy 3B zbudowali robota sortującego odpady. Opiekun: Piotr Zieliński. " * 3}
    www.przetworz_wpisy(con, {"nazwa": "ZST", "typ": "szkola_ponadpodstawowa", "url": "https://szkola.pl/"}, [wpis])
    z = db.zgloszenie(con, 1)
    calosc = f"{z.opis} {z.cytat or ''}"
    assert "Kowalski" not in calosc and "Nowak" not in calosc and "Zieliński" not in calosc
    assert "robota sortującego" in z.opis and len(z.opis) < 600


def test_nieocenione_wpisy_wracaja_w_nastepnym_przebiegu(tmp_path, monkeypatch):
    from radar import ai, db
    con = db.polacz(tmp_path / "t.sqlite")
    monkeypatch.setattr(ai, "czy_innowacja", lambda t, x: ({"czy": "niepewne", "cytat": None}, 0.0))
    monkeypatch.setattr(www, "MAX_AI", 1)
    wpisy = [{"tytul": f"Uczniowie zbudowali robota {i}", "link": f"https://s.pl/{i}", "data": None,
              "tekst": "Uczniowie zbudowali robota i aplikację, prototyp działa."} for i in range(3)]
    www.przetworz_wpisy(con, {"nazwa": "ZST", "typ": "szkola_ponadpodstawowa", "url": "https://s.pl/"}, wpisy)
    zapisane = {r[0] for r in con.execute("SELECT link FROM radar_widziane")}
    assert zapisane == set()  # „niepewne” (np. awaria AI) i ponad limit: bez wyroku, wrócą w następnym przebiegu
