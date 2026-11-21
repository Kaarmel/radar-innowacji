"""Karta innowacji wg FAQ PCI §5: obszar, poziom wdrożenia, TRL, wiarygodność. Same reguły w kodzie, bez AI.

Każde pole ma pochodzenie: fakt (z publicznego rejestru), deklaracja (wpisał człowiek), szacunek_ai (AI ze strony
źródłowej, z dosłownym cytatem) albo regula (wyliczone przez kod z pól powyżej).
"""
POCHODZENIE = {"fakt": "fakt z danych", "deklaracja": "deklaracja", "szacunek_ai": "szacunek AI", "regula": "reguła w kodzie"}
OSLO = ("Innowacja to nowe lub ulepszone rozwiązanie, które znacząco różni się od dotychczasowych i zostało udostępnione "
        "użytkownikom lub wdrożone w praktyce (OECD/Eurostat, Oslo Manual 2018).")
KROKI = ["koncepcja", "prototyp", "testy", "wdrożenie pilotażowe", "rozwiązanie stosowane w praktyce"]
# etap z karty → zakres na skali FAQ (indeksy KROKI) i zakres TRL
ETAP_KROKI = {"pomysl": (0, 0), "prototyp": (1, 3), "zakonczone": (3, 4), "wdrozone": (4, 4)}
ETAP_TRL = {"pomysl": "1–3", "prototyp": "4–6", "zakonczone": "6–9", "wdrozone": "7–9"}
PUBLICZNE = {"jst", "inna_publiczna"}
EDUKACJA = {"szkola_podstawowa", "szkola_ponadpodstawowa", "uczelnia"}
REJESTRY_ZAKONCZONYCH = ("mapadotacji:", "interreg:")


def _obszar(typ_innowacji: str, typ_instytucji: str) -> str:
    if typ_innowacji == "edukacyjna":
        return "edukacyjny"
    if typ_innowacji == "techniczna":
        return "technologiczny"
    if typ_instytucji in PUBLICZNE:
        return "administracyjny"
    if typ_instytucji in EDUKACJA and typ_innowacji in ("organizacyjna", "spoleczna"):
        return "edukacyjny"
    return "technologiczny" if typ_innowacji == "procesowa" else "administracyjny"


def _pochodzenie_pol(k: dict) -> str:
    """Skąd są typ i etap: rejestr (fakt), człowiek (deklaracja) albo AI ze strony (szacunek)."""
    if k.get("wejscie") == "radar":
        return "szacunek_ai"
    if k.get("wejscie") == "baza" and (k.get("zrodlo_dok") or "").startswith(REJESTRY_ZAKONCZONYCH) and k.get("etap") == "zakonczone":
        return "fakt"
    return "deklaracja"


def _wiarygodnosc(k: dict) -> dict:
    dowody = sum(1 for w in k.get("wyniki") or [] if w.get("dowody"))
    pokrycie = k.get("pokrycie") or {}
    kryteria = [
        {"nazwa": "Opis z publicznego rejestru (Mapa Dotacji, Interreg, RAD-on)", "spelnione": k.get("wejscie") == "baza" and bool(k.get("zrodlo_dok"))},
        {"nazwa": "Link do źródła informacji", "spelnione": (k.get("link") or "").startswith(("http://", "https://"))},
        {"nazwa": "Dosłowny cytat ze źródła sprawdzony przez kod", "spelnione": bool(k.get("cytat"))},
        {"nazwa": "Filtry oparte na dokumentach-dowodach", "spelnione": dowody >= 1},
        {"nazwa": "Wszystkie źródła dostępne w czasie sprawdzenia", "spelnione": bool(pokrycie) and not pokrycie.get("niedostepne")},
    ]
    n = sum(x["spelnione"] for x in kryteria)
    return {"poziom": "wysoka" if n >= 4 else "średnia" if n >= 2 else "niska", "spelnione": n, "kryteria": kryteria,
            "pochodzenie": "regula"}


def profil(k: dict) -> dict:
    etap = k.get("etap") or ""
    od, do = ETAP_KROKI.get(etap, (None, None))
    poch = _pochodzenie_pol(k)
    techniczna = k.get("typ_innowacji") in ("techniczna", "procesowa")
    potencjal = (k.get("potencjal") or {}).get("wynik")
    return {
        "obszar": {"wartosc": _obszar(k.get("typ_innowacji") or "", k.get("typ_instytucji") or ""), "pochodzenie": "regula"},
        "wdrozenie": {"kroki": [{"nazwa": n, "zaznaczony": od is not None and od <= i <= do} for i, n in enumerate(KROKI)],
                      "pochodzenie": poch},
        "trl": {"wartosc": ETAP_TRL.get(etap) if techniczna else None, "pochodzenie": "regula",
                "uwaga": "szacunek z etapu" if techniczna else "nie dotyczy (innowacja nietechniczna)"},
        "potencjal": {"wartosc": potencjal, "pochodzenie": "regula"},
        "wiarygodnosc": _wiarygodnosc(k),
        "pochodzenie_opisu": poch,
    }
