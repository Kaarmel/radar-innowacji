"""Crossref: metadane publikacji (czasem abstrakt). Bez nazwisk autorów."""
from .. import siec
from ..model import Dokument
from ..tekst import bez_html
from . import BrakDostepu

API = "https://api.crossref.org/works"
TYPY = {"journal-article", "proceedings-article", "posted-content", "book-chapter", "report", "dissertation"}


def parsuj(surowe: dict) -> list[Dokument]:
    out = []
    for it in (surowe.get("message") or {}).get("items", []):
        if it.get("type") not in TYPY or not it.get("title"):
            continue
        rok = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        out.append(Dokument(id=f"crossref:{it['DOI']}", zrodlo="crossref", typ="publikacja", tytul=bez_html(it["title"][0]),
                            opis=bez_html(it.get("abstract") or ""), link=f"https://doi.org/{it['DOI']}",
                            rok=rok if isinstance(rok, int) else None, jezyk="en"))
    return out


def szukaj(terminy_en: list[str], limit: int = 20) -> list[Dokument]:
    try:
        r = siec.pobierz(API, params={"query.bibliographic": " ".join(terminy_en[:6]), "rows": limit}, timeout=30)
        r.raise_for_status()
        return parsuj(r.json())
    except Exception as e:
        raise BrakDostepu(f"Crossref: {e}") from e
