"""AI (DeepSeek przez OpenRouter): tylko to, czego nie da się zaprogramować. Każda funkcja zwraca (wynik, koszt_usd)
i nigdy nie rzuca wyjątku z powodu złej odpowiedzi modelu. ID dokumentów i cytaty są sprawdzane kodem."""
import json
import os
import re
import threading

import httpx

from . import config, termin

URL = "https://openrouter.ai/api/v1/chat/completions"  # ścieżka A (API); AI_URL zmienia na model lokalny (ścieżka B)
SYSTEM = ("Jesteś analitykiem innowacji w sektorze publicznym i firmach. Odpowiadasz wyłącznie poprawnym obiektem JSON "
          "o podanej strukturze. Opierasz się tylko na podanych tekstach; nie wymyślasz dokumentów, liczb ani faktów.")
TYPY_INNOWACJI = {"techniczna", "organizacyjna", "edukacyjna", "spoleczna", "procesowa"}
ETAPY = {"pomysl", "prototyp", "wdrozone", "zakonczone"}
RUBRYKA = [
    ("Q1", "Czy zgłoszenie rozwiązuje problem, którego nie rozwiązuje żaden ze znalezionych dokumentów?"),
    ("Q2", "Czy używa innej metody lub technologii niż znalezione dokumenty?"),
    ("Q3", "Czy celuje w innego odbiorcę albo kontekst (np. instytucje publiczne, region)?"),
    ("Q4", "Czy opisuje mierzalną przewagę (koszt, czas, skala)?"),
    ("Q5", "Czy zgłoszenie opisuje własne nowe lub ulepszone rozwiązanie, a nie rutynę (wydarzenie, zakup gotowego sprzętu, budowę, remont, szkolenie, udział w konkursie)?"),
]


_rej = threading.local()


def zacznij_rejestr() -> None:
    """Początek sprawdzenia: od teraz zapisujemy, które modele i którzy dostawcy odpowiedzieli."""
    _rej.uzyte, _rej.ostatni = [], None


def rejestr() -> list[str]:
    return list(dict.fromkeys(getattr(_rej, "uzyte", [])))


def czat_json(system: str, user: str) -> tuple[dict, float]:
    """Dostawcy OpenRouter bywają niestabilni (pusta treść, finish=length): każde ponowienie omija dostawcę, który zawiódł,
    a ostatnia próba idzie do modelu zapasowego innej rodziny."""
    wynik, koszt, ignoruj = {}, 0.0, []
    for proba in range(3):
        if termin.zostalo() < 8:
            termin.notuj("część odpowiedzi AI")
            break
        _rej.ostatni = None
        wynik, k = _czat_json(system, user, ignoruj=list(ignoruj), model=config.MODEL_ZAPASOWY if proba == 2 else None)
        koszt += k
        ostatni = getattr(_rej, "ostatni", None)
        if wynik:
            if ostatni and hasattr(_rej, "uzyte"):
                _rej.uzyte.append(f"{ostatni[0]} ({ostatni[1]})")
            break
        if ostatni and ostatni[1]:
            ignoruj.append(ostatni[1])
    return wynik, koszt


def _loguj_blad(opis: str) -> None:
    try:
        config.DANE.mkdir(parents=True, exist_ok=True)
        with open(config.DANE / "ai_bledy.log", "a", encoding="utf-8") as f:
            f.write(opis[:600].replace("\n", " ") + "\n")
    except OSError:
        pass


def _czat_json(system: str, user: str, ignoruj: list[str] | None = None, model: str | None = None) -> tuple[dict, float]:
    url = os.environ.get("AI_URL") or URL
    openrouter = "openrouter.ai" in url
    klucz = os.environ.get("OPENROUTER_API_KEY") if openrouter else os.environ.get("AI_API_KEY")
    if openrouter and not klucz:
        return {}, 0.0  # ścieżka C: bez AI
    body = {"model": (model if openrouter else None) or os.environ.get("MODEL") or config.MODEL, "temperature": 0, "max_tokens": 3000,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if openrouter:
        # bez rozumowania: inaczej model zużywa cały limit na "myślenie" i zwraca pustą treść (finish=length)
        body |= {"provider": {"data_collection": "deny"} | ({"ignore": ignoruj} if ignoruj else {}),
                 "usage": {"include": True}, "reasoning": {"enabled": False}}
    try:
        r = httpx.post(url, json=body, timeout=max(5.0, min(300 if not openrouter else 120, termin.zostalo() - 3)),
                       headers={"X-Title": "Radar Innowacji"} | ({"Authorization": f"Bearer {klucz}"} if klucz else {}))
        d = r.json()
        tresc = d["choices"][0]["message"].get("content") or ""
        koszt = float((d.get("usage") or {}).get("cost") or 0.0)
        _rej.ostatni = (d.get("model") or body["model"], d.get("provider") or "")
    except Exception as e:
        _loguj_blad(f"wyjątek {type(e).__name__}: {e} | {getattr(locals().get('r'), 'text', '')[:300]}")
        return {}, 0.0
    if not tresc:
        _loguj_blad(f"pusta treść | provider={d.get('provider')} finish={d['choices'][0].get('finish_reason')}")
    m = re.search(r"\{.*\}", tresc, re.S)
    try:
        return (json.loads(m.group(0)) if m else {}), koszt
    except json.JSONDecodeError:
        return {}, koszt


def _z(x, dozwolone) -> str | None:
    """Wartość z dozwolonego zbioru albo None; odporne na listy i obiekty zamiast tekstu."""
    return x if isinstance(x, str) and x in dozwolone else None


def _tekst(x) -> str:
    return x if isinstance(x, str) else ""


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def _cytat_ok(cytat, tekst: str) -> str | None:
    return cytat if isinstance(cytat, str) and len(_norm(cytat)) >= 10 and _norm(cytat) in _norm(tekst) else None


def _dokumenty_txt(dokumenty, dl: int) -> str:
    return "\n\n".join(f"[{d.id}] ({d.zrodlo}, {d.typ}{', ' + str(d.rok) if d.rok else ''}) {d.tytul}\n{d.opis[:dl]}"
                        for d in dokumenty)


def karta_z_tekstu(tytul: str, tekst: str) -> tuple[dict, float]:
    odp, koszt = czat_json(SYSTEM, f"""Z tekstu wyciągnij kartę innowacji. NIE podawaj imion ani nazwisk osób: zastąp je rolą
(uczniowie, nauczyciel, zespół). JSON:
{{"nazwa": "krótka nazwa rozwiązania (do 80 znaków), np. Aplikacja do szukania zaginionych zwierząt; nie nagłówek newsa",
 "co": "jedno zdanie: co powstało", "opis": "3-4 zdania: jaki problem, jakie rozwiązanie, jak działa, na jakim jest etapie",
 "instytucja": "nazwa instytucji",
 "typ_innowacji": "techniczna|organizacyjna|edukacyjna|spoleczna|procesowa", "etap": "pomysl|prototyp|wdrozone|zakonczone",
 "cytat": "dosłowny fragment tekstu (do 200 znaków) będący dowodem, bez imion i nazwisk"}}

Tytuł: {tytul}
Tekst:
{tekst[:4000]}""")
    return {"nazwa": _tekst(odp.get("nazwa"))[:120], "co": _tekst(odp.get("co")), "opis": _tekst(odp.get("opis")), "instytucja": _tekst(odp.get("instytucja")),
            "typ_innowacji": _z(odp.get("typ_innowacji"), TYPY_INNOWACJI) or "",
            "etap": _z(odp.get("etap"), ETAPY) or "",
            "cytat": _cytat_ok(odp.get("cytat"), f"{tytul} {tekst}")}, koszt


def tlumacz_zapytanie(opis: str) -> tuple[dict, float]:
    odp, koszt = czat_json(SYSTEM, f"""Przygotuj wyszukiwanie w bazach patentów i publikacji po angielsku. JSON:
{{"opis_en": "wierne tłumaczenie opisu na angielski", "terminy_en": ["5-10 angielskich terminów technicznych lub fraz"],
 "ipc": ["1-3 najbardziej prawdopodobne podklasy IPC, np. C02F"]}}

Opis:
{opis[:4000]}""")
    terminy = [str(t) for t in odp.get("terminy_en") or [] if isinstance(t, str) and t.strip()][:10]
    ipc = [str(t) for t in odp.get("ipc") or [] if isinstance(t, str) and re.fullmatch(r"[A-H]\d{2}[A-Z]", t.strip())][:3]
    return {"opis_en": str(odp.get("opis_en") or ""), "terminy_en": terminy, "ipc": ipc}, koszt


def ten_sam_pomysl(zgl_opis: str, dokumenty: list) -> tuple[dict[str, dict], float]:
    if not dokumenty:
        return {}, 0.0
    odp, koszt = czat_json(SYSTEM, f"""Dla każdego dokumentu oceń, czy opisuje TO SAMO rozwiązanie co zgłoszenie
(ten_sam), częściowo to samo (czesciowo), czy tylko podobny temat (inny). JSON:
{{"oceny": [{{"dokument_id": "id z nawiasu kwadratowego", "ocena": "ten_sam|czesciowo|inny", "uzasadnienie": "jedno zdanie"}}]}}

ZGŁOSZENIE:
{zgl_opis[:3000]}

DOKUMENTY:
{_dokumenty_txt(dokumenty, 1500)}""")
    dozwolone = {d.id for d in dokumenty}
    wynik = {}
    for o in odp.get("oceny") or []:
        if isinstance(o, dict) and _z(o.get("dokument_id"), dozwolone) and _z(o.get("ocena"), {"ten_sam", "czesciowo", "inny"}):
            wynik[o["dokument_id"]] = {"ocena": o["ocena"], "uzasadnienie": _tekst(o.get("uzasadnienie"))}
    return wynik, koszt


def rubryka_nowosci(zgl_opis: str, dokumenty: list) -> tuple[list[dict], float]:
    pytania = "\n".join(f"{k}: {p}" for k, p in RUBRYKA)
    odp, koszt = czat_json(SYSTEM, f"""Oceń nowość zgłoszenia względem ZNALEZIONYCH DOKUMENTÓW (to wszystko, co wiesz o stanie techniki).
Na każde pytanie odpowiedz "tak", "nie" albo "nie_wiadomo". Odpowiedź "nie" w Q1–Q3 tylko wtedy, gdy dokument opisuje
TO SAMO rozwiązanie (ten sam problem rozwiązany tą samą metodą); podobny temat albo ta sama branża to jeszcze nie brak nowości.
Gdy żaden znaleziony dokument nie opisuje tego samego rozwiązania, odpowiedź na Q1–Q3 to "tak". "nie_wiadomo" tylko wtedy,
gdy samo zgłoszenie jest zbyt ogólne, by powiedzieć, co robi.
W dokument_id podaj id dokumentu z nawiasu kwadratowego,
na którym opierasz odpowiedź (albo null, gdy opierasz się tylko na zgłoszeniu). JSON:
{{"odpowiedzi": [{{"pytanie": "Q1", "odpowiedz": "tak|nie|nie_wiadomo", "dokument_id": null, "uzasadnienie": "jedno zdanie"}}]}}

PYTANIA:
{pytania}

ZGŁOSZENIE:
{zgl_opis[:3000]}

ZNALEZIONE DOKUMENTY:
{_dokumenty_txt(dokumenty, 1200) or "(brak)"}""")
    dozwolone = {d.id for d in dokumenty}
    z_modelu = {o["pytanie"]: o for o in odp.get("odpowiedzi") or [] if isinstance(o, dict) and isinstance(o.get("pytanie"), str)}
    wynik = []
    for k, p in RUBRYKA:
        o = z_modelu.get(k) or {}
        odpowiedz = _z(o.get("odpowiedz"), {"tak", "nie", "nie_wiadomo"}) or "nie_wiadomo"
        dok = o.get("dokument_id") or None
        if dok is not None and not isinstance(dok, str):
            dok = None  # lista/obiekt zamiast id: odpowiedź bez wskazanego dokumentu
        elif dok is not None and dok not in dozwolone:
            odpowiedz, dok = "nie_wiadomo", None
        wynik.append({"pytanie": k, "tresc": p, "odpowiedz": odpowiedz, "dokument_id": dok,
                      "uzasadnienie": _tekst(o.get("uzasadnienie"))})
    return wynik, koszt


def czy_innowacja(tytul: str, tekst: str) -> tuple[dict, float]:
    odp, koszt = czat_json(SYSTEM, f"""Czy ten wpis opisuje konkretne NOWE lub ulepszone rozwiązanie stworzone w tej instytucji
(urządzenie, aplikację, metodę nauczania, program, usługę, sposób organizacji pracy), które działa albo zostało przetestowane
lub udostępnione (definicja innowacji wg Oslo Manual 2018)? Odpowiedz "tak" TYLKO wtedy, gdy tekst mówi konkretnie, CO
zbudowano lub opracowano i JAK to działa albo do czego służy. NIE: wydarzenie, warsztaty, hackathon, wycieczka, uroczystość,
szkolenie, pokaz, pogadanka, zajęcia lub kampania edukacyjna albo profilaktyczna (także gdy występuje maskotka
lub „autorska postać”), konkurs, akcja, zakup sprzętu, zakup lub montaż gotowych instalacji (np. fotowoltaika,
magazyny energii), wyposażenie pracowni, budowa, przebudowa lub remont, inwestycja w infrastrukturę, projekt unijny
opisany tylko celami, nabór,
rekrutacja, ogłoszenie, wynik w konkursie bez opisu działania rozwiązania. Wyjątek: tekst opisuje konkretne nowe narzędzie
lub metodę opracowaną w instytucji (np. aplikację, urządzenie, autorski program nauczania) i to, jak działa. JSON:
{{"czy": "tak|nie|niepewne", "cytat": "dosłowny fragment tekstu (do 200 znaków) opisujący działanie rozwiązania, bez imion i nazwisk"}}

Tytuł: {tytul}
Tekst:
{tekst[:3500]}""")
    czy = _z(odp.get("czy"), {"tak", "nie", "niepewne"}) or "niepewne"
    return {"czy": czy, "cytat": _cytat_ok(odp.get("cytat"), f"{tytul} {tekst}")}, koszt


def parafrazuj(tekst: str) -> tuple[str, float]:
    odp, koszt = czat_json(SYSTEM, f"""Przepisz tekst innymi słowami (inna kolejność zdań, synonimy), zachowując ten sam
pomysł i fakty. Nie kopiuj więcej niż 4 słów z rzędu. JSON: {{"tekst": "..."}}

{tekst[:3000]}""")
    return str(odp.get("tekst") or ""), koszt
