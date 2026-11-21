"""Polecenia: python -m radar.cli pobierz <mapadotacji|interreg|radon> | sprawdz <id> | radar | zestaw | raport"""
import argparse
import sys

from . import db


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("pobierz")
    pp.add_argument("zrodlo", choices=["mapadotacji", "interreg", "radon", "radon_patenty"])
    pp.add_argument("--woj", default="327", help="Mapa Dotacji: id województwa (327 = podkarpackie)")
    a = p.parse_args(argv)
    con = db.polacz()
    if a.cmd == "pobierz":
        from .zrodla import interreg, mapadotacji, radon, radon_patenty
        n = {"mapadotacji": lambda: mapadotacji.pobierz_wszystko(con, a.woj),
             "interreg": lambda: interreg.pobierz_wszystko(con),
             "radon": lambda: radon.pobierz_wszystko(con),
             "radon_patenty": lambda: radon_patenty.pobierz_wszystko(con)}[a.zrodlo]()
        print(f"{a.zrodlo}: zapisano {n}; w bazie: {db.liczba_dokumentow(con)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
