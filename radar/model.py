"""Wspólne typy danych."""
from dataclasses import dataclass, field


@dataclass
class Dokument:
    id: str                 # "<zrodlo>:<id_w_zrodle>"
    zrodlo: str             # mapadotacji|interreg|radon|crossref|cordis|openalex|epo|www|zgloszenie
    typ: str                # projekt|publikacja|patent|wpis|zgloszenie
    tytul: str
    opis: str
    link: str
    rok: int | None = None
    instytucje: list[str] = field(default_factory=list)
    wojewodztwo: str | None = None
    status: str | None = None      # patent: "udzielony"|"zgloszenie"
    jezyk: str = "pl"              # "pl"|"en"|"inny"


@dataclass
class Zgloszenie:
    id: int | None
    wejscie: str            # "formularz"|"radar"
    tytul: str
    opis: str
    link: str | None
    instytucja: str
    typ_instytucji: str
    typ_innowacji: str
    etap: str
    wiek_przedzial: str
    opis_en: str | None = None
    cytat: str | None = None
    demo: bool = False
    organizacja: str = "ogolny"
    zrodlo_dok: str | None = None   # ocena projektu z bazy: id dokumentu, z którego powstało zgłoszenie


@dataclass
class WynikFiltra:
    filtr: str              # plagiat|kopia|patent|nowosc
    procent: float | None   # None = brak danych
    pasmo: str              # zielone|zolte|czerwone|brak_danych
    dowody: list[dict]
    uwaga: str = ""
    wlasna_praca: bool = False


@dataclass
class Rekomendacja:
    nazwa: str
    powod: str
    reguly: list[str]
