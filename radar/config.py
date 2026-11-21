"""Ustawienia: ścieżki, progi pasm, model AI, User-Agent. Klucze tylko z .env (poza gitem)."""
import os
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
DANE = KORZEN / "dane"
BAZA = Path(os.environ.get("RADAR_BAZA") or DANE / "radar.sqlite")  # RADAR_BAZA: osobna kopia np. dla zestawu testowego
KONFIGURACJA = KORZEN / "konfiguracja"

USER_AGENT = "radar-innowacji-hackathon/0.1 (+https://github.com/; projekt HackNation 2026)"
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4.1-flash")  # przypięta wersja, nie "latest"

# Progi pasm (spec §6.5). Jedno miejsce; zmiany po kalibracji zapisywać w walidacja/raport.md.
PROGI = {
    "plagiat": {"czerwone": 30.0, "zolte": 10.0},           # % 8-gramów zgłoszenia znalezionych dosłownie
    "kopia": {"czerwone": 0.6, "zolte": 0.4},                # cosinus TF-IDF; czerwone wymaga potwierdzenia AI
    "patent": {"czerwone": 0.6, "zolte": 0.4},
    "nowosc": {"czerwone_max_tak": 1, "zolte_max_tak": 2},   # liczba odpowiedzi "tak" z 5
    "duplikat_plagiat": 90.0,
}


def wczytaj_env(plik: Path = KORZEN / ".env") -> None:
    """Wczytuje KLUCZ=wartość z .env do os.environ (nie nadpisuje istniejących)."""
    if not plik.exists():
        return
    for linia in plik.read_text(encoding="utf-8").splitlines():
        linia = linia.strip()
        if not linia or linia.startswith("#") or "=" not in linia:
            continue
        k, v = linia.split("=", 1)
        if v.strip():
            os.environ.setdefault(k.strip(), v.strip())


wczytaj_env()
