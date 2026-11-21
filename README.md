# Radar Innowacji

Wyszukiwanie i **ocena projektów innowacyjnych** dla firm i instytucji, z dowodami przy każdej liczbie.
Rozwiązanie zadania „Radar innowacji” Podkarpackiego Centrum Innowacji (HackNation 2026). PCI jest jednym z użytkowników:
nowa organizacja to jeden plik JSON.

**Demo:** https://radar.46.60.21.253.sslip.io/ · **API:** https://radar.46.60.21.253.sslip.io/docs

## Problem

Wartościowe pomysły ze szkół, uczelni i samorządów zostają tam, gdzie powstały. Dziś analityk szuka ich ręcznie
(bazy, strony, telefony do naukowców) i ręcznie sprawdza, czy projekt nie jest kopią, plagiatem albo czy nie jest już
opatentowany. Brakuje powtarzalnego procesu oceny z jawnymi kryteriami.

## Jak działa

```text
 wejście                      wyszukiwanie (kod)                     ocena                                 człowiek
 ─────────                    ──────────────────                     ─────                                 ────────
 formularz ─┐                 SQLite FTS5 (BM25) po ~88 tys.         bramka: 4 filtry odrzucenia           kolejka organizacji
 z linku   ─┼─► karta ──────► dokumentów + źródła na żądanie ──────► (procent, pasmo, dowód)       ──────► decyzja z powodem
 z bazy    ─┤   zgłoszenia    (EPO, OpenAlex, Crossref) +            potencjał 0–100 (jawny wzór)          (potwierdź / przywróć /
 radar WWW ─┘                 wcześniejsze zgłoszenia                komórka, ścieżka, partnerzy           przekaż) → dziennik
```

1. **Wejście.** Formularz; strona z linku (AI wypełnia pola, człowiek poprawia); projekt znaleziony w bazie
   (przycisk „Oceń ten projekt” w wyszukiwarce); radar WWW, który czyta kanały RSS szkół, uczelni i instytucji.
2. **Wyszukiwanie.** Tylko kod: indeks pełnotekstowy z wagami BM25. Opis zgłoszenia jest tłumaczony na angielski
   (DeepSeek), żeby szukać w patentach EPO i publikacjach.
3. **Bramka: cztery filtry odrzucenia.** Kryteria podali mentorzy PCI:

| Filtr | Co znaczy procent | Kto liczy | Czerwone, gdy |
|---|---|---|---|
| Plagiat | jaka część 8-wyrazowych ciągów zgłoszenia występuje dosłownie w innym dokumencie | kod | ≥ 30% |
| Kopia pomysłu | podobieństwo treści TF-IDF (rdzenie słów) | kod, AI potwierdza | ≥ 60% **i** AI: „ten sam pomysł” |
| Patent | podobieństwo do patentów EP (udzielonych i zgłoszeń) i patentów polskich uczelni | kod, AI potwierdza | ≥ 60% **i** AI: „ten sam pomysł” |
| Nowość | liczba odpowiedzi „tak” na 5 pytań rubryki | AI, kod sprawdza dowody | ≤ 1 z 5 |

   Przy każdym wyniku są linki do dokumentów, a przy plagiacie fragmenty obok siebie z podświetleniem.
   **Wcześniejsza praca tej samej instytucji nie jest powodem odrzucenia.** Jest oznaczana jako kontynuacja
   i kierowana do ochrony lub licencji. Ponowne zgłoszenie tego samego tekstu to duplikat.
4. **Ocena potencjału 0–100.** Wzór: `100 × Σ punkty / Σ maksimów kryteriów z danymi`. Wagi są w profilu organizacji.

| Kryterium | Źródło | Jak liczone |
|---|---|---|
| Nowość | AI (rubryka) | „tak” w Q1–Q3 i Q5, każda odpowiedź z dokumentem-dowodem |
| Dojrzałość | formularz | pomysł 25%, prototyp 60%, zakończone 80%, wdrożone 100% |
| Mierzalna przewaga | AI (rubryka) | Q4: koszt, czas, skala |
| Zapotrzebowanie i transfer | kod | inne instytucje z podobnym (nie skopiowanym) projektem; pełne punkty od 5 |
| Możliwość ochrony | kod | wynik filtra patentowego |
| Precedens finansowania | kod | podobne projekty z dofinansowaniem (Mapa Dotacji, Interreg) |
| Specjalizacje organizacji | kod | słowa kluczowe z profilu; dla PCI: lotnictwo i kosmos, motoryzacja, ICT, jakość życia |

5. **Dalej.** Werdykt (`odrzucone, do przeglądu` / `do przeglądu` / `bez flag`), komórka organizacji
   (PCI: młodzi 16–30, naukowcy, inni, ogólne), ścieżka z nazwaną regułą (R1 akceleracja i Protolab, R2 ochrona,
   R3 transfer, R4 finansowanie, R5 współpraca) i instytucje, które już działają w temacie.
6. **Człowiek decyduje.** Kolejka pokazuje najpierw pozycje z flagą, a w obrębie werdyktu sortuje po potencjale.
   Decyzja i jej powód trafiają do dziennika.

**Dlaczego to nie jest „AI wrapper”.** Wyszukiwanie, plagiat, podobieństwo, reguły ścieżek i wzór potencjału liczy kod.
AI (DeepSeek przez OpenRouter, temperatura 0, bez rozumowania) robi tylko to, czego nie da się zaprogramować:
tłumaczy zapytanie, potwierdza kopie, odpowiada na pytania rubryki nowości i wyciąga kartę z tekstu strony. Kod odrzuca
każdą odpowiedź, która powołuje się na dokument spoza wyników, i każdy „cytat”, którego nie ma w tekście.

## Źródła danych

| Źródło | Tryb | Zakres | Uwagi |
|---|---|---|---|
| [Mapa Dotacji UE](https://mapadotacji.gov.pl) | pobierane (API WordPress) | 20 069 projektów z Podkarpacia | beneficjent tylko ze strony projektu, dociągany na żądanie |
| [Interreg Polska–Słowacja](https://pl-sk.eu) | pobierane (XLSX) | 258 projektów | |
| [RAD-on](https://radon.nauka.gov.pl): projekty | pobierane (API) | 48 817 projektów naukowych | bez nazwisk kierowników |
| RAD-on: patenty | pobierane (API) | 19 004 patentów i wzorów polskich uczelni | bez nazwisk twórców |
| [EPO Linked Data](https://data.epo.org/linked-data/) + European Publication Server | na żądanie | tytuły EP, zgłaszający, A/B, abstrakty 5 najlepszych | bez klucza |
| [OpenAlex](https://openalex.org) | na żądanie | publikacje z abstraktami | darmowy klucz |
| [Crossref](https://www.crossref.org) | na żądanie | metadane publikacji | |
| Radar WWW | kanały RSS | `konfiguracja/zrodla_www.csv` | robots.txt, 1 zapytanie/s na host |

Pobieranie: `python -m radar.cli pobierz mapadotacji|interreg|radon|radon_patenty` (wznawialne).
Zawsze respektujemy robots.txt, a zabezpieczeń anty-botowych nie obchodzimy. Dlatego e-Wyszukiwarka UPRP (Incapsula)
jest tylko linkowana, a wyszukiwarka CORDIS (`Disallow: /search`) pominięta.

## Ograniczenia (świadome)

- **Zgłoszenia patentowe są jawne dopiero po 18 miesiącach.** Karta zawsze to przypomina. Polskie zgłoszenia w toku
  (Biuletyn UPRP) to następne źródło do dodania.
- Patenty EP są wyszukiwane po tytułach. Abstrakty pobieramy dla 5 najlepszych wyników.
- Podobieństwo TF-IDF łapie przepisany tekst, ale nie ten sam pomysł opisany zupełnie innymi słowami. Dlatego czerwone
  pasmo kopii wymaga potwierdzenia AI, a nowość ocenia rubryka.
- Wagi potencjału i progi są eksperckie. Dziennik decyzji analityków służy do ich kalibracji.
- Wersja demo jest publiczna, bez logowania; decyzje może wpisać każdy. Limit: 20 sprawdzeń na adres IP na godzinę
  i 200 na dobę.

## Miary

Zestaw testowy (`python -m radar.cli zestaw`, na osobnej kopii bazy) buduje przypadki ze znaną prawdą z dzisiejszych
danych: plagiat dwóch projektów, parafrazę AI, przepisany patent, własną pracę i duplikat. Do tego 20 projektów z bazy
z ręczną etykietą „rutyna / nowość”. Wyniki: `walidacja/raport.md` i strona `/miary`.

## Uruchomienie

```bash
uv venv && uv pip install -r requirements.txt pytest      # albo: python -m venv .venv && pip install -r requirements.txt
cp .env.example .env                                       # wpisz OPENROUTER_API_KEY i OPENALEX_API_KEY
python -m radar.cli pobierz interreg                       # i pozostałe źródła
uvicorn radar.app:app --port 8090                          # http://127.0.0.1:8090
python -m radar.cli sprawdz --opis "…" --organizacja pci   # sprawdzenie z wiersza poleceń
python -m radar.cli radar --limit 300                      # radar WWW
pytest                                                     # testy (te z prawdziwym API pomijane bez kluczy)
```

Wdrożenie na Ubuntu: `wdrozenie/vm.sh` (uvicorn jako usługa systemd, Caddy z HTTPS, osobny blok hosta).
Docker: `docker build -t radar-innowacji . && docker run -p 8090:8090 -v "$PWD/dane:/app/dane" --env-file .env radar-innowacji`.

## Integracja i skalowanie

- REST API z OpenAPI: `POST /api/zgloszenia`, `GET /api/karta/{id}`, `GET /api/zgloszenia`, `GET /api/szukaj?q=`,
  `GET /api/miary`, `GET /api/organizacje`.
- Nowa organizacja (inkubator, centrum transferu technologii uczelni, samorząd): plik `konfiguracja/organizacje/<slug>.json`
  z komórkami, ścieżkami, wagami potencjału i specjalizacjami. Kolejka pod `/o/<slug>/kolejka`.
- Nowe województwo: parametr `--woj` przy Mapie Dotacji i nowa lista `zrodla_www.csv`.
- Bezpieczeństwo: klucze tylko w `.env`, escapowanie całego tekstu z zewnątrz, linki tylko http(s), ochrona przed SSRF
  przy pobieraniu strony z linku, XML z encjami odrzucany, brak danych osobowych z baz (bez nazwisk twórców i kierowników).

## Historia repozytorium

Pierwszy commit (`394f34c`) zawiera wcześniejszy, porzucony prototyp. Został usunięty w `5dd8d88`, a obecne
rozwiązanie powstało od nowa w trakcie hackathonu (21–22.11.2026). Projekt, plan i dziennik decyzji: `docs/`.

## Licencja

EUPL-1.2. Zależności: MIT, BSD lub Apache-2.0.
