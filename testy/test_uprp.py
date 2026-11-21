"""Biuletyn Urzędu Patentowego: PDF numeru w dwóch kolumnach → zgłoszenia, bez twórców (72) i bez osób fizycznych."""
from radar.zrodla import uprp


def _strona(lewa, prawa, szer=72):
    n = max(len(lewa), len(prawa))
    lewa, prawa = lewa + [""] * (n - len(lewa)), prawa + [""] * (n - len(prawa))
    return "\n".join((l.ljust(szer) + p).rstrip() for l, p in zip(lewa, prawa))


STRONA1 = _strona([
    "A1 (21) 449092 (22) 2024 07 01",
    "(51) A61K 31/4425 (2006.01)",
    "     A61K 31/122 (2006.01)",
    "(71) UNIWERSYTET JAGIELLOŃSKI, Kraków",
    "(72) CHŁOPICKI STEFAN; BAR ANNA",
    "(54) Synergiczna kombinacja 1-metylonikotynamidu",
    "     (MNA) i witaminy K",
    "(57) Przedmiotem zgłoszenia jest kombinacja zawierają-",
    "ca MNA i witaminę K do stosowania w leczeniu.",
    "                                 (4 zastrzeżenia)",
    "",
    "U1 (21) 133001 (22) 2024 08 12",
    "(51) B65D 81/38 (2006.01)",
    "(71) KOWALSKI JAN, Rzeszów; FIRMA TESTOWA SP. Z O.O., Mielec",
    "(72) KOWALSKI JAN",
    "(54) Pojemnik termiczny",
], [
    "(57) Pojemnik ma ścianki z dwiema warstwami",
    "pianki i zawór wyrównujący ciśnienie.",
    "                    (1 zastrzeżenie)",
    "",
    "                    DZIAŁ B",
    "Różne procesy przemysłowe; transport",
    "A1 (21) 449103 (22) 2024 07 02",
    "(71) KOWALSKA ANNA, Lublin",
    "(72) KOWALSKA ANNA",
    "(54) Sposób otrzymywania katalizatora",
    "(57) Sposób polega na kalcynacji węgla.",
    "                    (2 zastrzeżenia)",
]) + "\nNr 1/2026                         BIULETYN URZĘDU PATENTOWEGO                                   7\n"
STRONA2 = _strona([
    "A1 (21) 449200 (22) 2025 01 15",
    "(71) POLITECHNIKA RZESZOWSKA IM. IGNACEGO ŁUKASIEWICZA, Rzeszów",
    "(72) NOWAK PIOTR",
    "(54) Czujnik wilgotności",
    "(57) Czujnik mierzy wilgotność gleby",
], [
    "w doniczce bez baterii.",
    "                    (3 zastrzeżenia)",
])
LINK = "https://uprp.gov.pl/sites/default/files/bup01_2026.pdf"


def test_parsuje_zgloszenia_w_kolejnosci_kolumn():
    docs = uprp.parsuj_tekst(STRONA1 + "\f" + STRONA2, link=LINK, numer="1/2026")
    assert [d.id for d in docs] == ["uprp:449092", "uprp:133001", "uprp:449103", "uprp:449200"]
    a, u, k, c = docs
    assert a.tytul == "Synergiczna kombinacja 1-metylonikotynamidu (MNA) i witaminy K"
    assert "kombinacja zawierająca MNA" in a.opis and "zastrzeż" not in a.opis
    assert a.opis.startswith("Zgłoszenie wynalazku P.449092 (BUP 1/2026).") and u.opis.startswith("Zgłoszenie wzoru użytkowego")
    assert u.tytul == "Pojemnik termiczny" and "zawór wyrównujący ciśnienie" in u.opis
    assert k.tytul == "Sposób otrzymywania katalizatora"
    assert "gleby w doniczce bez baterii" in c.opis
    assert all(d.typ == "patent" and d.status == "zgloszenie" and d.zrodlo == "uprp" and d.link == LINK for d in docs)
    assert a.rok == 2024 and c.rok == 2025
    assert not any("BIULETYN" in d.opis or "DZIAŁ" in d.opis for d in docs)


def test_bez_tworcow_i_osob_fizycznych():
    docs = uprp.parsuj_tekst(STRONA1 + "\f" + STRONA2, link=LINK, numer="1/2026")
    assert [d.instytucje for d in docs] == [["UNIWERSYTET JAGIELLOŃSKI"], ["FIRMA TESTOWA SP. Z O.O."], [],
                                             ["POLITECHNIKA RZESZOWSKA IM. IGNACEGO ŁUKASIEWICZA"]]
    tekst = " ".join(d.tytul + d.opis + " ".join(d.instytucje) for d in docs)
    assert not any(osoba in tekst for osoba in ("CHŁOPICKI", "KOWALSK", "NOWAK", "BAR ANNA"))


def test_nazwa_zagranicznego_zglaszajacego_bez_miasta_i_kraju():
    assert uprp._instytucje("BSH Hausgeräte GmbH, Monachium, DE; POLITECHNIKA GDAŃSKA, Gdańsk") == [
        "BSH Hausgeräte GmbH", "POLITECHNIKA GDAŃSKA"]


def test_wybiera_najnowsze_numery():
    html = " ".join(f'<a href="/sites/default/files/{p}">x</a>' for p in
                    ["2021-06/bup23_1999.pdf", "2022-02/bup07_2022_1.pdf", "bup/2025/W/11/47/bup47_2025.pdf",
                     "2026-01/bup01_2026.pdf", "bup/2026/W/02/bup02_2026.pdf", "2026-01/wup01_2026.pdf"])
    assert uprp.linki_numerow(html, ile=2) == [("1/2026", "https://uprp.gov.pl/sites/default/files/2026-01/bup01_2026.pdf"),
                                               ("2/2026", "https://uprp.gov.pl/sites/default/files/bup/2026/W/02/bup02_2026.pdf")]
