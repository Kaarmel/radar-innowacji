"""Profile organizacji oceniających (PCI, inkubator, centrum transferu, JST…): komórki i ścieżki w JSON."""
import json
from functools import lru_cache

from . import config

KATALOG = config.KONFIGURACJA / "organizacje"


@lru_cache(maxsize=None)
def _wszystkie() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(KATALOG.glob("*.json"))}


def wczytaj(slug: str | None) -> dict:
    profile = _wszystkie()
    return profile.get(slug or "ogolny") or profile["ogolny"]


def lista() -> list[dict]:
    return [{"slug": p["slug"], "nazwa": p["nazwa"], "opis": p.get("opis", "")} for p in _wszystkie().values()]


def nazwa_komorki(profil: dict, komorka: str) -> str:
    return profil.get("nazwy_komorek", {}).get(komorka, komorka)
