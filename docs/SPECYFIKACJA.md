# Specyfikacja: Radar Innowacji

Wersja 1.0, 22.11.2026 (koniec HackNation 2026). Dokument opisuje, **co** system robi, **według jakich reguł**, **na jakich
danych** i **z jakimi opóźnieniami**, a na końcu proponuje ścieżkę wdrożenia w Podkarpackim Centrum Innowacji (PCI).
Jak to jest zbudowane technicznie: [ARCHITEKTURA.md](ARCHITEKTURA.md). Przy każdej regule podajemy plik w kodzie,
żeby dało się ją sprawdzić u źródła.

Działające demo: https://radar-innowacji.skroban.tech/ · API: https://radar-innowacji.skroban.tech/docs · Stan danych na żywo: https://radar-innowacji.skroban.tech/warunki

## Spis treści

1. [Cel i zakres](#1-cel-i-zakres)
2. [Użytkownicy i role](#2-użytkownicy-i-role)
3. [Przypadki użycia i wymagania funkcjonalne](#3-przypadki-użycia-i-wymagania-funkcjonalne)
4. [Kryteria oceny](#4-kryteria-oceny)
5. [Propozycja ścieżki dla innowacji: komórka, rekomendacje, partnerzy](#5-propozycja-ścieżki-dla-innowacji-komórka-rekomendacje-partnerzy)
6. [Dane: aktualność i opóźnienia](#6-dane-aktualność-i-opóźnienia)
7. [Interfejsy](#7-interfejsy)
8. [Wymagania niefunkcjonalne](#8-wymagania-niefunkcjonalne)
9. [Mierniki i walidacja](#9-mierniki-i-walidacja)
10. [Propozycja ścieżki wdrożenia w PCI](#10-propozycja-ścieżki-wdrożenia-w-pci)
11. [Ograniczenia i ryzyka](#11-ograniczenia-i-ryzyka)
12. [Słownik](#12-słownik)

---

## 1. Cel i zakres

**Problem.** Wartościowe rozwiązania powstają w szkołach, na uczelniach i w samorządach, ale wiedzą o nich tylko te
instytucje. Opis ginie w aktualnościach szkoły albo w rejestrze projektów. Inna instytucja rozwiązuje ten sam problem
od nowa. Analityk centrum innowacji dowiaduje się o projektach przypadkiem i ręcznie sprawdza, czy pomysł jest nowy,
czy nie jest kopią albo plagiatem i czy nie blokuje go patent.

**Cel.** System, który:

1. sam **odkrywa** istniejące innowacje (strony WWW instytucji, publiczne bazy projektów i patentów),
2. **porządkuje** informację w karcie innowacji (FAQ PCI §5),
3. **ocenia** potencjał według jawnych kryteriów, z dowodem przy każdej liczbie,
4. **kieruje** innowację do właściwej komórki, proponuje ścieżkę dalej z miernikiem skuteczności i wskazuje instytucje,
   które już pracują w temacie,
5. zostawia **decyzję człowiekowi** i zapisuje ją z powodem.

**W zakresie:** radar WWW, ocena projektu z bazy, z linku albo z opisu, wyszukiwarka „Szukam rozwiązania”, katalog
z filtrami i porównaniem, kolejka organizacji z decyzjami, REST API, profile organizacji, harmonogram aktualizacji danych.

**Poza zakresem (świadomie):**

- Radar **nie jest platformą do zgłaszania pomysłów** przez twórców. Formularz „Oceń projekt” służy analitykowi
  do oceny projektu, który znalazł sam (link, opis).
- Radar nie wydaje opinii prawnej o zdolności patentowej. Wskazuje ryzyko kolizji i kieruje do rzecznika patentowego.
- Radar nie zbiera danych osobowych twórców. Wskazuje instytucję, z którą można się skontaktować, a nie osobę.

**Definicja innowacji.** Za Oslo Manual 2018 (OECD/Eurostat): nowe lub ulepszone rozwiązanie, które znacząco różni się
od dotychczasowych i zostało udostępnione użytkownikom albo wdrożone w praktyce. Innowacja nie musi być techniczna:
system rozróżnia typy techniczna, organizacyjna, edukacyjna, społeczna i procesowa, a kartę przypisuje do obszaru
technologicznego, edukacyjnego albo administracyjnego (`radar/klasyfikacja.py`).

## 2. Użytkownicy i role

| Rola | Czego potrzebuje | Co robi w systemie | Gdzie |
|---|---|---|---|
| **Analityk PCI** (główny użytkownik) | wiedzieć o innowacjach pierwszy i mieć dowody | przegląda kolejkę (najpierw flagi), czyta kartę, decyduje z powodem, zleca ocenę projektu z bazy albo z linku | [/o/pci/kolejka](https://radar-innowacji.skroban.tech/o/pci/kolejka), [/dla/analityk](https://radar-innowacji.skroban.tech/dla/analityk) |
| **Komórki PCI** (młodzi 16–30, naukowcy, inni) | karty przypisane do ich programu | dostają kartę z ustawioną komórką i ścieżką | pole „komórka” na karcie |
| **Szkoła, młodzi twórcy** | zostać zauważonym bez pisania wniosku | nic: wystarczy wpis w aktualnościach szkoły | [/dla/mlodzi](https://radar-innowacji.skroban.tech/dla/mlodzi) |
| **Uczelnia, naukowcy** | sprawdzić nowość na tle patentów i publikacji przed ochroną | ocena opisu albo linku | [/zglos](https://radar-innowacji.skroban.tech/zglos), [/dla/naukowcy](https://radar-innowacji.skroban.tech/dla/naukowcy) |
| **Gmina, urząd** | dowiedzieć się, kto wdrożył już podobne rozwiązanie | wyszukiwarka z filtrem źródła, województwa i roku; katalog po obszarze administracyjnym | [/szukaj](https://radar-innowacji.skroban.tech/szukaj), [/dla/gmina](https://radar-innowacji.skroban.tech/dla/gmina) |
| **Firma** | znaleźć, kto w regionie pracuje nad jej problemem | wyszukiwarka, „Oceń ten projekt”, lista partnerów | [/dla/firma](https://radar-innowacji.skroban.tech/dla/firma) |
| **System zewnętrzny** (CRM, portal) | przyjmować i wysyłać karty automatycznie | REST API (JSON, OpenAPI) | [/docs](https://radar-innowacji.skroban.tech/docs) |
| **Administrator** | dostroić system bez programisty | edytuje profil organizacji (JSON) i listę stron (CSV), uruchamia timery | `konfiguracja/`, `wdrozenie/` |

## 3. Przypadki użycia i wymagania funkcjonalne

### 3.1 Scenariusz testowy zadania (a–e)

| Krok zadania | Jak system go realizuje | Kod | Gdzie to widać |
|---|---|---|---|
| a) wykrycie albo wprowadzenie innowacji | radar WWW co godzinę; ocena projektu z bazy; ocena z linku albo opisu; API | `radar/zrodla/www.py`, `radar/app.py` | strona główna, [karta 7](https://radar-innowacji.skroban.tech/karta/7) |
| b) kluczowe informacje | karta: opis, instytucja, obszar, źródło z cytatem, status wdrożenia, TRL, wiarygodność, pochodzenie każdego pola | `radar/klasyfikacja.py` | góra karty |
| c) ocena potencjału | 4 filtry odrzucenia z procentem, pasmem i dowodami; potencjał 0–100 z jawnego wzoru | `radar/filtry.py`, `radar/potencjal.py` | [karta 7, #potencjal](https://radar-innowacji.skroban.tech/karta/7#potencjal) |
| d) odbiorcy, partnerzy, ścieżki | komórka organizacji, ścieżki R1–R5 z nazwaną regułą, instytucje działające w temacie | `radar/werdykt.py` | [karta 18](https://radar-innowacji.skroban.tech/karta/18) |
| e) uzasadnienie i mierniki | powód przy każdej rekomendacji, miernik skuteczności każdej ścieżki, decyzja analityka z powodem w dzienniku | `radar/slowniki.py` (MIERNIKI), tabela `decyzja` | dół karty |

### 3.2 Przypadki użycia

**UC1. Radar wykrywa innowację na stronie instytucji** (aktor: timer systemowy albo analityk przyciskiem).
1. Radar czyta kanały RSS/Atom stron z `konfiguracja/zrodla_www.csv` (wpisy z ostatnich 180 dni).
2. Kod liczy sygnał słów (np. „zbudowali”, „prototyp”, „aplikacja”: +2; „laureat”, „grant”: +1; „jadłospis”, „wycieczka”: −3).
   Dalej idą wpisy z sygnałem ≥ 2, najwyżej 150 na przebieg (bezpiecznik kosztu).
3. AI odpowiada, czy wpis opisuje konkretne nowe rozwiązanie według Oslo Manual, i podaje dosłowny cytat. Kod sprawdza,
   że cytat jest w tekście.
4. AI wyciąga kartę (nazwa, opis, instytucja, typ, etap, cytat) bez imion i nazwisk. Kod dodatkowo usuwa imiona.
5. Powstaje zgłoszenie z wejściem `radar` i rusza pełne sprawdzenie (UC2, kroki 2–6).

Wynik: karta w kolejce organizacji. Lejek z 22.11.2026: 1 539 wpisów → 136 z sygnałem → 13 uznanych za innowację.

**UC2. Ocena projektu z bazy** (aktor: analityk, firma). W wyszukiwarce przy dokumencie „Oceń ten projekt”.
1. Zgłoszenie dostaje opis i instytucję z rejestru (`zrodlo_dok`), a etap „zakończone” z rejestru jest faktem.
2. Tłumaczenie opisu na angielski i terminy wyszukiwania (AI).
3. Wyszukiwanie w bazie lokalnej (BM25) i równolegle w EPO, OpenAlex i Crossref.
4. Cztery filtry, potencjał, werdykt, komórka, ścieżki, partnerzy.
5. Karta z pokryciem: które źródła odpowiedziały, stan danych, użyte modele AI, czas i koszt.
6. Pozycja w kolejce: najpierw flagi, w obrębie werdyktu po potencjale.

Sam dokument źródłowy nie jest dowodem przeciwko projektowi (wykluczany z kandydatów).

**UC3. Ocena z linku albo opisu** ([/zglos](https://radar-innowacji.skroban.tech/zglos)). Z linku: kod pobiera stronę (z ochroną przed SSRF, tylko http(s)),
AI wyciąga kartę z cytatem, analityk poprawia pola przed sprawdzeniem. Z opisu: formularz (tytuł, opis 300–8000 znaków,
instytucja, typ instytucji, typ innowacji, etap, opcjonalnie przedział wieku twórców).

**UC4. Szukam rozwiązania** ([/szukaj](https://radar-innowacji.skroban.tech/szukaj)). Bez AI: BM25 po całym korpusie i ocenionych zgłoszeniach,
filtry źródła, województwa i roku. Wynik: dokumenty z linkiem do źródła i przycisk „Oceń ten projekt”.

**UC5. Katalog i porównanie** ([/kolejka](https://radar-innowacji.skroban.tech/kolejka)). Filtry werdyktu, wejścia (radar, baza, formularz) i obszaru
(technologiczny, edukacyjny, administracyjny). Zaznaczenie 2–4 kart → `/porownaj`: filtry, potencjał, etap, TRL,
komórka i ścieżki obok siebie.

**UC6. Decyzja analityka.** Na karcie: „Potwierdzam odrzucenie”, „Odrzucam: to nie innowacja”, „Przywracam (flaga nietrafna)”,
„Przekazuję dalej (do komórki lub eksperta)”, z polem powodu. Decyzja trafia do dziennika (tabela `decyzja`) i do miar.
„Sprawdź ponownie” powtarza sprawdzenie, np. gdy źródło nie odpowiedziało.

**UC7. Integracja przez API.** `POST /api/zgloszenia` przyjmuje zgłoszenie (202, sprawdzenie w tle), `GET /api/karta/{id}`
zwraca kartę z dowodami. Szczegóły w rozdziale 7.

**UC8. Nowa organizacja.** Administrator dodaje `konfiguracja/organizacje/<slug>.json` (komórki, nazwy ścieżek, wagi,
specjalizacje). Kolejka działa od razu pod `/o/<slug>/kolejka`, bez zmian w kodzie.

### 3.3 Wymagania funkcjonalne

| ID | Wymaganie | Realizacja | Test |
|---|---|---|---|
| F-01 | Radar sam znajduje wpisy o nowych rozwiązaniach na stronach instytucji | `radar/zrodla/www.py` | `testy/test_www.py`, `test_radar_teraz.py` |
| F-02 | Ocena projektu z bazy, z linku, z opisu i przez API | `radar/app.py`, `radar/sprawdz.py` | `test_app.py`, `test_sprawdz.py` |
| F-03 | Wyszukiwanie pełnotekstowe po źródle, województwie i roku | `radar/db.py: szukaj` | `test_db.py`, `test_szukaj_formularz.py` |
| F-04 | Cztery filtry z procentem, pasmem i dowodami | `radar/filtry.py` | `test_filtry.py` |
| F-05 | Własna praca instytucji nie jest powodem odrzucenia; duplikat jest | `radar/filtry.py`, `radar/instytucje.py` | `test_filtry.py`, `test_walidacja.py` |
| F-06 | Potencjał 0–100 z jawnego wzoru, wagi z profilu | `radar/potencjal.py` | `test_potencjal.py` |
| F-07 | Karta wg FAQ §5 z pochodzeniem pól | `radar/klasyfikacja.py` | `test_klasyfikacja.py`, `test_legenda.py` |
| F-08 | Werdykt, komórka, ścieżki z nazwaną regułą, partnerzy | `radar/werdykt.py` | `test_werdykt.py` |
| F-09 | Miernik skuteczności przy każdej ścieżce | `radar/slowniki.py: MIERNIKI` | `test_mierniki.py` |
| F-10 | Decyzja człowieka z powodem, dziennik | `radar/db.py`, tabela `decyzja` | `test_app.py` |
| F-11 | Katalog z filtrami i porównanie 2–4 kart | `radar/app.py: /kolejka, /porownaj` | `test_porownaj.py` |
| F-12 | Stan danych i harmonogram widoczne dla użytkownika | `radar/slowniki.py: HARMONOGRAM`, `/warunki`, `/api/zrodla` | `test_warunki.py` |
| F-13 | Limit czasu sprawdzenia; brakujące źródło opisane na karcie | `radar/termin.py` | `test_termin.py` |
| F-14 | Pobieranie źródeł z zadania (Mapa Dotacji, Interreg, RAD-on, UPRP) | `radar/zrodla/*`, `radar/cli.py pobierz` | `test_zrodla_masowe.py`, `test_zrodla_zadanie.py`, `test_uprp.py` |
| F-15 | Zakładki dla ról (analityk, młodzi, naukowcy, gmina, firma) z przyciskami do demo | `radar/slowniki.py: ROLE`, `/dla/{slug}` | `test_role.py` |
| F-16 | Profile wielu organizacji | `radar/organizacje.py` | `test_werdykt.py`, `test_potencjal.py`, `test_app.py` |

## 4. Kryteria oceny

### 4.1 Bramka: cztery filtry odrzucenia

Kryteria odrzucenia podali mentorzy PCI. Każdy filtr zwraca procent, pasmo (zielone, żółte, czerwone albo „brak danych”),
dowody (dokument, link, źródło, rok, instytucja) i uwagę. Progi są w jednym miejscu: `radar/config.py: PROGI`.

| Filtr | Co mierzy | Jak liczone | Żółte | Czerwone | Rola AI |
|---|---|---|---|---|---|
| **Plagiat** | dosłowne przejęcie tekstu | udział 8-wyrazowych ciągów zgłoszenia (po normalizacji: małe litery, bez diakrytyków) obecnych w dokumencie; 5 najbliższych dokumentów, do 5 wspólnych fragmentów z podświetleniem | ≥ 10% | ≥ 30% | brak |
| **Kopia pomysłu** | ten sam pomysł innymi słowami | podobieństwo cosinusowe TF-IDF na rdzeniach słów, wagi IDF z całego korpusu | ≥ 40% | ≥ 60% **i** AI: „ten sam” | potwierdza: ten sam / częściowo / inny, z uzasadnieniem |
| **Patent** | kolizja z patentem | jak kopia, ale tylko dokumenty typu patent: EPO (na żywo), patenty polskich uczelni (RAD-on), zgłoszenia z Biuletynu UPRP | ≥ 40% | ≥ 60% **i** AI: „ten sam” | jak przy kopii |
| **Nowość** | czy rozwiązanie wnosi coś nowego | rubryka 5 pytań wobec 10 najbliższych dokumentów innych instytucji; procent = 100 × liczba „tak” / 5 | ≤ 2 „tak” | ≤ 1 „tak” | odpowiada na pytania; kod sprawdza dowody |

**Rubryka nowości** (`radar/ai.py: RUBRYKA`). Każda odpowiedź to „tak”, „nie” albo „nie wiadomo”, z identyfikatorem
dokumentu-dowodu i jednym zdaniem uzasadnienia:

| Pytanie | Treść |
|---|---|
| Q1 | Czy zgłoszenie rozwiązuje problem, którego nie rozwiązuje żaden ze znalezionych dokumentów? |
| Q2 | Czy używa innej metody lub technologii niż znalezione dokumenty? |
| Q3 | Czy celuje w innego odbiorcę albo kontekst (np. instytucje publiczne, region)? |
| Q4 | Czy opisuje mierzalną przewagę (koszt, czas, skala)? |
| Q5 | Czy opisuje własne nowe lub ulepszone rozwiązanie, a nie rutynę (wydarzenie, zakup gotowego sprzętu, budowę, remont, szkolenie, udział w konkursie)? |

Odpowiedź „nie” w Q1–Q3 jest dozwolona tylko wtedy, gdy dokument opisuje **to samo** rozwiązanie (ten sam problem
tą samą metodą); podobny temat to jeszcze nie brak nowości.

**Reguły dodatkowe:**

- **Własna praca.** Dopasowanie do dokumentu tej samej instytucji (`radar/instytucje.py: ta_sama`, porównanie
  znormalizowanych nazw) nie podnosi pasma. Karta oznacza je jako kontynuację i kieruje do ochrony lub licencji.
- **Duplikat.** Wcześniejsze zgłoszenie tej samej instytucji z pokryciem tekstu ≥ 90% daje czerwony plagiat z uwagą
  „duplikat zgłoszenia”.
- **Reguła Oslo.** Czerwona nowość przy odpowiedzi „tak” na Q5 (własne nowe rozwiązanie, choć podobne istnieją) zmienia się
  na żółtą: to innowacja co najmniej na poziomie instytucji, więc do sprawdzenia, a nie do odrzucenia.
- **Brak danych.** AI odpowiedziało na mniej niż 3 z 5 pytań → nowość „brak danych”, potencjał nie jest liczony.
  Bez klucza AI kopia i patent są najwyżej żółte (nie ma potwierdzenia).
- **Weryfikacja odpowiedzi AI.** Kod odrzuca odpowiedź, która wskazuje dokument spoza listy wyników, i każdy cytat, którego
  nie ma w tekście.

### 4.2 Werdykt

| Pasma filtrów | Werdykt | Co dalej |
|---|---|---|
| co najmniej jedno czerwone | **odrzucone automatycznie, do przeglądu** | jedyna rekomendacja: przegląd powodów odrzucenia z linkami do dowodów; decyzję podejmuje człowiek |
| co najmniej jedno żółte, żadne czerwone | **do przeglądu** | rekomendacja „sprawdź żółte filtry” plus ścieżki R1–R5, które pasują |
| same zielone | **bez flag, dalej** | ścieżki R1–R5, które pasują |

Kolejka pokazuje najpierw karty z flagą, w obrębie werdyktu sortuje po potencjale (`radar/werdykt.py: werdykt`).

### 4.3 Ocena potencjału 0–100

```text
potencjał = round( 100 × Σ punkty kryteriów z danymi / Σ maksimów tych kryteriów )
punkty kryterium = waga × udział (0–1)
bramka nowości: punkty dojrzałości, zapotrzebowania, ochrony, finansowania i specjalizacji × (punkty nowości / maksimum nowości)
```

AI nie wystawia liczby. Jego odpowiedzi „tak/nie” z rubryki są tylko wejściem do wzoru (`radar/potencjal.py`).
Bramka nowości istnieje, bo rutynowy zakup bywa dojrzały, powszechny, sfinansowany i bez kolidującego patentu, a nie
ma potencjału innowacji. Kryterium bez danych wypada z sumy i z mianownika; karta mówi, którego brakuje.

| Kryterium | Udział (0–1) | Źródło | Waga: profil ogólny | Waga: profil PCI |
|---|---|---|---|---|
| Nowość wobec znalezionych dokumentów | liczba „tak” w Q1, Q2, Q3, Q5 / 4 | AI (rubryka) | 30 | 25 |
| Dojrzałość | pomysł 0,25; prototyp 0,6; zakończone 0,8; wdrożone 1,0 | formularz, rejestr albo szacunek AI | 15 | 15 |
| Mierzalna przewaga | Q4 = „tak” → 1, inaczej 0 | AI (rubryka) | 15 | 10 |
| Zapotrzebowanie i transfer | liczba innych instytucji z podobnym (15–60% podobieństwa, czyli nie kopią) projektem / 5, najwyżej 1 | kod | 15 | 15 |
| Możliwość ochrony | z wyniku filtra patentowego | kod | 15 | 10 |
| Precedens finansowania | podobne projekty z dofinansowaniem (Mapa Dotacji, Interreg) | kod | 10 | 10 |
| Specjalizacje organizacji | czy opis zawiera słowa kluczowe specjalizacji z profilu | kod | – | 15 |

Specjalizacje PCI (`konfiguracja/organizacje/pci.json`): lotnictwo i kosmos, motoryzacja, ICT, jakość życia
(każda z listą rdzeni słów po polsku i angielsku, np. „dron”, „uav”, „aplikac”, „senior”).

**Przykład: karta 7 (RescuePet, technikum, etap: pomysł), profil PCI.**

| Kryterium | Uzasadnienie z karty | Punkty |
|---|---|---|
| Nowość | 4 z 4 pytań Q1–Q3, Q5 z odpowiedzią „tak” | 25 / 25 |
| Dojrzałość | etap „pomysł” = 25% | 3,75 / 15 |
| Mierzalna przewaga | Q4: „nie”, brak wskaźników kosztu, czasu, skali | 0 / 10 |
| Zapotrzebowanie | brak innych instytucji z tym samym problemem (projekty o bezdomności ludzi AI odrzuciło) | 0 / 15 |
| Ochrona | filtr patentowy zielony, najbliższy patent 17% | 10 / 10 |
| Finansowanie | brak sfinansowanych projektów o tym samym problemie | 0 / 10 |
| Specjalizacje | ICT (aplikacja, sztuczna inteligencja) | 15 / 15 |
| **Razem** | 53,75 / 100 | **54** |

Bez potwierdzenia tematu ta karta miała 74 pkt: „zapotrzebowanie” i finansowanie policzono z projektów o bezdomności
ludzi, bo opis mówi o bezdomnych zwierzętach. Teraz AI sprawdza, czy podobny dokument dotyczy tego samego problemu,
zanim policzy zapotrzebowanie, finansowanie (R4) i partnerów; odrzucone dokumenty są wypisane na karcie
(polecenie `python -m radar.cli przelicz-podobne` stosuje to do zapisanych kart bez zmiany filtrów).

Karta 18 (AirNest, projekt z Mapy Dotacji, etap: zakończone): nowość 25, dojrzałość 12, przewaga 0, zapotrzebowanie 15,
ochrona 10, finansowanie 10, specjalizacje 15 (lotnictwo i kosmos, ICT) → **87**.

### 4.4 Karta innowacji (FAQ PCI §5)

| Pole | Reguła | Pochodzenie |
|---|---|---|
| Opis, nazwa, instytucja | z rejestru, z formularza albo wyciągnięte przez AI ze strony (bez nazwisk) | fakt / deklaracja / szacunek AI |
| Źródło i cytat | link do strony albo rejestru; dosłowny cytat sprawdzony przez kod | fakt |
| Obszar | edukacyjna → edukacyjny; techniczna → technologiczny; instytucja publiczna (JST, inna publiczna) → administracyjny; organizacyjna lub społeczna w szkole lub na uczelni → edukacyjny; procesowa → technologiczny | reguła w kodzie |
| Status wdrożenia (5 poziomów) | koncepcja → prototyp → testy → wdrożenie pilotażowe → rozwiązanie stosowane; z etapu: pomysł = koncepcja; prototyp = od prototypu do wdrożenia pilotażowego; zakończone = wdrożenie pilotażowe albo stosowane; wdrożone = stosowane | fakt (projekt zakończony w Mapie Dotacji lub Interreg), deklaracja albo szacunek AI (radar) |
| TRL | pomysł 1–3; prototyp 4–6; zakończone 6–9; wdrożone 7–9 (szacunek z etapu) | reguła w kodzie |
| Zasięg nowości | Q5 = „nie” → rutyna; ≥ 2 „tak” w Q1–Q3 → nowe dla rynku (w przeszukanych bazach); inaczej nowe dla instytucji | szacunek AI |
| Specjalizacje | słowa kluczowe z profilu organizacji | reguła w kodzie |
| Potencjał | rozdział 4.3 | reguła w kodzie |
| Wiarygodność | 5 kryteriów: opis z publicznego rejestru; finansowanie albo zakończenie potwierdzone w rejestrze; link do źródła; dosłowny cytat sprawdzony przez kod; drugi, niezależny zapis tej samej instytucji w bazach. ≥ 4 wysoka, 2–3 średnia, 0–1 niska | reguła w kodzie |

Każde pole na karcie ma etykietę pochodzenia: **fakt z danych**, **deklaracja**, **szacunek AI** albo **reguła w kodzie**.
Karta 7 ma wiarygodność średnią (2/5: link i sprawdzony cytat), karta 18 średnią (3/5: rejestr, finansowanie, link).

## 5. Propozycja ścieżki dla innowacji: komórka, rekomendacje, partnerzy

### 5.1 Komórka organizacji

Reguły są w profilu (`konfiguracja/organizacje/pci.json: komorki`). Wygrywa pierwsza pasująca reguła, w kolejności z pliku:

| Kolejność | Warunek | Komórka PCI |
|---|---|---|
| 1 | przedział wieku twórców 16–30 | Młodzi innowatorzy 16–30 |
| 2 | typ instytucji: szkoła ponadpodstawowa | Młodzi innowatorzy 16–30 |
| 3 | typ instytucji: uczelnia albo instytut badawczy | Naukowcy |
| 4 | typ instytucji: samorząd, inna instytucja publiczna, szkoła podstawowa | Inni (instytucje publiczne) |
| – | nic nie pasuje (np. firma bez twórców 16–30, NGO) | Ogólne |

Przykłady: karta 7 (technikum) → młodzi 16–30; karta 18 (firma) → ogólne.

### 5.2 Ścieżki dalej (R1–R5) i mierniki skuteczności

Reguły są w `radar/werdykt.py: sciezka`, nazwy ścieżek w profilu organizacji, mierniki w `radar/slowniki.py: MIERNIKI`.
Kilka reguł może zadziałać naraz. Przy werdykcie „odrzucone” działa tylko reguła ODRZUCENIE.

| Reguła | Warunek (dokładnie jak w kodzie) | Ścieżka w profilu PCI | Miernik skuteczności |
|---|---|---|---|
| ODRZUCENIE | jakikolwiek filtr czerwony | Do przeglądu analityka: powody odrzucenia z linkami do dowodów | decyzja analityka w ciągu 5 dni roboczych; odsetek odrzuceń potwierdzonych przez człowieka |
| PRZEGLĄD | jakikolwiek filtr żółty | Do przeglądu analityka: sprawdź żółte filtry | decyzja analityka w ciągu 5 dni roboczych |
| R1 | typ techniczny **i** etap prototyp albo wdrożone **i** nowość zielona | Akceleracja PCI i prototypowanie w Protolab | prototyp przetestowany z pierwszym odbiorcą w ciągu 6 miesięcy |
| R2 | nowość ≥ 80% **i** (patent zielony **albo** podobne patenty to własna praca) | Ochrona: konsultacja z rzecznikiem patentowym, zgłoszenie w UPRP lub licencja | zgłoszenie do UPRP albo umowa licencyjna w ciągu 12 miesięcy |
| R3 | typ organizacyjny, edukacyjny, społeczny albo procesowy **i** brak czerwonych | Transfer do innych instytucji tego samego typu (sieć partnerów PCI) | co najmniej jedna instytucja tego samego typu wdraża rozwiązanie w ciągu roku |
| R4 | wśród podobnych projektów są projekty z dofinansowaniem (Mapa Dotacji, Interreg); karta podaje do 3 z linkami | Finansowanie: programy, z których sfinansowano podobne projekty | wniosek o finansowanie złożony w najbliższym naborze |
| R5 | kopia żółta **i** to nie własna praca | Współpraca zamiast dublowania: kontakt z autorami podobnego rozwiązania | pierwszy kontakt z autorem podobnego projektu w ciągu miesiąca |

### 5.3 Partnerzy

Instytucje z najbardziej podobnych dokumentów (`radar/werdykt.py: partnerzy`): najpierw polskie i regionalne źródła
(Mapa Dotacji, Interreg, RAD-on, UPRP, WWW), bo z nimi da się porozmawiać, potem zagraniczne patenty i publikacje.
Bez własnej instytucji, bez powtórzeń, do 5. Przy każdej: dokument, który ją wskazał, i link.

### 5.4 Dwa przypadki krok po kroku

| | Karta 7: RescuePet (radar WWW) | Karta 18: AirNest (projekt z bazy) |
|---|---|---|
| Wejście | wpis w aktualnościach technikum w Trzcianie | „Szukam rozwiązania”: drony, autonomiczne ładowanie → „Oceń ten projekt” |
| Filtry | plagiat 0%, kopia 20%, patent 17%, nowość 80%: wszystkie zielone | wszystkie zielone |
| Werdykt | bez flag, dalej | bez flag, dalej |
| Komórka | młodzi innowatorzy 16–30 (szkoła ponadpodstawowa) | ogólne (firma) |
| Ścieżki | R2 ochrona (nowość 80% ≥ 80%, patent zielony); R4 finansowanie (słabe dopasowanie, rozdział 11) | R2 ochrona; R4 finansowanie |
| Partnerzy | podpowiedź do weryfikacji przez analityka | Politechnika Łódzka, AGH, Łukasiewicz – Instytut Lotnictwa (projekty dronów w RAD-on) |
| Mierniki | zgłoszenie do UPRP albo licencja w 12 miesięcy | jak obok oraz wniosek o finansowanie w najbliższym naborze |
| Czas sprawdzenia | 21,5 s | 16,6 s |

### 5.5 Decyzja człowieka

Każda karta ma formularz decyzji z powodem: potwierdzam odrzucenie; odrzucam, bo to nie innowacja; przywracam (flaga
nietrafna); przekazuję dalej (do komórki lub eksperta). Decyzja nie zmienia wyniku filtrów. Zapisuje się obok niego,
w dzienniku, i służy do kalibracji (rozdział 10). Przykład: [karta 10](https://radar-innowacji.skroban.tech/karta/10), zajęcia z maskotką, które AI
przepuściło, a analityk odrzucił jedną decyzją.

## 6. Dane: aktualność i opóźnienia

### 6.1 Źródła i harmonogram

Stan na 22.11.2026; na żywo: [/warunki](https://radar-innowacji.skroban.tech/warunki) i `GET /api/zrodla`. Harmonogram realizują timery systemd
(`wdrozenie/vm.sh`), każdy uruchamia `wdrozenie/aktualizuj.sh <źródło>`.

| Źródło | Zawartość | Tryb | Dokumentów | Nasza aktualizacja | Opóźnienie po stronie źródła |
|---|---|---|---|---|---|
| Mapa Dotacji UE | projekty z funduszy UE z całej Polski (tytuł, opis, program, województwo, beneficjent ze strony projektu) | kopia lokalna (API WordPress) | 313 750 | co tydzień, pon. 03:00 | projekt pojawia się po podpisaniu umowy o dofinansowanie |
| Interreg Polska–Słowacja | projekty programu | kopia lokalna (XLSX) | 258 | co miesiąc, 1. dnia 03:30 | lista publikowana przez wspólny sekretariat programu |
| RAD-on: projekty naukowe | projekty uczelni i instytutów (bez nazwisk kierowników) | kopia lokalna (API) | 48 817 | co tydzień, wt. 03:00 | wpisy uczelni i instytutów do systemu |
| RAD-on: patenty uczelni | patenty i wzory udzielone polskim uczelniom (bez twórców) | kopia lokalna (API) | 19 004 | co tydzień, śr. 03:00 | tylko prawa udzielone |
| Biuletyn UPRP | zgłoszenia wynalazków (A1) i wzorów użytkowych (U1), 52 ostatnie numery (bez twórców i zgłaszających osób fizycznych) | kopia lokalna (PDF) | 3 304 | co tydzień, czw. 03:00 | zgłoszenie jawne 18 miesięcy od daty pierwszeństwa |
| EPO (Linked Data i European Publication Server) | patenty europejskie: tytuły, zgłaszający, A/B, abstrakty 5 najbliższych | na żywo | (pamięć podręczna) | przy każdym sprawdzeniu | EPO publikuje co tydzień, w środy; zgłoszenia jawne po 18 miesiącach |
| OpenAlex | publikacje z abstraktami | na żywo | (pamięć podręczna) | przy każdym sprawdzeniu | zależnie od indeksowania |
| Crossref | metadane publikacji (DOI) | na żywo | (pamięć podręczna) | przy każdym sprawdzeniu | zależnie od wydawcy |
| Radar WWW | 172 strony szkół, uczelni, PCI i samorządów; ok. 125 z kanałem RSS/Atom | kanały RSS | 1 539 wpisów | co godzinę (5 min po pełnej) i na żądanie (najwyżej raz na 10 min); wpisy z 180 dni | zależnie od tego, kiedy instytucja opublikuje wpis |

### 6.2 Od zdarzenia do karty: opóźnienia od początku do końca

| Zdarzenie w świecie | Kiedy radar je zobaczy (najgorszy przypadek) | Skąd to opóźnienie |
|---|---|---|
| szkoła publikuje wpis o projekcie (strona z RSS) | **do ok. 65 minut**, albo od razu po przycisku „Sprawdź źródła teraz” | timer co godzinę o :05, sprawdzenie 15–45 s |
| szkoła publikuje wpis (strona bez RSS) | nie zobaczy (dziś); plan w rozdziale 10 | ok. 47 ze 172 stron nie ma kanału |
| nowy projekt z dotacją | do 7 dni od publikacji w Mapie Dotacji | cotygodniowa kopia; Mapa publikuje projekt po podpisaniu umowy |
| nowy projekt naukowy albo patent uczelni | do 7 dni od wpisu w RAD-on | cotygodniowa kopia |
| polskie zgłoszenie patentowe | **18 miesięcy** od daty pierwszeństwa + do 7 dni od numeru Biuletynu | tajemnica zgłoszenia; cotygodniowa kopia |
| europejskie zgłoszenie patentowe | **18 miesięcy** od daty pierwszeństwa; potem od razu | EPO na żywo przy każdym sprawdzeniu |
| nowa publikacja naukowa | od chwili zindeksowania w OpenAlex lub Crossref | na żywo |
| nowy projekt Interreg | do 1 miesiąca | comiesięczna kopia |

Zgłoszenia patentowego z ostatnich 18 miesięcy nie pokazuje żadna baza. Karta zawsze o tym przypomina, a filtr patentowy
jest wtedy tylko tak dobry, jak jawne dokumenty.

### 6.3 „Stan na” i świeżość karty

- Dla kopii lokalnej „stan na” to chwila pobrania **najstarszego** rekordu źródła, czyli dane są co najmniej tak świeże.
  Dociąganie pojedynczych rekordów (np. beneficjenta z Mapy Dotacji) nie odmładza całego źródła
  (`radar/slowniki.py: stan_na`).
- Dla źródła na żywo to godzina ostatniego zapytania.
- Każda karta zapisuje stan danych, na których ją oceniono (`pokrycie.stan_danych`), godzinę zapytań na żywo, źródła,
  które nie odpowiedziały, i użyte modele AI. Ocena sprzed tygodnia mówi więc uczciwie, na jakich danych powstała.
  „Sprawdź ponownie” liczy ją na dzisiejszych danych.
- Pełne odświeżenie kopii (`--od-nowa`) nadpisuje rekordy w miejscu. Baza SQLite pracuje w trybie WAL, więc aplikacja
  działa w czasie aktualizacji.

### 6.4 Pokrycie i świadome luki

- **Mapa Dotacji:** ok. 93% z 338 934 projektów w API. Dalsze strony API nie odpowiadały podczas hackathonu;
  cotygodniowa aktualizacja dopełnia resztę. Beneficjent jest tylko na stronie projektu, więc pobieramy go na żądanie
  dla najbliższych dokumentów (do 5 na sprawdzenie).
- **Radar WWW:** ok. 125 ze 172 stron ma kanał RSS/Atom. Lista stron to plik CSV (`nazwa,typ,url,kanal`), więc nowy region
  albo nowa szkoła to nowy wiersz.
- **EPO:** wyszukiwanie po tytułach; abstrakty dla 5 najbliższych.

### 6.5 Źródła z zadania, których nie pobieramy, i jak je wpiąć

| Źródło | Stan (sprawdzone 21.11.2026) | Jak je wpiąć |
|---|---|---|
| e-Wyszukiwarka UPRP | ochrona anty-botowa; nie obchodzimy jej | zgłoszenia bierzemy z Biuletynu UPRP, patenty uczelni z RAD-on, publikacje EP z EPO; karta linkuje do ręcznego sprawdzenia |
| PBN (publikacje) | API wymaga tokenu instytucji | token PCI albo uczelni partnerskiej; moduł jak RAD-on (ok. 1 dzień) |
| CORDIS (projekty UE) | wyszukiwarka zabroniona w robots.txt | miesięczne zrzuty z portalu otwartych danych UE, wczytywane jak Interreg |
| NCBR, PARP, NCN | projekty z funduszy UE są już w Mapie Dotacji, projekty uczelni w RAD-on | listy rankingowe NCBR i NCN (XLSX/PDF) jako kolejny moduł |
| PPM (repozytorium) | robots.txt zabrania pobierania | tylko za zgodą właściciela |
| Google Scholar | brak API, zakaz automatycznego pobierania | zastąpione przez OpenAlex i Crossref |

### 6.6 Zasady pobierania i dane osobowe

- robots.txt sprawdzany dla każdego hosta; najwyżej 1 zapytanie na sekundę na host; identyfikujący User-Agent
  `radar-innowacji-hackathon/0.1`; ponowienia z odstępem (`radar/siec.py`). Zabezpieczeń anty-botowych nie obchodzimy.
- Nie zapisujemy nazwisk: z RAD-on bez kierowników i twórców, z UPRP bez twórców i zgłaszających osób fizycznych,
  z WWW tylko instytucje (AI ma zakaz podawania imion, a kod dodatkowo usuwa imiona). Uczniowie bywają niepełnoletni.

## 7. Interfejsy

### 7.1 Strony WWW

| Adres | Co pokazuje |
|---|---|
| `/` | lejek radaru, ostatnie wykrycia z dowodem, przycisk „Sprawdź źródła teraz” |
| `/o/{slug}/kolejka` | kolejka organizacji (np. `/o/pci/kolejka`): najpierw flagi |
| `/kolejka` | katalog: filtry werdyktu, wejścia i obszaru; zaznaczanie do porównania |
| `/porownaj?id=…` | 2–4 karty obok siebie |
| `/karta/{id}` | karta innowacji z filtrami, potencjałem, ścieżką, partnerami i decyzją |
| `/szukaj?q=&zrodlo=&woj=&rok_od=` | „Szukam rozwiązania” |
| `/zglos` | „Oceń projekt” z linku albo z opisu |
| `/dla/{analityk,mlodzi,naukowcy,gmina,firma}` | zakładki dla ról |
| `/miary` | wyniki zestawu testowego i kontrolnego, czas, koszt, decyzje |
| `/warunki` | źródła, stan danych, harmonogram, ścieżki AI, wymagania |

### 7.2 REST API

Pełny opis OpenAPI: [/docs](https://radar-innowacji.skroban.tech/docs).

| Metoda i adres | Opis |
|---|---|
| `POST /api/zgloszenia` | nowe zgłoszenie; 202 i id, sprawdzenie rusza w tle |
| `GET /api/zgloszenia` | lista zgłoszeń (najpierw z flagą) |
| `GET /api/karta/{id}` | karta: wyniki 4 filtrów z dowodami, potencjał z kryteriami, werdykt, komórka, ścieżki, partnerzy, pokrycie, decyzje |
| `GET /api/szukaj?q=&zrodlo=&rok_od=` | wyszukiwanie w zgłoszeniach i korpusie (bez AI) |
| `GET /api/zrodla` | źródła: liczba dokumentów, stan danych, harmonogram |
| `GET /api/miary` | czas, koszt, werdykty, decyzje, korpus, zestaw testowy |
| `GET /api/organizacje` | profile organizacji |

Pola zgłoszenia (`ZgloszenieWe` w `radar/app.py`):

| Pole | Wartości |
|---|---|
| `tytul` | 5–200 znaków |
| `opis` | 300–8000 znaków (80 dla projektu z bazy) |
| `instytucja` | 2–200 znaków |
| `typ_instytucji` | `szkola_podstawowa`, `szkola_ponadpodstawowa`, `uczelnia`, `instytut`, `jst`, `inna_publiczna`, `firma`, `ngo`, `osoba` |
| `typ_innowacji` | `techniczna`, `organizacyjna`, `edukacyjna`, `spoleczna`, `procesowa` |
| `etap` | `pomysl`, `prototyp`, `wdrozone`, `zakonczone` |
| `wiek_przedzial` | `ponizej_16`, `16_30`, `powyzej_30`, `mieszany` |
| `link` | opcjonalnie, tylko http(s) |
| `organizacja` | slug profilu, domyślnie `ogolny` |
| `zrodlo_dok` | opcjonalnie: id dokumentu z bazy (ocena projektu z bazy) |

### 7.3 Wiersz poleceń

| Polecenie | Co robi |
|---|---|
| `python -m radar.cli pobierz <źródło> [--od-nowa]` | pobiera albo odświeża źródło: `mapadotacji`, `interreg`, `radon`, `radon_patenty`, `uprp` (wznawialne) |
| `python -m radar.cli radar --limit 300 --dni 180` | jeden przebieg radaru WWW |
| `python -m radar.cli sprawdz --opis "…" --organizacja pci` | sprawdza nowe zgłoszenie (albo istniejące po id) |
| `python -m radar.cli zestaw` | buduje i sprawdza zestaw testowy (na kopii bazy: `RADAR_BAZA=…`) |
| `python -m radar.cli kontrolny` | buduje zestaw kontrolny |
| `python -m radar.cli raport` | liczy miary → `walidacja/raport.md` |
| `python -m radar.cli przelicz` | przelicza zapisane potencjały po zmianie wzoru |

### 7.4 Profil organizacji

```json
{
  "slug": "pci",
  "nazwa": "Podkarpackie Centrum Innowacji",
  "komorki": [{"id": "mlodzi_16_30", "nazwa": "Młodzi innowatorzy 16–30", "gdy": {"wiek_przedzial": ["16_30"]}}],
  "komorka_domyslna": "ogolne",
  "sciezki": {"R1": "Akceleracja PCI i prototypowanie w Protolab", "R2": "…", "R3": "…", "R4": "…", "R5": "…"},
  "potencjal": {
    "wagi": {"nowosc": 25, "dojrzalosc": 15, "przewaga": 10, "zapotrzebowanie": 15, "ochrona": 10, "finansowanie": 10, "specjalizacje": 15},
    "specjalizacje": {"Lotnictwo i kosmos": ["lotnic", "dron", "uav"], "ICT": ["aplikac", "algorytm", "software"]}
  }
}
```

Pełny przykład: `konfiguracja/organizacje/pci.json`; profil domyślny: `ogolny.json`.

## 8. Wymagania niefunkcjonalne

| Obszar | Wymaganie | Jak spełnione |
|---|---|---|
| Wydajność | karta w czasie rozmowy telefonicznej | jedno sprawdzenie 15–45 s (mediana 44 s przy 4 równoległych); limit 150 s, potem brakujące źródła są pomijane i opisane na karcie; 3 sprawdzenia równolegle |
| Koszt | ułamek centa za kartę | średnio 0,0013 $ na sprawdzenie (DeepSeek przez OpenRouter); radar WWW najwyżej 150 wpisów do AI na przebieg (ok. 0,05 $) |
| Sprzęt | mały serwer | 1–2 vCPU, 4 GB RAM, 3 GB dysku (baza z całą Polską ok. 1,3 GB); demo działa na 1 vCPU i 4 GB RAM |
| Skalowanie | nowe instytucje i regiony bez programisty | profil JSON na organizację; lista stron w CSV; filtr województwa w wyszukiwarce; adapter źródła to jeden moduł |
| Integracja | wpięcie w systemy PCI | REST API z OpenAPI, JSON, sprawdzenie asynchroniczne (202) |
| Przejrzystość | każda liczba do sprawdzenia | procent, pasmo i link do dowodu przy każdym filtrze; reguła przy każdej rekomendacji; wzór potencjału i wagi jawne; pochodzenie każdego pola karty |
| Niezawodność | awaria źródła nie psuje oceny | źródła na żywo równolegle z limitem czasu; niedostępne źródło zapisane w pokryciu; AI: 3 próby z pominięciem zawodzącego dostawcy, ostatnia na modelu zapasowym innej rodziny; „Sprawdź ponownie” |
| Niezależność od dostawcy AI | możliwość pracy lokalnej | ścieżka B: dowolne API zgodne z OpenAI (Ollama, vLLM, LM Studio); ścieżka C: bez AI (kod liczy plagiat, podobieństwo i patenty) |
| Bezpieczeństwo | aplikacja publiczna | klucze tylko w `.env`; escapowanie całego tekstu z zewnątrz; linki tylko http(s); ochrona przed SSRF przy pobieraniu strony z linku; XML z encjami odrzucany; limit 20 sprawdzeń na IP na godzinę i 200 na dobę |
| Prywatność (RODO) | brak danych osobowych | bez nazwisk z baz i stron; w zgłoszeniu tylko instytucja; dostawca AI z zakazem trenowania na danych (`data_collection: deny`) |
| Zgodność ze źródłami | uczciwe pobieranie | robots.txt, 1 zapytanie/s na host, identyfikujący User-Agent, bez obchodzenia zabezpieczeń |
| Licencja | otwarte wdrożenie w sektorze publicznym | EUPL-1.2; zależności MIT, BSD, Apache-2.0 |

## 9. Mierniki i walidacja

### 9.1 Zestaw testowy: przypadki ze znaną prawdą

`python -m radar.cli zestaw` buduje przypadki z dzisiejszych danych, na osobnej kopii bazy:

| Przypadek (21.11.2026, 52 sprawdzenia) | Jak zbudowany | Wykryte |
|---|---|---|
| Plagiat | połowa zdań z dwóch różnych projektów | 9/9 |
| Kopia | projekt przepisany przez AI innymi słowami | 10/10 |
| Patent | opis patentu uczelni przepisany | 5/5 |
| Własna praca | kontynuacja projektu tej samej instytucji: bez odrzucenia | 5/5 |
| Duplikat | ponowne zgłoszenie tego samego tekstu | 3/3 |

Zestaw mierzy czułość na przypadkach zbudowanych, a nie odsetek fałszywych alarmów.

### 9.2 Nowość na prawdziwych projektach

- **Dane:** projekty z Mapy Dotacji z etykietą „rutyna” albo „nowość”.
- **Etykiety:** głosowanie 5 niezależnych modeli (GPT-5.4-mini, Gemini 3.8 Flash, Claude Haiku 5.5, Mistral Small,
  Antigravity). Nie głosował DeepSeek, który ocenia w radarze. To nie jest ocena człowieka.
- **Przebieg:** pierwszy pomiar na 20 projektach pokazał, że filtr nowości był za surowy dla wdrożeń firm. Poprawiliśmy
  rubrykę (pytanie o rutynę bez podwójnego przeczenia, „brak nowości” tylko przy tym samym rozwiązaniu, reguła Oslo),
  zamroziliśmy ją i zmierzyliśmy na **50 nowych projektach wylosowanych po zamrożeniu** (zestaw kontrolny).

| Miara | Pierwszy pomiar (20) | Po poprawce (te same 20) | Zestaw kontrolny (50 nowych) |
|---|---|---|---|
| Zgodność koloru nowości z etykietami | 0,56 (n=16) | 0,95 (n=19) | **0,62 (n=48)** |
| Średni potencjał: nowość / rutyna | 28 / 18 | 59,8 / 10,5 | **66,8 / 22,0** |
| AUC: potencjał nowości wyżej niż rutyny | – | 0,93 | **0,89** |
| Nowości odrzucone przez lejek | – | 2 z 10 | **2 z 20** |
| Rutyny zatrzymane (odrzucone lub do przeglądu) | – | 10 z 10 | **29 z 30** |

Wniosek: ranking potencjału działa (losowa nowość ma wyższy potencjał niż losowa rutyna w 89% par), a lejek rzadko odrzuca
prawdziwą nowość. Słaby jest sam kolor nowości: 15 z 30 rutyn dostaje żółte „do sprawdzenia”. To błąd w bezpieczną
stronę: więcej przeglądu, mniej utraconych innowacji. Pliki: `walidacja/raport.md`, `walidacja/etykiety_glosy.csv`,
`walidacja/kontrolne_glosy.csv`.

### 9.3 Testy automatyczne

188 testów pytest (`testy/`): filtry, potencjał, werdykt, karta, źródła, API, strony, limit czasu. Testy z prawdziwym API
są pomijane bez kluczy.

### 9.4 Mierniki działania w PCI

| Miernik | Cel w pilotażu | Skąd dane |
|---|---|---|
| czas od publikacji wpisu do karty w kolejce | ≤ 1 godzina | znacznik wpisu RSS i `utworzono_at` karty |
| czas od karty do decyzji analityka | ≤ 5 dni roboczych | dziennik decyzji |
| odsetek odrzuceń automatycznych potwierdzonych przez analityka | ≥ 80% | dziennik decyzji |
| odsetek kart przywróconych (flaga nietrafna) | maleje po kalibracji | dziennik decyzji |
| skuteczność ścieżek R1–R5 | mierniki z rozdziału 5.2 | status karty po 6–12 miesiącach |
| koszt AI na kartę | ≤ 0,01 $ | `koszt_usd` karty, `/miary` |

## 10. Propozycja ścieżki wdrożenia w PCI

| Etap | Czas | Co robimy | Warunek przejścia dalej |
|---|---|---|---|
| **0. Dziś** | gotowe | publiczne demo, dane z całej Polski, profil PCI, radar 172 stron Podkarpacia, API | – |
| **1. Pilotaż** | miesiące 1–2 | instancja na serwerze PCI (albo w chmurze PCI) z logowaniem; 1–2 analityków codziennie przegląda kolejkę; uzupełnienie listy szkół i gmin Podkarpacia w `zrodla_www.csv`; komórki PCI dostają karty | ≥ 100 decyzji w dzienniku; czas do decyzji ≤ 5 dni roboczych |
| **2. Kalibracja** | miesiące 3–4 | wagi potencjału i progi filtrów dopasowane do decyzji analityków; nowy zestaw kontrolny z etykietami analityków PCI (zamiast głosowania modeli); potwierdzanie partnerów i projektów finansowania przez AI, jak przy kopii | zgodność werdyktu z decyzjami ≥ 80% na nowym zestawie |
| **3. Rozszerzenie** | miesiące 5–6 | powiadomienia dla komórek o nowych kartach bez flag; strony bez RSS (lista aktualności z poszanowaniem robots.txt); PBN z tokenem; listy rankingowe NCBR i NCN; zrzuty CORDIS; integracja z CRM PCI przez API | mierniki ścieżek R1–R5 zbierane dla kart z pilotażu |
| **4. Skala** | od miesiąca 7 | kolejne organizacje jako profile JSON (inkubatory, centra transferu technologii uczelni, samorządy); kolejne województwa (lista stron + filtr województwa); model lokalny (ścieżka B), jeśli PCI chce, by opisy nie opuszczały serwera | – |

**Co PCI musi zapewnić:** serwer 2 vCPU / 4 GB RAM / 3 GB dysku z HTTPS (albo GPU 8–12 GB dla modelu lokalnego),
klucz OpenRouter (ok. 0,001 $ na kartę), opcjonalnie token PBN, osobę odpowiedzialną za listę źródeł i analityków,
którzy wpisują decyzje z powodem: to one kalibrują system.

## 11. Ograniczenia i ryzyka

| Ograniczenie | Skutek | Jak ograniczamy |
|---|---|---|
| zgłoszenia patentowe jawne po 18 miesiącach | świeży patent niewidoczny dla filtra | przypomnienie na każdej karcie; Biuletyn UPRP; ścieżka R2 zawsze przez rzecznika |
| TF-IDF nie widzi tego samego pomysłu opisanego zupełnie innymi słowami | kopia może przejść | rubryka nowości (AI) ocenia osobno; czerwona kopia wymaga potwierdzenia AI |
| podobieństwo słów myli tematy (karta 7: bezdomne zwierzęta i bezdomność ludzi) | słabe dopasowania w R4, partnerach i kryterium zapotrzebowania | AI potwierdza temat najbliższych dokumentów przed policzeniem partnerów, zapotrzebowania i R4; pominięte są wypisane na karcie; decyzję zatwierdza analityk |
| kolor nowości za łagodny dla rutyn (15 z 30 żółtych) | więcej pracy przeglądu | błąd w bezpieczną stronę; kalibracja na decyzjach (etap 2) |
| wagi i progi eksperckie | ranking zależy od założeń | wagi w pliku profilu, jawne; dziennik decyzji do kalibracji |
| etykiety walidacji z głosowania modeli, nie od ludzi | miary są przybliżone | etap 2: etykiety analityków PCI |
| Mapa Dotacji ok. 93% | część projektów niewidoczna | cotygodniowa aktualizacja dopełnia resztę |
| strony bez RSS (ok. 47 ze 172) | wpisy niewidoczne | etap 3 |
| dostawca AI w chmurze | opis trafia do dostawcy | `data_collection: deny`; ścieżka B (lokalnie) |
| demo bez logowania | decyzje może wpisać każdy | limit sprawdzeń; etap 1: logowanie i role |

## 12. Słownik

| Pojęcie | Znaczenie |
|---|---|
| **Bramka** | cztery filtry odrzucenia: plagiat, kopia pomysłu, patent, nowość |
| **Pasmo** | wynik filtra: zielone (bez flagi), żółte (do przeglądu), czerwone (odrzucone automatycznie, do przeglądu), brak danych |
| **Werdykt** | wynik bramki dla całej karty: bez flag / do przeglądu / odrzucone, do przeglądu |
| **Potencjał** | ocena 0–100 z jawnego wzoru (rozdział 4.3) |
| **Bramka nowości** | mnożenie części kryteriów potencjału przez udział punktów nowości |
| **Komórka** | odbiorca karty w organizacji (dla PCI: młodzi 16–30, naukowcy, inni, ogólne) |
| **Ścieżka (R1–R5)** | rekomendacja, co zrobić z innowacją dalej, z nazwaną regułą i miernikiem |
| **Własna praca** | podobny dokument tej samej instytucji: kontynuacja, nie powód odrzucenia |
| **Wejście** | skąd jest karta: radar (WWW), baza (projekt z rejestru), formularz (link, opis, API) |
| **Pochodzenie pola** | fakt z danych, deklaracja, szacunek AI albo reguła w kodzie |
| **Stan na** | jak świeże są dane, na których oceniono kartę (rozdział 6.3) |
| **TRL** | poziom gotowości technologicznej 1–9 (szacunek z etapu) |
