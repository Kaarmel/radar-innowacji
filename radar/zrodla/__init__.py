"""Adaptery źródeł danych. Każdy zwraca list[Dokument]."""


class BrakDostepu(Exception):
    """Źródło niedostępne: brak klucza, błąd sieci, blokada. Filtr dostaje wtedy pasmo brak_danych."""
