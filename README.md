# Radar Innowacji

Radar, który **sam wyszukuje istniejące innowacje** na stronach szkół, uczelni i samorządów oraz w publicznych bazach
projektów i patentów, a potem **ocenia je według jawnych kryteriów**, z dowodem przy każdej liczbie.
Rozwiązanie zadania „Radar innowacji” Podkarpackiego Centrum Innowacji (HackNation 2026). PCI jest pierwszym profilem:
nowa organizacja to jeden plik JSON.

**Demo:** https://radar-innowacji.skroban.tech/ · **API:** https://radar-innowacji.skroban.tech/docs

## Problem

Wartościowe pomysły ze szkół, uczelni i samorządów zostają tam, gdzie powstały. Dziś analityk szuka ich ręcznie
(bazy, strony, telefony do naukowców) i ręcznie sprawdza, czy projekt nie jest kopią, plagiatem albo czy nie jest już
opatentowany. Brakuje powtarzalnego procesu oceny z jawnymi kryteriami.

## Dla kogo

Ta sama aplikacja ma zakładki opisane językiem konkretnej osoby, z przyciskami do działającego demo (`/dla/...`):

| Zakładka | Co dostaje |
|---|---|
| [Analityk PCI](https://radar-innowacji.skroban.tech/dla/analityk) | radar sam znajduje projekty; analityk przegląda tylko karty z flagą i decyduje |
| [Szkoła i młodzi twórcy (16–30)](https://radar-innowacji.skroban.tech/dla/mlodzi) | projekt opisany w aktualnościach szkoły może zostać zauważony bez żadnego zgłoszenia |
| [Uczelnia i naukowcy](https://radar-innowacji.skroban.tech/dla/naukowcy) | czy wynik jest nowy na tle patentów i publikacji, zanim zacznie się go chronić |
| [Gmina i urząd](https://radar-innowacji.skroban.tech/dla/gmina) | które gminy wdrożyły już podobne rozwiązanie z dotacją i kogo zapytać |
| [Firma szukająca rozwiązania](https://radar-innowacji.skroban.tech/dla/firma) | kto w regionie pracuje już nad danym problemem |

## Jak działa

```text
 wejście                      wyszukiwanie (kod)                     ocena                                 człowiek
 ─────────                    ──────────────────                     ─────                                 ────────
 radar WWW ─┐                 SQLite FTS5 (BM25) po ~88 tys.         bramka: 4 filtry odrzucenia           kolejka organizacji
 z bazy    ─┼─► karta ──────► dokumentów + źródła na żądanie ──────► (procent, pasmo, dowód)       ──────► decyzja z powodem
 z linku   ─┤   innowacji     (EPO, OpenAlex, Crossref) +            potencjał 0–100 (jawny wzór)          (potwierdź / przywróć /
 opis      ─┘                 wcześniej ocenione projekty            komórka, ścieżka, partnerzy           przekaż) → dziennik
```

1. **Odkrywanie.** Radar WWW codziennie czyta kanały RSS 172 stron szkół, uczelni, PCI i samorządów. AI przepuszcza tylko
   wpisy, które mówią konkretnie, co zbudowano i jak działa (definicja innowacji z Oslo Manual 2018); wydarzenia, warsztaty
   i wyniki konkursów bez opisu rozwiązania odpadają. Z wpisu zostaje streszczenie bez nazwisk i dosłowny cytat-dowód.
   Bazy projektów i patentów odświeżają się co tydzień. Analityk może też ocenić projekt znaleziony w wyszukiwarce
   („Oceń ten projekt”) albo z linku lub opisu („Oceń projekt”). Radar nie jest platformą do zgłaszania pomysłów.
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
   **Bramka nowości:** dojrzałość, zapotrzebowanie, ochronę, finansowanie i specjalizacje mnożymy przez udział punktów
   nowości. Rutynowy zakup bywa dojrzały, powszechny i sfinansowany, ale nie ma potencjału innowacji. Bez oceny nowości
   wynik nie jest liczony.

| Kryterium | Źródło | Jak liczone |
|---|---|---|
| Nowość | AI (rubryka) | „tak” w Q1–Q3 i Q5, każda odpowiedź z dokumentem-dowodem |
| Dojrzałość | formularz | pomysł 25%, prototyp 60%, zakończone 80%, wdrożone 100% |
| Mierzalna przewaga | AI (rubryka) | Q4: koszt, czas, skala |
| Zapotrzebowanie i transfer | kod | inne instytucje z podobnym (nie skopiowanym) projektem; pełne punkty od 5 |
| Możliwość ochrony | kod | wynik filtra patentowego |
| Precedens finansowania | kod | podobne projekty z dofinansowaniem (Mapa Dotacji, Interreg) |
| Specjalizacje organizacji | kod | słowa kluczowe z profilu; dla PCI: lotnictwo i kosmos, motoryzacja, ICT, jakość życia |

5. **Karta innowacji (FAQ §5).** Opis, obszar (technologiczny, edukacyjny, administracyjny), źródło z cytatem, status
   wdrożenia w 5 poziomach (koncepcja → rozwiązanie stosowane), TRL 1–9 (zakres z etapu), ocena potencjału i wiarygodność
   (5 kryteriów liczonych kodem: rejestr publiczny, link, sprawdzony cytat, dowody filtrów, dostępność źródeł). Każde pole
   ma oznaczenie: **fakt z danych**, **deklaracja**, **szacunek AI** albo **reguła w kodzie**.
6. **Dalej.** Werdykt (`odrzucone, do przeglądu` / `do przeglądu` / `bez flag`), komórka organizacji
   (PCI: młodzi 16–30, naukowcy, inni, ogólne), ścieżka z nazwaną regułą (R1 akceleracja i Protolab, R2 ochrona,
   R3 transfer, R4 finansowanie, R5 współpraca) i instytucje, które już działają w temacie.
7. **Człowiek decyduje.** Kolejka pokazuje najpierw pozycje z flagą, a w obrębie werdyktu sortuje po potencjale.
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

## Warunki działania: aktualność danych, harmonogram, AI, wymagania

Na żywo: strona [/warunki](https://radar-innowacji.skroban.tech/warunki) i `GET /api/zrodla`. Każda karta innowacji
podaje stan danych, na których ją oceniono, i godzinę zapytań na żywo.

| Źródło | Tryb | Aktualizacja | Opóźnienie po stronie źródła |
|---|---|---|---|
| Mapa Dotacji UE | kopia lokalna (API) | co tydzień, pon. 03:00 | projekty pojawiają się po podpisaniu umowy |
| Interreg PL–SK | kopia lokalna (XLSX) | co miesiąc, 1. dnia 03:30 | lista publikowana przez sekretariat programu |
| RAD-on: projekty | kopia lokalna (API) | co tydzień, wt. 03:00 | wpisy uczelni i instytutów |
| RAD-on: patenty uczelni | kopia lokalna (API) | co tydzień, śr. 03:00 | tylko udzielone; zgłoszenia jawne po 18 mies. |
| EPO (patenty EP) | na żywo | przy każdym sprawdzeniu | EPO publikuje co tydzień (środa); zgłoszenia jawne po 18 mies. od pierwszeństwa |
| OpenAlex, Crossref | na żywo | przy każdym sprawdzeniu | |
| Radar WWW (RSS) | kanały RSS | codziennie 06:00, wpisy z 180 dni | zależnie od tego, kiedy szkoła opublikuje wpis |

Harmonogram realizują timery systemd instalowane przez `wdrozenie/vm.sh`
(`wdrozenie/aktualizuj.sh <źródło>` → `python -m radar.cli pobierz <źródło> --od-nowa` albo `radar`).
Dane z 21.11.2026 to pierwsze pełne pobranie.

**Ścieżki AI**

| Ścieżka | Ustawienia | Wymagania i koszt | Dane |
|---|---|---|---|
| A: API w chmurze (domyślna) | `OPENROUTER_API_KEY`, `deepseek/deepseek-v4.1-flash`, temperatura 0 | ok. 0,001 $ na sprawdzenie, bez GPU | opis trafia do dostawcy; `data_collection: deny` |
| B: lokalnie, własny model | `AI_URL` (API zgodne z OpenAI: Ollama, vLLM, LM Studio), `MODEL`, opcjonalnie `AI_API_KEY` | model 7–12 mld parametrów: ok. 8–12 GB GPU albo 16 GB RAM | nic nie opuszcza serwera; jakości nie mierzyliśmy |
| C: bez AI | brak klucza | brak | działa wyszukiwanie, plagiat, podobieństwo, patenty; kopia i patent najwyżej żółte; nowość i potencjał: brak danych |

**Wymagania:** Linux albo macOS, Python 3.12+ (albo Docker), 2 vCPU, 4 GB RAM, 2 GB dysku (baza ok. 0,6 GB),
wyjście HTTPS do źródeł, reverse proxy z HTTPS. Klucze: `OPENROUTER_API_KEY` (ścieżka A), `OPENALEX_API_KEY`
(darmowy, opcjonalny); EPO i RAD-on bez klucza. Jedno sprawdzenie trwa 15–45 s.

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
danych: plagiat dwóch projektów, parafrazę AI, przepisany patent, własną pracę i duplikat. Do tego 20 prawdziwych
projektów z bazy wybranych zapytaniem po słowach kluczowych (10 rutynowych zakupów, 10 projektów B+R). Ręczne etykiety
„rutyna / nowość” (`walidacja/etykiety.csv`) czekają na analityków PCI. Wyniki: `walidacja/raport.md` i strona `/miary`.

| Przypadek (21.11.2026 po południu, przed wieczornymi poprawkami filtra nowości; 52 sprawdzenia) | Wykryte |
|---|---|
| Plagiat (połowa zdań z dwóch projektów) | 9/9 |
| Kopia (projekt przepisany przez AI) | 10/10 |
| Patent (opis patentu uczelni przepisany) | 5/5 |
| Własna praca: kontynuacja, bez odrzucenia | 5/5 |
| Duplikat zgłoszenia | 3/3 |

Mediana czasu sprawdzenia 44 s (4 równolegle), średni koszt AI 0,0013 $. Zestaw mierzy czułość na przypadkach
zbudowanych, a nie odsetek fałszywych alarmów. Na 20 prawdziwych projektach z Mapy Dotacji pierwszy przebieg pokazał,
że rutynowe zakupy (wozy OSP, oczyszczalnie) dostawały 62–74 pkt potencjału, prawie tyle co projekty B+R. Dlatego
dodaliśmy bramkę nowości i przeliczyliśmy oceny (`python -m radar.cli przelicz`): rutyna 0–44 pkt, B+R 0–65 pkt,
ale mediana w obu grupach to 22 pkt (pomiar przed regułą „nowość wymaga co najmniej 3 odpowiedzi”). Filtr nowości jest surowy: oznaczył na czerwono 8 z 10 rutynowych i 6 z 10
projektów B+R, więc 16 z 20 prawdziwych projektów trafiło do kolejki „odrzucone, do przeglądu”. Grupy nie są jeszcze
dobrze rozdzielone; to pierwsza rzecz do kalibracji na etykietach PCI. Każde odrzucenie i tak przegląda człowiek.
Opisy projektów OSP często dzielą szablonowe zdania, więc filtr plagiatu flaguje je do przeglądu: decyzję podejmuje człowiek.

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
