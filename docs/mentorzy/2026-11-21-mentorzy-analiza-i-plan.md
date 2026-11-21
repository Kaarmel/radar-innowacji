# Mentorzy PCI (21.11.2026, ok. 14:00): notatka, analiza i proponowana ścieżka

> Status: **propozycja do decyzji**, nic z tego nie jest jeszcze zbudowane.
>
> **Aktualizacja 21.11, ok. 15:10 (odpowiedzi użytkownika):** D1: teraz PCI (MC-AED idzie równolegle w innej sesji). D2: zgodnie z treścią zadania, czyli dwa przypadki: formularz + automatyczne wykrycie. D3: system flaguje i odrzuca, ale człowiek musi przejrzeć każdą pozycję z flagą. D4: tak, dane są publiczne. D6: **wcześniejszego kodu i danych nie używamy**: usunięte 21.11, dane pobieramy od nowa dziś (dotyczy też odwołań do „wpisów szkół” i `dane_przygotowane` w tym pliku). Projekt: `docs/superpowers/specs/2026-11-21-radar-innowacji-design.md`.

## 1. Prompt (dosłownie, jak go napisałem)

```text
bylem u mentorow,
1. jak to obecnie wyglada
szukaja baz danych, szukaja projektow recznie, kontaktuja sie z naukowcami, szukaja wszedzie
sa okreslone komorki na klasy
jest 1. dla mlodych 16-30lat 2.naukowcy 3.inni 4.ogolen
2.co chca
chca cos co pomorze im szukac i oceniac projeky
3. czego nie chca
nie chca ai wrapera tylko intelgetne (moez byc ai) do oceny
4.
waznymi dla nich punktami do odzucenia sa 1. brak innowacyjnosci 2.kopia 3.plagiat 4.patenty (uwaga morze byc w trakcie wyrabiania przez kogos patentu)
5.
to sa ludzie siedzacy w informatyce 
wiec mysze zeby zrobic pobieranie baz, oraz innuych baz bardziej ogolniejszych
scrapowaniu stron i zbieraniu
potem zeby model ai od razu filtrowal innowacyjnosc, kopie, plagity, patenty itp zeby byly wskazniki procentowe a w przypadku plagiatow kopi itp wskazywal linki do prac i rozwiazan zeby odrazu mozna bylo wykluczyc
to ma byc maksymalnie uzyteczne, mozemy uzywac do tego deepseka jako analizy jako tani ai zeby to dzialo
ale tez mozemy robic baze instejacych roziwazan pomyslow zeby moc to zamiast ai to np regexem czy jakos wyszukiwac ze to co mozemy to zrobmy deterministrycznym kodem a reszte na pewno innowacyjnosc ai bo to trudno zaprogramowac.


zaplanuj sciezke budowanie tego, oraz potem daj mi pytania/decycje ktore mam odpowiedziec zeby moc dalej pracowac

zapisz tego promopta i grubo przeanalzuj
```

## 2. Co powiedzieli mentorzy (uporządkowane)

| # | Temat | Ich słowa (skrót) | Co z tego wynika dla produktu |
|---|---|---|---|
| 1 | Jak jest dziś | szukają w bazach, szukają projektów ręcznie, dzwonią do naukowców, „szukają wszędzie” | Ból = **czas wyszukiwania i sprawdzania**. Produkt ma skracać ręczne przeszukiwanie wielu baz, nie tylko „odkrywać” |
| 1 | Organizacja | komórki (klasy): **1. młodzi 16–30, 2. naukowcy, 3. inni, 4. ogólne** | Każdy projekt musi trafić do **jednej komórki** (routing). Komórka 16–30 wymaga wieku twórcy, a tego nie ma w danych z WWW (patrz pytanie D8) |
| 2 | Czego chcą | narzędzia, które pomoże **szukać i oceniać** projekty | Dwie funkcje równorzędne: wyszukiwanie (radar + bazy) i ocena (lejek odrzuceń) |
| 3 | Czego nie chcą | **nie „AI wrapper”**; inteligentne narzędzie do oceny, AI może być w środku | AI nie może być rdzeniem. Rdzeń = indeks + reguły + miary; AI = jedna, mierzona warstwa z dowodami |
| 4 | Powody odrzucenia | **1. brak innowacyjności, 2. kopia, 3. plagiat, 4. patenty** (także zgłoszenia „w trakcie”) | To jest kręgosłup oceny: **lejek 4 filtrów odrzucających**, każdy z linkiem do dowodu |
| 5 | Kim są | ludzie z IT | Mogą uruchamiać skrypty, chcą danych i API; doceniają pobieranie baz, deterministykę, eksport |

## 3. Analiza (gruba)

### 3.1 Najważniejsza zmiana względem tego, co jest w repo
Do tej pory budowaliśmy **radar** (znajdź oddolne inicjatywy na stronach szkół) z oceną „potencjału”. Mentorzy przesunęli środek ciężkości na **sprawdzanie stanu techniki** (jak w urzędzie patentowym): *czy to już istnieje, czy ktoś to skopiował, czy ktoś to opatentował*. To jest:
- **bardziej konkretne** (da się zmierzyć i pokazać link),
- **bardziej deterministyczne** (wyszukiwanie i porównanie tekstu to klasyczna informatyka),
- **oryginalniejsze** na hackathonie (większość zespołów zrobi „formularz + LLM ocenia 1–10”).

Radar szkół nie idzie do kosza: staje się **jednym ze źródeł kandydatów** (wejście), a 7 061 wpisów + 3 131 kart to także **korpus porównawczy** (czy szkoła X nie robi tego samego co szkoła Y).

### 3.2 Cztery filtry: co da się zrobić deterministycznie, a co wymaga AI

| Filtr | Co naprawdę znaczy | Deterministycznie (bez AI) | AI (DeepSeek) | Wskaźnik % (uczciwy) | Dowód |
|---|---|---|---|---|---|
| **Kopia** (to samo rozwiązanie już istnieje / zostało zrealizowane) | Ten sam pomysł w innych słowach albo ten sam projekt zgłoszony drugi raz | Wyszukiwanie BM25 (SQLite FTS5) po korpusie; near-duplicate przez MinHash na 5-gramach słów | Potwierdzenie „to ten sam pomysł czy tylko ten sam temat?” dla top-k trafień | **Podobieństwo do najbliższego dokumentu** (0–100%), nie „prawdopodobieństwo kopii” | Link + tytuł + rok + źródło najbliższych 3–5 |
| **Plagiat** (skopiowany tekst opisu) | Fragmenty opisu przepisane z cudzej pracy | W pełni deterministyczne: wspólne 8-gramy słów, zdania pokrywające się z dokumentem źródłowym | Niepotrzebne | **% tekstu zgłoszenia znaleziony dosłownie** w źródle | Podświetlone fragmenty obok siebie + link |
| **Patent** (udzielony lub zgłoszony) | Rozwiązanie jest chronione lub ktoś je zgłosił | Wyszukiwanie po tytule/abstrakcie/klasie IPC; status z bazy (udzielony / zgłoszenie opublikowane / wygasły) | Tłumaczenie zapytania PL→EN + propozycja klas IPC (żeby szukać w bazie EN); ocena „czy zastrzeżenie pokrywa pomysł” dla top-k | Podobieństwo do najbliższego patentu + **status** | Numer publikacji + link do rejestru |
| **Brak innowacyjności** | Nic nowego względem tego, co już jest | Nic: tu deterministyka się kończy | **Tak**: porównanie zgłoszenia z top-k znalezionych dokumentów, rubryka 4–5 pytań tak/nie („co jest nowe względem dokumentu X?”) | % = udział spełnionych pytań rubryki, **nie** swobodna liczba z modelu | Każda odpowiedź wskazuje ID dokumentu z listy znalezionych; ID sprawdzane kodem (jak `cytat_ok` w `karty.py`) |

Wniosek: **3 z 4 filtrów są w większości deterministyczne**. AI robi dwie rzeczy: (1) pomaga szukać (tłumaczenie, słowa kluczowe, IPC), (2) ocenia nowość **na podstawie dokumentów, które znalazł nasz kod**. To jest dokładnie odpowiedź na „nie AI wrapper”.

### 3.3 Pułapki, o których trzeba powiedzieć wprost (i pokazać w UI)
1. **Zgłoszenia patentowe są niewidoczne przez 18 miesięcy** od daty zgłoszenia (publikacja po 18 mies.). „Patent w trakcie” wykryjemy tylko, jeśli zgłoszenie już opublikowano. Tego nie da się obejść żadną bazą; trzeba to napisać w ograniczeniach i w karcie („sprawdzono publikacje do dnia X”).
2. **Brak trafień ≠ nowość.** Wynik zależy od pokrycia korpusu. Karta musi pokazywać „sprawdzono w: N źródłach, M dokumentach, zakres lat”.
3. **Procenty muszą coś znaczyć.** Podobieństwo tekstowe i % pokrycia tekstu są mierzalne; „innowacyjność 73%” z LLM jest losowa, jeśli nie stoi za nią rubryka. Progi (np. kopia ≥ 60%) kalibrujemy na zestawie testowym i pokazujemy jury.
4. **Język.** Zgłoszenia są po polsku, patenty EPO i większość publikacji po angielsku. BM25 nie przeskoczy języka: potrzebne tłumaczenie zapytania (DeepSeek, tanio) albo embeddingi wielojęzyczne (podejście B).
5. **Poufność.** Niepubliczny pomysł wysłany do zewnętrznego API to ryzyko dla twórcy (ujawnienie przed zgłoszeniem patentowym). Potrzebna decyzja (D4) i informacja w formularzu.
6. **Zabezpieczenia anty-botowe.** Nie obchodzimy ich (Incapsula, Cloudflare, proof-of-work). Źródła za nimi idą do sekcji „integracja przez API/umowę” jako plan wdrożenia.
7. **Dane osobowe.** Komórka „16–30” wymaga wieku twórcy; nie zgadujemy go z tekstu. Wiek (przedział) tylko z formularza, deklaratywnie.

### 3.4 Źródła: sprawdzone dziś (21.11, ok. 14:58, curl z identyfikującym User-Agent)

| Źródło | Wynik | Do czego | Decyzja |
|---|---|---|---|
| Mapa Dotacji (na dysku): Podkarpacie 20 069, Polska ok. 325 tys. | ✅ lokalnie | kopia / dublowanie prac (projekty już sfinansowane) | **bierzemy** |
| Lista projektów FE 2014–2020 (103 829), Kohesio 2021–27 | ✅ lokalnie | jw. | **bierzemy** |
| Wpisy szkół (7 061) + karty (3 131) | ✅ lokalnie | kandydaci (radar) + kopia między szkołami | **bierzemy** |
| Interreg: `Wykaz_projektow_Interreg_2021-2027_art_49_CPR_20261116.xlsx` | ✅ plik do pobrania | dublowanie prac (źródło z treści zadania) | **bierzemy** |
| RAD-on (OPI) `opendata/polon/projects` | ✅ bez klucza, abstrakty PL/EN, słowa kluczowe | projekty naukowe (komórka „naukowcy”), kopia | **bierzemy** |
| RAD-on / dane.gov.pl zbiór 294 „Patenty i prawa ochronne” (uczelnie) | ⚠️ zbiór istnieje, endpointu API nie znalazłem | patenty uczelni PL | do ustalenia (30 min) |
| CORDIS (projekty UE) | ✅ JSON | dublowanie prac w UE | warto |
| Crossref | ✅ bez klucza | publikacje (metadane, czasem abstrakt) | warto |
| OpenAlex | ⚠️ 429 anonimowo, „use a free API key” | publikacje z abstraktami, filtr PL | darmowy klucz (D5) |
| **EPO OPS** (Open Patent Services) | ⚠️ 403 bez klucza; darmowa rejestracja | **patenty i opublikowane zgłoszenia, także polskie (PL) w DOCDB** → główne źródło filtra „patent” | klucz (D5); pokrycie PL sprawdzić po rejestracji |
| UPRP e-wyszukiwarka | ❌ Incapsula (ochrona przed botami) | patenty PL | nie obchodzimy; PL przez EPO OPS; w planie wdrożenia: eksport/API od UPRP |
| EPO Register (regviewer) | ❌ Cloudflare challenge | status zgłoszeń EP | zamiast tego OPS (ma endpoint register) |
| PBN API | ⚠️ 403, wymaga tokenu aplikacji | publikacje PL | plan wdrożenia (token instytucjonalny) |
| PPM (ppm.edu.pl) | ❌ robots.txt: `Disallow: /` (+ timeout) | publikacje medyczne | nie pobieramy |
| dLibra PAN (czasopisma) | ⚠️ OAI-PMH `Identify` działa, `ListRecords` za proof-of-work „High Load” | publikacje PAN | spróbować później; nie obchodzić |
| BazTOL | ✅ HTML 200 (stary interfejs) | publikacje techniczne | jeśli zostanie czas |
| NCBR „wyszukiwarka sukcesów” | ✅ strony gov.pl (wolne, ok. 900 KB, timeouty) | projekty B+R | jeśli zostanie czas |
| Lens.org | ❌ 401, klucz | patenty | nie |

## 4. Podejścia (jak zbudować silnik oceny)

| | A. Lejek: indeks + reguły, AI na końcu (**rekomendacja**) | B. A + lokalne embeddingi wielojęzyczne | C. AI na wszystkim |
|---|---|---|---|
| Jak | SQLite FTS5 (BM25) na wspólnym korpusie; MinHash/8-gramy dla kopii i plagiatu; DeepSeek: zapytanie PL→EN + IPC, potem ocena nowości na top-k | jak A, plus wektory (np. `multilingual-e5-small`, ok. 120 MB) i szukanie po znaczeniu | LLM czyta zgłoszenie i „ocenia innowacyjność” |
| Plus | zero ciężkich zależności (jak reszta repo: stdlib), wyjaśnialne, tanie, szybkie | łapie kopię pomysłu innymi słowami i po angielsku bez tłumaczenia | najszybsze do napisania |
| Minus | parafraza i inny język łapane gorzej (łata: tłumaczenie zapytania) | torch + pobranie modelu, liczenie wektorów dla 300+ tys. dokumentów na CPU (godziny); trudniej wyjaśnić „dlaczego 81%” | dokładnie to, czego mentorzy **nie chcą**; zmyślone linki |
| Werdykt | start | rozszerzenie, jeśli zostanie czas (np. tylko Podkarpacie + patenty) | odrzucone |

## 5. Proponowana ścieżka budowy (do zatwierdzenia)

Założenie: ok. 14 h pracy nad PCI do niedzieli 06:00 (zamrożenie), potem materiały do 11:00. Jeśli równolegle idzie MFiPR, skracamy od końca listy MUST.

| Faza | Co | Wynik | Czas |
|---|---|---|---|
| 0 | Porządek: prawdziwe daty, sekcja „Przygotowane przed hackathonem”, licencja **EUPL-1.2** (wymóg regulaminu §1 pkt 10), specyfikacja | README, LICENSE, `docs/superpowers/specs/…` | 0,5 h |
| 1 | **Korpus**: wspólny schemat `dokument(id, zrodlo, typ[patent/publikacja/projekt/wpis], tytul, opis, rok, instytucja, link, status, jezyk)` → `dane/korpus.sqlite` z FTS5. Ładowarki: Mapa Dotacji, FE, Kohesio, wpisy szkół, Interreg, RAD-on, CORDIS; EPO OPS po kluczu | `radar/korpus.py` + licznik dokumentów na źródło | 2,5 h |
| 2 | **Silnik deterministyczny**: top-k BM25, MinHash (kopia), 8-gramy z fragmentami (plagiat), patenty ze statusem; testy na podłożonych kopiach | `radar/sprawdz.py` | 2 h |
| 3 | **Warstwa AI** (DeepSeek przez OpenRouter, `data_collection: deny`): (a) zapytanie PL→EN + IPC, (b) rubryka nowości z ID dokumentów sprawdzanymi kodem | `radar/nowosc.py` | 1,5 h |
| 4 | **Werdykt i routing**: odrzuć / do weryfikacji / dalej; powód + link; komórka PCI (16–30 / naukowcy / inni / ogólne); następny krok | reguły w jednym pliku, czytelne dla jury | 1 h |
| 5 | **UI**: formularz zgłoszenia (wklej opis lub link), lista z filtrami (komórka, werdykt, źródło), karta z 4 wskaźnikami i linkami, przycisk „odrzuć / przekaż”; API JSON | serwer lokalny | 3 h |
| 6 | **Walidacja**: zestaw testowy (10 podłożonych kopii z Mapy Dotacji, 5 znanych patentów, 2 prawdziwe przypadki od mentorów, 50 ręcznie oznaczonych wpisów) → trafność, czas sprawdzenia, koszt | tabela miar do PDF | 1,5 h |
| 7 | Materiały: README (źródła, założenia, ograniczenia), PDF ≤ 10 slajdów, film ≤ 3 min | zgłoszenie | 3–4 h |

Demo (2 przypadki, jak w sekcji 6 zadania):
- **A, odrzucenie z dowodem:** zgłoszenie, które jest przeróbką istniejącego projektu z Mapy Dotacji i ma podobny patent → czerwone wskaźniki, 3 linki, „odrzuć” w 1 minutę zamiast godziny szukania.
- **B, przejście dalej:** uczniowski projekt z radaru (np. filtr mikroplastiku z ZST Jasło) → brak kopii, brak patentu, nowość z uzasadnieniem → komórka „młodzi 16–30” → następny krok.

## 6. Szkic karty sprawdzenia

```text
┌ Filtr mikroplastiku „skrzela ryb” · ZST Jasło · komórka: młodzi 16–30 ────────┐
│ Werdykt: DALEJ (do weryfikacji przez analityka)                               │
│ Kopia      ▓▓░░░░░░░░ 18%  najbliższy: Mapa Dotacji #… (2019) ↗               │
│ Plagiat    ░░░░░░░░░░  0%  brak wspólnych fragmentów                          │
│ Patent     ▓▓▓▓░░░░░░ 41%  EP… „Biomimetic filter…” · zgłoszenie opubl. ↗      │
│ Nowość     ▓▓▓▓▓▓▓░░░ 4/5  nowe względem EP…: przepływ bez wkładu, koszt…     │
│ Sprawdzono: 7 źródeł · 412 318 dokumentów · patenty publikowane do 05.2025    │
│ [Odrzuć ▾ powód]  [Przekaż do komórki]  [Eksport JSON]                         │
└────────────────────────────────────────────────────────────────────────────────┘
```
(liczby i numery w szkicu są przykładowe)

## 7. Decyzje do podjęcia

Blokujące (bez nich nie ruszam z kodem):
- **D1. Czas:** ile godzin dajesz PCI, a ile MFiPR? Czy MFiPR nadal idzie?
- **D2. Co jest główne w demo:** ocena zgłoszonego projektu (lejek 4 filtrów), a radar jako źródło kandydatów? *Propozycja: tak.*
- **D3. Odrzucenie:** system odrzuca sam czy tylko rekomenduje, a decyduje człowiek? *Propozycja: rekomenduje + jedno kliknięcie, decyzja zapisana (to później dane do kalibracji).*
- **D4. Poufność:** czy niepubliczne zgłoszenia mogą iść do DeepSeek (OpenRouter, `data_collection: deny`)? *Propozycja: tak, z informacją w formularzu i trybem „bez AI” (same filtry deterministyczne).*
- **D5. Klucze:** zarejestrujesz darmowe konta **EPO OPS** (developers.epo.org) i **OpenAlex**? Wymagają twojego e-maila, więc rejestracja po twojej stronie. Bez OPS filtr patentowy obejmie tylko patenty uczelni (o ile znajdziemy endpoint).
- **D6. Daty i ujawnienie:** poprawiamy README na prawdziwe daty (16–20.11) i opis „przygotowane przed”?

Mogę zdecydować sam (propozycje, popraw, jeśli się nie zgadzasz):
- **D7. Podejście:** A teraz, B (embeddingi) tylko jeśli faza 6 pokaże, że parafrazy uciekają.
- **D8. Komórka 16–30:** pole „przedział wieku twórców” w formularzu; dla radaru szkół: szkoła ponadpodstawowa → 16–30, uczelnia/RAD-on → naukowcy, JST/inne instytucje → inni; ogólne = reszta. (Co dokładnie znaczą „inni” i „ogólne”, trzeba dopytać.)
- **D9. Zakres korpusu:** cała Polska dla kopii i patentów (dublowanie prac nie zna granic województw), Podkarpacie dla radaru.
- **D10. Stack UI:** FastAPI (MIT) + zwykły HTML/JS; automatyczna dokumentacja API pod `/docs` pokazuje „integrację z istniejącymi systemami” (kryterium 5). Alternatywa: sam `http.server` ze stdlib.
- **D11. Progi:** trzy pasma (zielone / żółte / czerwone), kalibrowane na zestawie testowym, pokazane w PDF.

## 8. Dopytać mentorów (krótko, przy następnym podejściu)
1. „Plagiat”: chodzi o przepisany **tekst** (np. opis projektu z cudzej pracy), czy o **pomysł** wzięty od kogoś? (zmienia metodę: 8-gramy vs podobieństwo znaczeniowe)
2. „Kopia”: kopia czego: istniejącego produktu na rynku, projektu już sfinansowanego, czy innego zgłoszenia do PCI?
3. Dokładne nazwy i granice 4 komórek; co trafia do „inni”, a co do „ogólne”?
4. Czy mają 2–3 projekty, które odrzucili (z powodem), i 1–2, które przyjęli? To byłby najlepszy test.
5. Z jakich baz korzystają ręcznie dziś (kolejność ważności)? Czy mają dostęp do PBN/UPRP przez API lub eksport?
6. Czy mogą wysyłać opisy zgłoszeń do zewnętrznego AI (umowy, poufność)?
