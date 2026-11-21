# Radar Innowacji (PCI): projekt rozwiązania

Data: 21.11.2026 · Status: **do zatwierdzenia** · Zadanie: „Radar innowacji”, Podkarpackie Centrum Innowacji, HackNation 2026

## 1. Intencja i dlaczego
Dziś PCI szuka projektów ręcznie: przegląda bazy, szuka po stronach, dzwoni do naukowców (mentorzy PCI, 21.11). Chcą narzędzia, które pomaga **szukać i oceniać** projekty. Nie chcą „AI wrappera”: ma to być inteligentne narzędzie oceny, w którym AI może być jednym z elementów.

Dla PCI projekt odpada z czterech powodów: **1) brak innowacyjności, 2) kopia, 3) plagiat, 4) patent** (także zgłoszenie patentowe w toku). Projekty trafiają do jednej z czterech komórek PCI: **młodzi 16–30, naukowcy, inni, ogólne**. Użytkownicy w PCI to osoby z IT.

Narzędzie prowadzi innowację przez scenariusz z treści zadania (sekcja 6):
- **a)** wprowadzenie przez formularz albo automatyczne wykrycie;
- **b)** karta;
- **c)** ocena: cztery filtry odrzucenia z dowodami i wskaźnikiem procentowym;
- **d)** komórka PCI, ścieżka dalej i potencjalni partnerzy;
- **e)** uzasadnienie każdej rekomendacji oraz mierniki skuteczności systemu.

Przy każdej pozycji z flagą człowiek przegląda dowody i podejmuje decyzję.

### 1a. Zakres: wiele organizacji, PCI jako jedna z nich (decyzja użytkownika, 21.11 ok. 15:50)
Narzędzie nie jest wyłącznie dla PCI. Służy **firmom i instytucjom**, a PCI jest jednym z użytkowników. Treść zadania wymienia jako użytkowników szkoły, uczelnie, JST, inne instytucje publiczne oraz „podmioty poszukujące gotowych lub rozwijających się rozwiązań”. Trzy role, bez kont:
- **Zgłaszający** (szkoła, uczelnia, JST, firma, grupa młodych twórców): zgłasza innowację, dostaje kartę z czterema filtrami. To także samosprawdzenie: „czy mój pomysł jest nowy?”. Wybiera organizację, do której kieruje zgłoszenie (np. PCI), albo zostawia je w katalogu ogólnym.
- **Organizacja oceniająca** (PCI, inkubator, centrum transferu technologii uczelni, fundusz, JST): ma **profil** w `konfiguracja/organizacje/<slug>.json` z własnymi komórkami, ścieżkami i ewentualnie progami. Własna kolejka pod `/o/<slug>/kolejka`, w której przegląda pozycje z flagą. W wersji demo są dwa profile: `pci` (komórki młodzi 16–30 / naukowcy / inni / ogólne, ścieżki akceleracja i Protolab) oraz `ogolny`. Dodanie nowej organizacji to nowy plik JSON (skalowanie, kryterium 5).
- **Szukający** (firma, JST, szkoła): opisuje potrzebę na stronie „Szukam rozwiązania” i dostaje pasujące zgłoszenia oraz dokumenty z korpusu (projekty, publikacje, patenty) z wynikami filtrów i instytucją do kontaktu. To realizuje „łączenie twórców z użytkownikami, partnerami, inwestorami” z sekcji 3 zadania.

## 2. Cele, czego nie robimy, czego nie wolno
**Cele**
- Scenariusz a–e działa od początku do końca na **dwóch przypadkach**: (1) wprowadzony formularzem, (2) wykryty automatycznie. Wymóg z sekcji 6 zadania.
- Najpierw kod, potem AI: wyszukiwanie, plagiat, podobieństwo i reguły są deterministyczne. AI (DeepSeek) robi tylko to, czego nie da się zaprogramować: ocenia nowość i pomaga budować zapytania.
- Każda flaga ma **link do dokumentu-dowodu**. Każdy procent ma podaną definicję.
- Karta pokazuje pokrycie: ile źródeł i dokumentów przeszukano, zakres dat.
- Skalowanie: lista źródeł i województwo (TERYT) w konfiguracji, wymienne adaptery źródeł, API JSON.

**Czego nie robimy**
- Opinii prawnej o zdolności patentowej. To sygnał dla analityka, nie ekspertyza rzecznika.
- Pełnego systemu antyplagiatowego (typu JSA). Porównujemy z dokumentami, które sami zebraliśmy.
- Kont użytkowników i ról. W demo jest jeden analityk.
- Mediów społecznościowych.

**Czego nie wolno (porażka, nawet jeśli działa)**
- Ocena, która jest swobodną liczbą z LLM.
- Link albo dokument wymyślony przez model.
- Ukrywanie luk: 18 miesięcy niewidocznych zgłoszeń patentowych, źródeł, których nie da się pobrać.
- Obchodzenie zabezpieczeń anty-botowych.
- Przechowywanie danych osobowych ponad potrzebę.

## 3. Ograniczenia
- **Czas:** zamrożenie kodu 22.11 o 06:00, zgłoszenie do 22.11 o 11:00. Pracuje jedna osoba; równolegle trwa inny projekt (MC-AED, osobna sesja i osobny folder: nie ruszamy go).
- **Wszystko powstaje 21–22.11.** Nie korzystamy z wcześniejszego prototypu (był w pierwszym commicie, usunięty 21.11) ani z `../../dane_przygotowane`. Dane pobieramy dziś.
- **Regulamin zadania:**
  - zwycięskie rozwiązanie jest publikowane na licencji **EUPL-1.2** (§1 pkt 10), więc repo ma plik LICENSE z EUPL-1.2, a zależności muszą być z nią zgodne: MIT, BSD, Apache-2.0 (§4 pkt 8);
  - nagrodę wypłaca się po przekazaniu kompletnego kodu z dokumentacją (§3 pkt 5);
  - autorzy muszą być twórcami swojego wkładu (§4 pkt 2).
- **Materiały do zgłoszenia** (sekcja 4 zadania): tytuł; opis problemu i rozwiązania; opis działania i funkcji; PDF do 10 slajdów; film do 3 minut (link). Dodatkowo: repozytorium, działający prototyp, zrzuty ekranu.
- **Sekcja 5 zadania:** podać źródła danych, założenia i ograniczenia. Pokazać: skalowanie na wiele organizacji, bezpieczeństwo danych, integrację z istniejącymi systemami, przejrzystość kryteriów, możliwość dalszego rozwoju.
- **Etykieta pobierania:**
  - robots.txt sprawdzany per host;
  - 1 zapytanie na sekundę na host;
  - User-Agent identyfikujący projekt (bez e-maila);
  - TLS weryfikowany;
  - bez obchodzenia Incapsula, Cloudflare i proof-of-work.
- **AI:** DeepSeek przez OpenRouter, `provider.data_collection = deny`, temperatura 0, wyjście w JSON. Decyzja użytkownika: teksty są publiczne, więc mogą iść do AI. Formularz informuje, że opis jest analizowany przez model AI.
- **Klucze** (OpenRouter, EPO OPS, OpenAlex) w `.env`, który jest w .gitignore. Nigdy nie trafiają do repo ani do HTML.
- **Dane osobowe:**
  - z WWW zapisujemy instytucje, nie osoby;
  - nazwiska twórców i zgłaszających z baz patentowych i publikacji to publiczne dane bibliograficzne: pokazujemy je tylko tak, jak są w źródle, z linkiem, i nie wzbogacamy;
  - wiek twórców wyłącznie deklaratywnie, jako przedział w formularzu.

## 4. Podejścia
| | Opis | Werdykt |
|---|---|---|
| **A. Lejek: indeks + reguły, AI na końcu** | Lokalny indeks SQLite FTS5 (BM25) i porównania tekstu (n-gramy, TF-IDF) dają dowody. DeepSeek dostaje tylko znalezione dokumenty i ocenia nowość według rubryki; kod sprawdza, czy model powołuje się na istniejące ID | **Wybrane.** Zgodne z kierunkiem użytkownika („co możemy, robimy deterministycznym kodem, reszta, czyli innowacyjność, AI”) i z wymaganiem mentorów („nie AI wrapper”) |
| B. A + embeddingi wielojęzyczne (np. multilingual-e5-small) | Wyszukiwanie po znaczeniu, łapie parafrazy i tekst angielski | Rozszerzenie tylko wtedy, gdy walidacja (sekcja 9) pokaże, że parafrazy uciekają filtrowi „kopia”. Koszt: torch, pobranie modelu, godziny liczenia na CPU |
| C. LLM ocenia wszystko | Jedno zapytanie „oceń innowacyjność 0–100” | Odrzucone: dokładnie to, czego mentorzy nie chcą; ryzyko wymyślonych linków |

## 5. Architektura (decyzje)
- **Stos:** Python 3.11+, SQLite (jeden plik `dane/radar.sqlite`), FastAPI + uvicorn (MIT/BSD), zwykły HTML i JS bez frameworka frontendowego. Pobieranie: `urllib` albo `httpx` (BSD). XLSX: `openpyxl` (MIT). *Moja decyzja:* FastAPI daje dokumentację API pod `/docs`, co pokazuje „integrację z istniejącymi systemami”.
- **Model danych:**
  - `dokument`: id, zrodlo, typ (`patent` | `publikacja` | `projekt` | `wpis`), tytul, opis, rok, instytucja, wojewodztwo, link, status (np. patent udzielony / zgłoszenie opublikowane / wygasły), jezyk, pobrano_at, surowe (JSON);
  - `dokument_fts`: FTS5 na tytul + opis, tokenizer `unicode61 remove_diacritics 2`;
  - `zgloszenie`: id, wejscie (`formularz` | `radar`), tytul, opis, link, instytucja, typ_instytucji, typ_innowacji (techniczna / organizacyjna / edukacyjna / społeczna / procesowa, za sekcją 1 zadania), etap, wiek_przedzial, utworzono_at;
  - `wynik`: zgloszenie_id, filtr, procent, pasmo (zielone / żółte / czerwone / brak danych), dowody (JSON: id dokumentów, fragmenty, linki), wersja_reguł, policzono_at;
  - `decyzja`: zgloszenie_id, decyzja, powod, kto, kiedy. Dziennik decyzji analityka to później materiał do kalibracji progów.
- **Źródła, dwa rodzaje** (stan dostępności sprawdzony 21.11, `docs/mentorzy/2026-11-21-mentorzy-analiza-i-plan.md` §3.4):
  - **Masowe**, pobierane do indeksu przed użyciem:
    - Mapa Dotacji API (`mapadotacji.gov.pl/wp-json/wp/v2/projekty`): najpierw Podkarpacie, potem cała Polska, jeśli starczy czasu;
    - Interreg: wykaz XLSX 2021–2027 z `interreg.gov.pl/lista-projektow/`;
    - RAD-on `radon.nauka.gov.pl/opendata/polon/projects` (projekty naukowe, abstrakty PL/EN);
    - wpisy radaru.
  - **Na żądanie**, przy każdym zgłoszeniu, z zapisem wyników do `dokument` jako pamięć podręczna:
    - EPO OPS (patenty i opublikowane zgłoszenia, także PL; wymaga klucza);
    - OpenAlex (publikacje; darmowy klucz);
    - Crossref;
    - CORDIS.
  - Źródła z treści zadania, których nie da się pobrać skryptem (UPRP e-wyszukiwarka, EPO Register, PBN, PPM, dLibra PAN), opisujemy jako „integracja przez API lub umowę” w planie wdrożenia.
- **Radar (automatyczne wykrywanie):**
  - lista źródeł w konfiguracji: kanały RSS i podstrony aktualności;
  - na dziś: uczelnie Podkarpacia, szkoły ponadpodstawowe z RSPO ze stroną WWW (technika, licea, branżowe centra umiejętności), strony JST z regionu, PCI;
  - wpis przechodzi wstępny filtr słów (deterministyczny, z zapisanym dowodem słownym), potem DeepSeek: „czy to opis nowego rozwiązania?” (tak / nie / niepewne, z dosłownym cytatem sprawdzanym kodem);
  - „tak” staje się `zgloszenie` z `wejscie = radar`.

## 6. Przepływ oceny jednego zgłoszenia
1. **Karta (b):** z formularza pola wpisuje człowiek. Z linku albo z radaru DeepSeek wyciąga: co powstało, instytucję, typ innowacji i etap, plus dosłowny cytat (kod sprawdza, że cytat jest w tekście).
2. **Zapytanie:**
   - deterministycznie: 10–15 najważniejszych terminów TF-IDF;
   - przez AI: wersja angielska i 1–3 proponowane klasy IPC, tylko do szukania w źródłach angielskich i patentowych.
3. **Wyszukiwanie:** BM25 top-50 lokalnie + top-N z każdego źródła na żądanie (zapis do pamięci podręcznej).
4. **Filtry (c):**

| Filtr | Definicja procentu | Metoda | Rola AI | Dowód |
|---|---|---|---|---|
| **Plagiat** | % 8-gramów słów (po normalizacji) z opisu zgłoszenia, które występują dosłownie w jednym dokumencie | deterministyczna | brak | pokrywające się fragmenty scalone w ciągi, obok siebie, z linkiem |
| **Kopia** | podobieństwo cosinusowe TF-IDF do najbliższego projektu, wpisu albo zgłoszenia (×100); dla dokumentów po angielsku liczone na angielskim tłumaczeniu opisu (*moja decyzja*, patrz §11) | deterministyczna | dla top-3: „ten sam pomysł / częściowo / inny temat” z uzasadnieniem; czerwone tylko przy wysokim podobieństwie **i** „ten sam pomysł” | 3 najbliższe dokumenty: link, rok, instytucja |
| **Patent** | podobieństwo (na tłumaczeniu EN, jak wyżej) do najbliższego dokumentu patentowego + **status** (udzielony / zgłoszenie opublikowane, np. kody A1/A2 bez B / wygasły) | deterministyczna | dla top-3: „czy opis patentu obejmuje to rozwiązanie?” z uzasadnieniem | numer publikacji, status, link; stała uwaga o 18 miesiącach niewidocznych zgłoszeń |
| **Nowość** | liczba pytań rubryki, na które odpowiedź brzmi „tak”, podzielona przez 5 | AI | 5 pytań tak / nie / nie wiadomo, każde z ID dokumentu z listy znalezionych albo z cytatem ze zgłoszenia; odpowiedź z ID spoza listy zamieniana na „nie wiadomo” | odpowiedzi i ID pokazane w karcie |

   Rubryka nowości:
   - **Q1** Czy zgłoszenie rozwiązuje problem, którego nie rozwiązuje żaden ze znalezionych dokumentów?
   - **Q2** Czy używa innej metody lub technologii niż znalezione dokumenty?
   - **Q3** Czy celuje w innego odbiorcę albo kontekst (np. instytucje publiczne, region)?
   - **Q4** Czy opisuje mierzalną przewagę (koszt, czas, skala)?
   - **Q5** Czy to nie jest rutyna (wydarzenie, zakup sprzętu, udział w konkursie, szkolenie)?

5. **Pasma:**
   - zielone / żółte / czerwone według progów z jednego pliku konfiguracyjnego, kalibrowanych na zestawie testowym (sekcja 9);
   - startowo: plagiat ≥ 30% czerwone, 10–30% żółte; podobieństwo kopii i patentu ≥ 0,6 i potwierdzenie AI czerwone, ≥ 0,4 żółte; nowość ≤ 1/5 czerwone, 2/5 żółte.
   - Brak dostępu do źródła daje pasmo „brak danych”, nigdy zielone.
6. **Werdykt:**
   - jakiekolwiek czerwone: „odrzucone automatycznie, do przeglądu”;
   - jakiekolwiek żółte: „do przeglądu”;
   - w przeciwnym razie: „dalej”.
   - Decyzja użytkownika: **system flaguje i odrzuca, ale każdą pozycję z flagą musi przejrzeć człowiek.** Kolejka analityka pokazuje najpierw te z flagą; decyzja (potwierdź / przywróć / przekaż) i jej powód trafiają do dziennika.
7. **Komórka (d), według profilu organizacji, do której trafiło zgłoszenie.** Reguły z JSON profilu, pierwsza pasująca wygrywa. Dla profilu `pci`:
   - przedział wieku z formularza 16–30 albo szkoła ponadpodstawowa → **młodzi 16–30**;
   - uczelnia, instytut albo źródło RAD-on → **naukowcy**;
   - JST i inne instytucje publiczne → **inni**;
   - pozostałe → **ogólne**.
   - *Założenie do potwierdzenia z mentorami:* znaczenie komórek „inni” i „ogólne”.
8. **Ścieżka i partnerzy (d):** tabela reguł: typ innowacji × etap × wyniki filtrów → ścieżka:
   - **komercjalizacja:** akceleracja PCI, prototypowanie w Protolab dla osób 16–30;
   - **transfer / replikacja:** inne instytucje tego samego typu;
   - **finansowanie:** programy i działania z najbardziej podobnych projektów z Mapy Dotacji i Interreg;
   - **ochrona:** sugestia zgłoszenia patentowego przy wysokiej nowości i braku patentu.
   - **Partnerzy** = instytucje z najbardziej podobnych dokumentów: beneficjenci projektów, jednostki naukowe z RAD-on, zgłaszający patenty. To ci, którzy już działają w tym temacie.
9. **Uzasadnienie (e):** przy każdej rekomendacji lista reguł, które zadziałały, i dowodów. Strona „miary” pokazuje trafność filtrów na zestawie testowym, czas i koszt jednego sprawdzenia oraz pokrycie źródeł (liczba dokumentów, daty pobrania).

## 6b. Ocena potencjału (dodane 21.11 po uwadze użytkownika: „całe zadanie opiera się na ocenie projektów”)

Filtry odrzucenia to bramka. Zgłoszenie (także to z flagą) dostaje dodatkowo **ocenę potencjału 0–100** według jawnego wzoru:
`100 × Σ punkty / Σ maksimów kryteriów z danymi`. Kryteria i wagi są w profilu organizacji (`potencjal.wagi`):

| Kryterium | Źródło | Jak liczone |
|---|---|---|
| Nowość | AI (rubryka) | liczba „tak” w Q1–Q3 i Q5, z dokumentem-dowodem |
| Dojrzałość | formularz | etap: pomysł 25%, prototyp 60%, zakończone 80%, wdrożone 100% |
| Mierzalna przewaga | AI (rubryka) | Q4 „tak” |
| Zapotrzebowanie i transfer | kod | liczba innych instytucji z podobnym (0,15–0,6), ale nie skopiowanym projektem; pełne punkty od 5 |
| Możliwość ochrony | kod (+AI) | pasmo filtra patentowego; własne patenty = kontynuacja |
| Precedens finansowania | kod | podobne projekty z Mapy Dotacji / Interreg (≥ 0,15); pełne punkty od 2 |
| Specjalizacje organizacji | kod | słowa kluczowe z profilu (PCI: lotnictwo i kosmos, motoryzacja, ICT, jakość życia) |

Kryterium bez danych nie obniża wyniku (wypada z mianownika, karta to pokazuje). Kolejka sortuje po werdykcie, potem po potencjale.
Analityk może ocenić także projekt znaleziony w bazie (`/szukaj` → „Oceń ten projekt”); dokument źródłowy nie jest wtedy porównywany sam ze sobą.

## 7. Ekrany
```text
/zglos     formularz: tytuł, opis (min. ~300 znaków), link (opcjonalnie), instytucja + typ instytucji,
           typ innowacji (5 typów), etap, przedział wieku twórców; informacja o analizie AI
/o/slug/kolejka  kolejka organizacji: werdykt, komórka, wejście (formularz/radar), flagi; najpierw z flagą
/szukaj    „Szukam rozwiązania”: opis potrzeby → zgłoszenia + dokumenty z korpusu, z wynikami filtrów i instytucją
/kolejka   katalog wszystkich zgłoszeń
/karta/id  4 paski z procentem i pasmem, dowody (linki, fragmenty obok siebie), linia pokrycia,
           komórka, ścieżka, partnerzy, przyciski decyzji z powodem
/miary     trafność na zestawie testowym, czas, koszt, pokrycie źródeł
/docs      OpenAPI (FastAPI); /api/zgloszenia, /api/karta/{id}, /api/sprawdz (POST)
```
Tekst z obcych stron zawsze escapowany; linki tylko http(s).

## 8. Przypadki demo (sekcja 6 zadania, co najmniej dwa)
1. **Wprowadzony formularzem:** opis, który powiela istniejący, już sfinansowany projekt i częściowo przepisuje jego tekst. Wynik: plagiat i kopia czerwone, linki do oryginału, analityk potwierdza odrzucenie w minutę.
2. **Wykryty automatycznie:** nowe rozwiązanie z aktualności szkoły albo uczelni. Wynik: brak kopii i plagiatu, patenty sprawdzone, nowość z uzasadnieniem, komórka, ścieżka, partnerzy.

3. *(Jeśli zostanie czas w filmie)* **Firma szuka rozwiązania:** opis potrzeby → lista zgłoszeń i projektów → kontakt z instytucją.

Konkretne przypadki wybieramy z danych pobranych dziś. Jeśli mentorzy dadzą swoje, mają pierwszeństwo.

## 9. Walidacja i mierniki
Zestaw testowy budowany dziś z pobranych danych i zapisany w repo jako lista ID plus wygenerowane opisy:
- 10 sztucznych plagiatów: 40–60% tekstu skopiowane z dokumentu. Plagiat musi być czerwony.
- 10 parafraz istniejących projektów (przepisanych przez DeepSeek). Kopia co najmniej żółta.
- 5 opisów wynalazków, które mają patent (z EPO OPS). Patent co najmniej żółty.
- 10 opisów rutynowych (wydarzenie, zakup sprzętu) i 10 nowatorskich. Nowość ma je rozdzielić.

Raport: trafność i czułość dla każdego filtra, czas i koszt sprawdzenia. Wyniki trafiają do README i PDF. Testy jednostkowe dla normalizacji, n-gramów, progów i reguł.

## 10. Odpowiedzialność za kryteria oceny (sekcja 8 zadania)
| Kryterium (20% każde) | Czym odpowiadamy |
|---|---|
| Związek z wyzwaniem | scenariusz a–e na dwóch przypadkach; cztery powody odrzucenia od PCI |
| Pomysł i oryginalność | sprawdzenie stanu techniki z dowodami zamiast „LLM ocenia 1–10”; deterministyczne filtry |
| Użyteczność | kolejka z flagami, dowody obok siebie, decyzja jednym kliknięciem; komórki PCI |
| Kompletność prototypu | działający przepływ, prawdziwe dane pobrane dziś, mierniki na zestawie testowym |
| Potencjał wdrożeniowy | źródła i województwo w konfiguracji, API, EUPL-1.2, dziennik decyzji do kalibracji, plan integracji z UPRP i PBN |

## 11. Decyzje wykonawcy (po przeglądzie projektu)
- **Język** (*moja decyzja*): zgłoszenie po polsku porównujemy z dokumentami polskimi wprost. Z angielskimi (patenty, CORDIS, OpenAlex, Crossref) porównujemy przez tłumaczenie opisu na angielski (DeepSeek, temperatura 0). Tłumaczenie zapisujemy i pokazujemy w karcie, więc procent da się odtworzyć. Embeddingi (podejście B) pozostają opcją, jeśli walidacja pokaże słabe wyniki.
- **Zestaw testowy** (*moja decyzja, do potwierdzenia*): przykłady plagiatów i parafraz budujemy sztucznie, więc znamy prawdę. Przykłady „rutyna” i „nowość” bierzemy z prawdziwych danych z etykietą ze źródła, a nie od DeepSeek: rutyna to zwykłe aktualności (wydarzenia, zakupy), nowość to nagrodzone lub sfinansowane projekty B+R. Do tego ręczne sprawdzenie ok. 20 pozycji, żeby uniknąć błędnego koła „AI ocenia to, co AI napisało”.

## 12. Odpowiedzi użytkownika (21.11, ok. 15:20)
1. **Klucze:** OpenRouter jest (w `.env`). EPO OPS i OpenAlex jeszcze nie: do czasu ich dodania filtr patentowy i OpenAlex pokazują „brak danych”, a kod ma działać bez nich.
2. **Własna wcześniejsza praca:** dopasowanie do dokumentu tej samej instytucji (albo tego samego zgłaszającego patent) **nie odrzuca**. Pokazujemy „kontynuacja własnej pracy” i kierujemy na ścieżkę ochrona / licencja. Odrzuca tylko praca **innych**. Wymaga porównania nazw instytucji i zgłaszających (normalizacja nazw).
3. **Ręczne sprawdzenie** ok. 20 przykładów testowych robi użytkownik.
4. **Materiały:** repo, film, prezentacja i **publiczna strona** z działającym formularzem; koszty wywołań AI przez jury są akceptowane. Z tego wynika:
   - hosting z trwałym plikiem SQLite;
   - limit zapytań na IP w formularzu;
   - limit wydatków ustawiony na kluczu OpenRouter;
   - klucze tylko po stronie serwera;
   - zgłoszenia jury widoczne w publicznej kolejce (oznaczone „demo”).

## 13. Zostawione wykonawcy
- Normalizacja tekstu polskiego (diakrytyki, prosty stemming albo przycinanie końcówek).
- Dokładne progi: po kalibracji.
- Ponawianie i backoff przy pobieraniu; harmonogram.
- Wygląd stron.
- Liczba źródeł radaru, jaką zdążymy pobrać dziś.
- Czy Mapa Dotacji obejmie całą Polskę.
