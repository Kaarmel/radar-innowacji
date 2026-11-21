"""AI (DeepSeek przez OpenRouter): tylko to, czego nie da się zaprogramować. Każda funkcja zwraca (wynik, koszt_usd)
i nigdy nie rzuca wyjątku z powodu złej odpowiedzi modelu. ID dokumentów i cytaty są sprawdzane kodem."""
import json
import os
import re

import httpx

from . import config

URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM = ("Jesteś analitykiem innowacji w sektorze publicznym i firmach. Odpowiadasz wyłącznie poprawnym obiektem JSON "
          "o podanej strukturze. Opierasz się tylko na podanych tekstach; nie wymyślasz dokumentów, liczb ani faktów.")
TYPY_INNOWACJI = {"techniczna", "organizacyjna", "edukacyjna", "spoleczna", "procesowa"}
ETAPY = {"pomysl", "prototyp", "wdrozone", "zakonczone"}
RUBRYKA = [
    ("Q1", "Czy zgłoszenie rozwiązuje problem, którego nie rozwiązuje żaden ze znalezionych dokumentów?"),
    ("Q2", "Czy używa innej metody lub technologii niż znalezione dokumenty?"),
    ("Q3", "Czy celuje w innego odbiorcę albo kontekst (np. instytucje publiczne, region)?"),
    ("Q4", "Czy opisuje mierzalną przewagę (koszt, czas, skala)?"),
    ("Q5", "Czy to nie jest rutyna (wydarzenie, zakup sprzętu, udział w konkursie, szkolenie)?"),
]


def czat_json(system: str, user: str) -> tuple[dict, float]:
    """Jedno ponowienie przy błędzie sieci lub pustej odpowiedzi (dostawcy OpenRouter bywają niestabilni)."""
    wynik, koszt = {}, 0.0
    for _ in range(3):
        wynik, k = _czat_json(system, user)
        koszt += k
        if wynik:
            break
    return wynik, koszt


def _loguj_blad(opis: str) -> None:
    try:
        config.DANE.mkdir(parents=True, exist_ok=True)
        with open(config.DANE / "ai_bledy.log", "a", encoding="utf-8") as f:
            f.write(opis[:600].replace("\n", " ") + "\n")
    except OSError:
        pass


def _czat_json(system: str, user: str) -> tuple[dict, float]:
    klucz = os.environ.get("OPENROUTER_API_KEY")
    if not klucz:
        return {}, 0.0
    body = {"model": config.MODEL, "temperature": 0, "max_tokens": 3000,
            "response_format": {"type": "json_object"}, "provider": {"data_collection": "deny"},
            "usage": {"include": True},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    try:
        r = httpx.post(URL, json=body, timeout=120,
                       headers={"Authorization": f"Bearer {klucz}", "X-Title": "Radar Innowacji"})
        d = r.json()
        tresc = d["choices"][0]["message"].get("content") or ""
        koszt = float((d.get("usage") or {}).get("cost") or 0.0)
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


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def _cytat_ok(cytat, tekst: str) -> str | None:
    return cytat if isinstance(cytat, str) and len(_norm(cytat)) >= 10 and _norm(cytat) in _norm(tekst) else None


def _dokumenty_txt(dokumenty, dl: int) -> str:
    return "\n\n".join(f"[{d.id}] ({d.zrodlo}, {d.typ}{', ' + str(d.rok) if d.rok else ''}) {d.tytul}\n{d.opis[:dl]}"
                        for d in dokumenty)


def karta_z_tekstu(tytul: str, tekst: str) -> tuple[dict, float]:
    odp, koszt = czat_json(SYSTEM, f"""Z tekstu wyciągnij kartę innowacji. JSON:
{{"co": "jedno zdanie: co powstało", "instytucja": "nazwa instytucji (bez imion i nazwisk osób)",
 "typ_innowacji": "techniczna|organizacyjna|edukacyjna|spoleczna|procesowa", "etap": "pomysl|prototyp|wdrozone|zakonczone",
 "cytat": "dosłowny fragment tekstu (do 200 znaków) będący dowodem, bez imion i nazwisk"}}

Tytuł: {tytul}
Tekst:
{tekst[:4000]}""")
    return {"co": str(odp.get("co") or ""), "instytucja": str(odp.get("instytucja") or ""),
            "typ_innowacji": odp.get("typ_innowacji") if odp.get("typ_innowacji") in TYPY_INNOWACJI else "",
            "etap": odp.get("etap") if odp.get("etap") in ETAPY else "",
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
        if isinstance(o, dict) and o.get("dokument_id") in dozwolone and o.get("ocena") in {"ten_sam", "czesciowo", "inny"}:
            wynik[o["dokument_id"]] = {"ocena": o["ocena"], "uzasadnienie": str(o.get("uzasadnienie") or "")}
    return wynik, koszt


def rubryka_nowosci(zgl_opis: str, dokumenty: list) -> tuple[list[dict], float]:
    pytania = "\n".join(f"{k}: {p}" for k, p in RUBRYKA)
    odp, koszt = czat_json(SYSTEM, f"""Oceń nowość zgłoszenia względem ZNALEZIONYCH DOKUMENTÓW (to wszystko, co wiesz o stanie techniki).
Na każde pytanie odpowiedz "tak", "nie" albo "nie_wiadomo". W dokument_id podaj id dokumentu z nawiasu kwadratowego,
na którym opierasz odpowiedź (albo null, gdy opierasz się tylko na zgłoszeniu). JSON:
{{"odpowiedzi": [{{"pytanie": "Q1", "odpowiedz": "tak|nie|nie_wiadomo", "dokument_id": null, "uzasadnienie": "jedno zdanie"}}]}}

PYTANIA:
{pytania}

ZGŁOSZENIE:
{zgl_opis[:3000]}

ZNALEZIONE DOKUMENTY:
{_dokumenty_txt(dokumenty, 1200) or "(brak)"}""")
    dozwolone = {d.id for d in dokumenty}
    z_modelu = {o.get("pytanie"): o for o in odp.get("odpowiedzi") or [] if isinstance(o, dict)}
    wynik = []
    for k, p in RUBRYKA:
        o = z_modelu.get(k) or {}
        odpowiedz = o.get("odpowiedz") if o.get("odpowiedz") in {"tak", "nie", "nie_wiadomo"} else "nie_wiadomo"
        dok = o.get("dokument_id") or None
        if dok is not None and dok not in dozwolone:
            odpowiedz, dok = "nie_wiadomo", None
        wynik.append({"pytanie": k, "tresc": p, "odpowiedz": odpowiedz, "dokument_id": dok,
                      "uzasadnienie": str(o.get("uzasadnienie") or "")})
    return wynik, koszt


def czy_innowacja(tytul: str, tekst: str) -> tuple[dict, float]:
    odp, koszt = czat_json(SYSTEM, f"""Czy ten wpis opisuje NOWE rozwiązanie stworzone w instytucji (urządzenie, aplikację,
metodę, program, usługę, sposób organizacji pracy)? NIE: wydarzenie, wycieczka, uroczystość, zakup sprzętu, udział
w konkursie bez własnego rozwiązania, ogłoszenie, rekrutacja. JSON:
{{"czy": "tak|nie|niepewne", "cytat": "dosłowny fragment tekstu (do 200 znaków) będący dowodem"}}

Tytuł: {tytul}
Tekst:
{tekst[:3500]}""")
    czy = odp.get("czy") if odp.get("czy") in {"tak", "nie", "niepewne"} else "niepewne"
    return {"czy": czy, "cytat": _cytat_ok(odp.get("cytat"), f"{tytul} {tekst}")}, koszt


def parafrazuj(tekst: str) -> tuple[str, float]:
    odp, koszt = czat_json(SYSTEM, f"""Przepisz tekst innymi słowami (inna kolejność zdań, synonimy), zachowując ten sam
pomysł i fakty. Nie kopiuj więcej niż 4 słów z rzędu. JSON: {{"tekst": "..."}}

{tekst[:3000]}""")
    return str(odp.get("tekst") or ""), koszt
