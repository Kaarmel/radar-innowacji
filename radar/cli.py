"""Polecenia: python -m radar.cli pobierz <mapadotacji|interreg|radon> | sprawdz <id> | radar | zestaw | raport"""
import argparse
import sys
import time

from . import db


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("pobierz")
    pp.add_argument("zrodlo", choices=["mapadotacji", "interreg", "radon", "radon_patenty", "uprp"])
    pp.add_argument("--woj", default="pl", help="Mapa Dotacji: pl = cała Polska (domyślnie) albo id województwa (327 = podkarpackie)")
    pp.add_argument("--od-nowa", action="store_true", help="cykliczna aktualizacja: pobiera całe źródło od początku (nadpisuje rekordy)")
    pp.add_argument("--od-konca", action="store_true", help="Mapa Dotacji: dopełnij od najnowszych projektów, aż strona jest już w bazie")
    pr = sub.add_parser("radar", help="radar WWW: kanały RSS szkół i uczelni → zgłoszenia z wejściem radar")
    pr.add_argument("--limit", type=int, default=300)
    pr.add_argument("--dni", type=int, default=180)
    pr.add_argument("--organizacja", default="pci")
    pz = sub.add_parser("zestaw", help="buduje i sprawdza zestaw testowy (najlepiej na kopii bazy: RADAR_BAZA=...)")
    pz.add_argument("--n", type=int, default=10)
    pk = sub.add_parser("kontrolny", help="buduje zestaw kontrolny (projekty niewidziane przy kalibracji) → walidacja/kontrolne.csv")
    pk.add_argument("--n-losowe", type=int, default=30)
    pk.add_argument("--n-br", type=int, default=20)
    sub.add_parser("raport", help="liczy miary zestawu testowego → walidacja/raport.md i dane/zestaw_raport.json")
    sub.add_parser("przelicz", help="przelicza zapisane oceny potencjału po zmianie wzoru")
    ps = sub.add_parser("sprawdz", help="sprawdza zgłoszenie o danym id albo nowe z --opis")
    ps.add_argument("id", nargs="?", type=int)
    ps.add_argument("--tytul", default="Zgłoszenie z wiersza poleceń")
    ps.add_argument("--opis")
    ps.add_argument("--instytucja", default="")
    ps.add_argument("--typ-instytucji", default="inna_publiczna")
    ps.add_argument("--typ-innowacji", default="techniczna")
    ps.add_argument("--etap", default="prototyp")
    ps.add_argument("--wiek", default="powyzej_30")
    ps.add_argument("--organizacja", default="ogolny")
    a = p.parse_args(argv)
    con = db.polacz()
    if a.cmd == "pobierz":
        from .zrodla import interreg, mapadotacji, radon, radon_patenty, uprp
        if a.od_nowa:
            with con:
                con.execute("CREATE TABLE IF NOT EXISTS postep(klucz TEXT PRIMARY KEY, wartosc TEXT)")
                con.execute("DELETE FROM postep WHERE klucz LIKE ?", (f"{a.zrodlo}:%",))
        n = {"mapadotacji": lambda: (mapadotacji.pobierz_od_konca if a.od_konca else mapadotacji.pobierz_wszystko)(con, a.woj),
             "interreg": lambda: interreg.pobierz_wszystko(con),
             "radon": lambda: radon.pobierz_wszystko(con),
             "radon_patenty": lambda: radon_patenty.pobierz_wszystko(con),
             "uprp": lambda: uprp.pobierz_wszystko(con)}[a.zrodlo]()
        mapadotacji._postep(con, f"{a.zrodlo}:pelne", str(time.time()))
        print(f"{a.zrodlo}: zapisano {n}; w bazie: {db.liczba_dokumentow(con)}", flush=True)
    elif a.cmd == "radar":
        from .zrodla import www
        stat = www.uruchom(con, a.limit, a.dni, a.organizacja)
        print({k: v for k, v in stat.items() if k != "bledy"}, flush=True)
    elif a.cmd == "zestaw":
        from . import walidacja
        walidacja.zbuduj(con, a.n)
        walidacja.raport(con)
    elif a.cmd == "kontrolny":
        from . import walidacja
        print(walidacja.zbuduj_kontrolny(con, a.n_losowe, a.n_br), flush=True)
    elif a.cmd == "przelicz":
        from . import potencjal
        print(f"przeliczono ocen: {potencjal.przelicz_zapisane(con)}", flush=True)
    elif a.cmd == "raport":
        from . import walidacja
        walidacja.raport(con)
    elif a.cmd == "sprawdz":
        import json

        from .model import Zgloszenie
        from .sprawdz import sprawdz
        zid = a.id
        if zid is None:
            if not a.opis:
                p.error("podaj id albo --opis")
            zid = db.zapisz_zgloszenie(con, Zgloszenie(id=None, wejscie="formularz", tytul=a.tytul, opis=a.opis, link=None,
                                                       instytucja=a.instytucja, typ_instytucji=a.typ_instytucji,
                                                       typ_innowacji=a.typ_innowacji, etap=a.etap, wiek_przedzial=a.wiek,
                                                       organizacja=a.organizacja))
        k = sprawdz(con, zid)
        print(json.dumps({"id": zid, "werdykt": k["werdykt"], "komorka": k["komorka"], "czas_s": k["czas_s"],
                          "koszt_usd": k["koszt_usd"], "pokrycie": k["pokrycie"],
                          "wyniki": [{x: w[x] for x in ("filtr", "procent", "pasmo", "uwaga")} | {"dowody": [
                              {d: v for d, v in dw.items() if d in ("dokument_id", "tytul", "link", "procent", "podobienstwo",
                                                                     "ocena_ai", "odpowiedz", "pytanie", "wlasna")}
                              for dw in w["dowody"][:3]]} for w in k["wyniki"]],
                          "rekomendacje": k["rekomendacje"], "partnerzy": k["partnerzy"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
