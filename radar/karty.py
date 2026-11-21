"""Karty inicjatyw przez LLM (OpenRouter, DeepSeek) → dane/karty.jsonl.

Użycie: OPENROUTER_API_KEY=... [MODEL=... OUT=...] python3 radar/karty.py [min_pkt=5]
Bierze wpisy z ≥ min_pkt punktów sygnałów oraz 50 wpisów z dane/etykiety_proba.json (do porównania z ocenami ręcznymi).
Wznawialne: pomija linki już obecne w karty.jsonl. Cytat sprawdzany: musi być dosłownym fragmentem tekstu (cytat_ok).
Prywatność: tekst wpisu idzie do OpenRoutera z provider.data_collection=deny; karta nie ma zawierać imion i nazwisk.
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from sygnaly import ocena

DANE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dane")
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4.1-flash-1017")
OUT = os.path.join(DANE, os.environ.get("OUT", "karty.jsonl"))  # drugi model: OUT=karty_sedzia.jsonl, min_pkt=99 → tylko próba 50

PROMPT = """Jesteś analitykiem Podkarpackiego Centrum Innowacji. Oceniasz wpis ze strony szkoły lub instytucji publicznej.
Oddolna inicjatywa = uczniowie, nauczyciele lub lokalna społeczność SAMI stworzyli, zbudowali lub uruchomili coś nowego
(projekt, wynalazek, aplikację, koło, akcję), co mogłoby się rozwinąć dalej. NIE: rutyna, uroczystość, ogłoszenie, wycieczka,
zwykły udział w konkursie lub szkoleniu.
Zwróć wyłącznie JSON:
{"czy_inicjatywa": "tak"|"nie"|"niepewne",
 "co": "jedno zdanie, co powstało (pusty, gdy nie)",
 "kto": "instytucja, koło, klasa lub rola, BEZ imion i nazwisk",
 "etap": "pomysł"|"realizacja"|"zakończona"|"nagrodzona"|"",
 "cytat": "dosłowny fragment tekstu (do 200 znaków) będący dowodem; wybierz fragment bez imion i nazwisk",
 "potencjal": 0-5 (0 = brak inicjatywy; 5 = może wyjść poza szkołę: wdrożenie, firma, skala regionu),
 "uzasadnienie": "jedno zdanie"}"""


def wolaj(wpis, klucz):
    body = {"model": MODEL, "max_tokens": 4000, "temperature": 0, "provider": {"data_collection": "deny"},
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": f"Tytuł: {wpis['tytul']}\n\nTekst:\n{wpis['tekst'][:3000]}"}]}
    if "deepseek" in MODEL:  # inne modele (np. qwen) zwracają pustą treść przy tych parametrach
        body.update(response_format={"type": "json_object"}, reasoning={"effort": "low"})
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(body).encode(),
                                 {"Authorization": "Bearer " + klucz, "Content-Type": "application/json", "X-Title": "radar"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    return parsuj(d["choices"][0]["message"]["content"] or ""), d.get("usage", {}).get("cost", 0)


def parsuj(s):
    m = re.search(r"\{.*\}", s, re.S)
    return json.loads(m.group(0)) if m else {}


def norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def main(min_pkt=5):
    klucz = os.environ["OPENROUTER_API_KEY"]
    wpisy = {}
    for w in map(json.loads, open(os.path.join(DANE, "wpisy.jsonl"), encoding="utf-8")):
        w["pkt"] = ocena(w["tytul"] + " " + w["tekst"][:3000])[0]
        wpisy[w["link"]] = w
    proba = {x["link"] for x in json.load(open(os.path.join(DANE, "etykiety_proba.json"), encoding="utf-8"))}
    gotowe = {json.loads(l)["link"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()
    kolejka = [w for k, w in wpisy.items() if (w["pkt"] >= min_pkt or k in proba) and k not in gotowe]
    print("do zrobienia:", len(kolejka), "gotowe:", len(gotowe), flush=True)

    def jeden(w):
        try:
            k, koszt = wolaj(w, klucz)
        except Exception as e:  # błąd sieci/API: nie zapisujemy, ponowne uruchomienie spróbuje znowu
            return None, str(e)[:120]
        if not k.get("czy_inicjatywa"):
            return None, "pusta lub zła odpowiedź JSON"
        k["cytat_ok"] = bool(k.get("cytat")) and norm(k["cytat"]) in norm(w["tekst"] + " " + w["tytul"])
        k.update(link=w["link"], zrodlo_id=w["zrodlo_id"], pkt=w["pkt"], model=MODEL)
        return k, koszt

    suma, bledy = 0.0, 0
    with ThreadPoolExecutor(4) as ex, open(OUT, "a", encoding="utf-8") as f:
        for i, (k, koszt) in enumerate(ex.map(jeden, kolejka), 1):
            if k is None:
                bledy += 1
                print("błąd:", koszt, flush=True)
                continue
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
            f.flush()
            suma += koszt or 0
            if i % 25 == 0:
                print(i, f"koszt {suma:.4f} $", flush=True)
    print("KONIEC: nowych", len(kolejka) - bledy, "błędów", bledy, f"koszt {suma:.4f} $")


if __name__ == "__main__":
    assert parsuj('```json\n{"a": 1}\n```') == {"a": 1} and parsuj("brak") == {}
    assert norm("Koło  „Robotyki”!") in norm("Powstało koło robotyki w szkole")
    main(*map(int, sys.argv[1:2]))
