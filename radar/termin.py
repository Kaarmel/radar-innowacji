"""Limit czasu jednego sprawdzenia (w wątku sprawdzenia): źródła na żądanie i AI kończą się, zanim karta zawiśnie.

Co pominięto z braku czasu, trafia do pokrycia karty, więc analityk widzi lukę zamiast wiecznego „Sprawdzam…”.
"""
import threading
import time

_st = threading.local()


def ustaw(sekundy: float | None) -> None:
    _st.do = None if sekundy is None else time.monotonic() + sekundy
    _st.pominiete = []


def zostalo() -> float:
    do = getattr(_st, "do", None)
    return float("inf") if do is None else do - time.monotonic()


def notuj(co: str) -> None:
    if getattr(_st, "do", None) is not None and co not in _st.pominiete:
        _st.pominiete.append(co)


def przekroczenia() -> list[str]:
    return list(getattr(_st, "pominiete", []))
