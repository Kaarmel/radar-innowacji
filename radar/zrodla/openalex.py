"""OpenAlex: publikacje z abstraktami (darmowy klucz). Zapisujemy instytucje autorów, nie nazwiska."""
import os

from .. import siec
from ..model import Dokument
from . import BrakDostepu

API = "https://api.openalex.org/works"


def abstrakt(indeks: dict | None) -> str:
    if not indeks:
        return ""
    pozycje = sorted((p, slowo) for slowo, lista in indeks.items() for p in lista)
    return " ".join(s for _, s in pozycje)


def parsuj(surowe: dict) -> list[Dokument]:
    out = []
    for w in surowe.get("results", []):
        if not w.get("display_name"):
            continue
        inst = list(dict.fromkeys(i["display_name"] for a in w.get("authorships") or [] for i in a.get("institutions") or []
                                  if i.get("display_name")))
        out.append(Dokument(id=f"openalex:{w['id'].rsplit('/', 1)[-1]}", zrodlo="openalex", typ="publikacja",
                            tytul=w["display_name"], opis=abstrakt(w.get("abstract_inverted_index")),
                            link=w.get("doi") or w["id"], rok=w.get("publication_year"), instytucje=inst[:5],
                            jezyk="pl" if w.get("language") == "pl" else "en"))
    return out


def szukaj(terminy_en: list[str], limit: int = 20) -> list[Dokument]:
    klucz = os.environ.get("OPENALEX_API_KEY")
    if not klucz:
        raise BrakDostepu("OpenAlex: brak klucza API")
    try:
        r = siec.pobierz(API, params={"search": " ".join(terminy_en[:6]), "per_page": limit, "api_key": klucz}, timeout=30)
        r.raise_for_status()
        return parsuj(r.json())
    except Exception as e:
        raise BrakDostepu(f"OpenAlex: {e}") from e
