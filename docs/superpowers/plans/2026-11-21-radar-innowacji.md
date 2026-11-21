# Radar Innowacji (PCI): plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publiczna aplikacja, która przyjmuje innowację (formularz albo radar WWW), porządkuje ją w kartę, przepuszcza przez cztery filtry odrzucenia (plagiat, kopia, patent, nowość) z dowodami i procentami, a potem wskazuje komórkę PCI, ścieżkę i partnerów. Każdą pozycję z flagą przegląda człowiek.

**Architecture:** Python. Wspólny korpus dokumentów w SQLite z FTS5 (BM25) zasilany adapterami źródeł. Źródła są dwóch rodzajów: masowe (Mapa Dotacji, Interreg, RAD-on) i na żądanie (Crossref, CORDIS, OpenAlex, EPO OPS). Filtry plagiatu, kopii i patentu są deterministyczne (n-gramy, TF-IDF). DeepSeek przez OpenRouter robi tylko kartę z tekstu, tłumaczenie zapytania, potwierdzenie „ten sam pomysł” i rubrykę nowości. Kod sprawdza, czy model powołuje się na ID z listy. FastAPI udostępnia strony HTML i API JSON.

**Tech Stack:** Python 3.14 (`uv venv`), SQLite FTS5, FastAPI + uvicorn + Jinja2 + python-multipart, httpx, openpyxl, pytest. Wszystkie MIT/BSD, zgodne z EUPL-1.2.

**Spec:** `docs/superpowers/specs/2026-11-21-radar-innowacji-design.md`. Tło i dostępność źródeł: `docs/mentorzy/2026-11-21-mentorzy-analiza-i-plan.md`.

## Global Constraints
- Licencja repo: **EUPL-1.2** (plik `LICENSE`); zależności tylko MIT, BSD lub Apache-2.0.
- Wszystkie dane pobierane 21–22.11.2026. Nie czytamy `../../dane_przygotowane` ani starego prototypu.
- Pobieranie:
  - User-Agent `radar-innowacji-hackathon/0.1 (+repo URL)`, bez e-maila;
  - robots.txt sprawdzany per host;
  - **1 zapytanie na sekundę na host**;
  - TLS weryfikowany;
  - **żadnego obchodzenia Incapsula, Cloudflare ani proof-of-work.**
- AI: OpenRouter, `provider.data_collection = "deny"`, `temperature = 0`, wyjście JSON. Klucze tylko z `.env` (w .gitignore); nigdy w HTML, logach ani repo.
- Dane osobowe:
  - nie zapisujemy nazwisk z RAD-on (`projectManagers`), Crossref ani OpenAlex (autorzy);
  - zapisujemy tylko instytucje oraz zgłaszających patent tak, jak są w źródle;
  - wiek twórców wyłącznie jako przedział z formularza.
- Progi (jedno miejsce: `radar/config.py: PROGI`):
  - plagiat ≥ 30% czerwone, 10–30% żółte;
  - kopia i patent: podobieństwo ≥ 0,6 **i** potwierdzenie AI czerwone, ≥ 0,4 żółte;
  - nowość ≤ 1/5 czerwone, 2/5 żółte;
  - brak dostępu do źródła daje `brak_danych`, nigdy zielone.
- **Własna praca** (ta sama instytucja albo ten sam zgłaszający) nigdy nie daje czerwonego ani żółtego w filtrach kopia i patent. Ustawia `wlasna_praca=True` i ścieżkę „ochrona / licencja”.
- Rubryka nowości, dosłownie:
  - Q1 „Czy zgłoszenie rozwiązuje problem, którego nie rozwiązuje żaden ze znalezionych dokumentów?”
  - Q2 „Czy używa innej metody lub technologii niż znalezione dokumenty?”
  - Q3 „Czy celuje w innego odbiorcę albo kontekst (np. instytucje publiczne, region)?”
  - Q4 „Czy opisuje mierzalną przewagę (koszt, czas, skala)?”
  - Q5 „Czy to nie jest rutyna (wydarzenie, zakup sprzętu, udział w konkursie, szkolenie)?”
- Typy innowacji (sekcja 1 zadania): `techniczna | organizacyjna | edukacyjna | spoleczna | procesowa`.
- Organizacje: profile JSON w `konfiguracja/organizacje/` (`pci`, `ogolny`). Komórki PCI: `mlodzi_16_30 | naukowcy | inni | ogolne`. Zgłoszenie ma pole `organizacja` (slug, domyślnie `ogolny`).
- Publiczna strona:
  - limit 5 zgłoszeń na IP na godzinę i 200 na dobę łącznie;
  - na kluczu OpenRouter jest limit 20 $ na miesiąc (sprawdzone 21.11);
  - zgłoszenia z formularza oznaczone „demo”;
  - informacja, że opis analizuje model AI.
- Praca na gałęzi `budowa`, scalenie do `main` przed zgłoszeniem.

## Review Focus
1. **Za krótki lub pusty opis** (np. 20 znaków, same spacje): błąd walidacji w formularzu i w API (422), bez wywołania AI ani zapisu. Test w zadaniu 9.
2. **Brak klucza albo źródło nie odpowiada** (EPO OPS bez klucza, timeout CORDIS): filtr dostaje `brak_danych` z uwagą, karta i werdykt nadal się liczą, strona się nie wywraca. Testy w zadaniach 5 i 8.
3. **Złośliwy tekst** (`<script>`, `javascript:` w linku) w zgłoszeniu albo w danych źródła: wszystko escapowane, linki inne niż http(s) pomijane. Test w zadaniu 9.
4. **Błędna odpowiedź AI** (nie-JSON, brak kluczy, ID spoza listy znalezionych): odpowiedź zamieniona na „nie wiadomo” lub „brak danych”, bez wyjątku na zewnątrz. Testy w zadaniach 4 i 6.
5. **To samo zgłoszenie wysłane dwa razy** (podwójny klik jury): drugie ma plagiat ≈ 100% wobec pierwszego. Ta sama instytucja i plagiat ≥ 90% to **duplikat zgłoszenia** (czerwone, „duplikat”), a nie „własna praca”. Test w zadaniu 6.

---

## Struktura plików
```text
pyproject.toml, LICENSE (EUPL-1.2), .env.example, README.md, Dockerfile
radar/config.py        ścieżki, PROGI, UA, MODEL, wczytanie .env
radar/model.py         dataclassy Dokument, Zgloszenie, WynikFiltra, Rekomendacja
radar/db.py            schemat SQLite + FTS5 + df, zapis/odczyt, wyszukiwanie BM25
radar/tekst.py         normalizacja, tokeny, n-gramy, TF-IDF, fragmenty plagiatu
radar/siec.py          grzeczne pobieranie (robots, 1 rps/host, UA, ponowienia)
radar/ai.py            klient OpenRouter + 6 funkcji AI
radar/zrodla/{mapadotacji,interreg,radon,crossref,cordis,openalex,epo}.py
radar/zrodla/www.py    radar: RSS / aktualności → kandydaci
radar/instytucje.py    normalizacja nazw, ta_sama_instytucja()
radar/filtry.py        plagiat(), kopia(), patent(), nowosc()
radar/werdykt.py       werdykt(), komorka(), sciezka(), partnerzy()
radar/sprawdz.py       orkiestracja jednego zgłoszenia
radar/app.py, radar/templates/*.html, radar/static/styl.css
radar/cli.py           python -m radar.cli {pobierz,radar,sprawdz,zestaw,raport}
konfiguracja/zrodla_www.csv   źródła radaru (nazwa,typ_instytucji,url,rss)
walidacja/zestaw.py, walidacja/raport.py
testy/test_*.py, testy/dane/*.json   (małe próbki odpowiedzi API zapisane dziś)
```

## Wspólne typy (`radar/model.py`), na nich opierają się wszystkie zadania
```python
@dataclass
class Dokument:
    id: str                 # "<zrodlo>:<id_w_zrodle>", np. "mapadotacji:1855670"
    zrodlo: str             # mapadotacji|interreg|radon|crossref|cordis|openalex|epo|www|zgloszenie
    typ: str                # projekt|publikacja|patent|wpis|zgloszenie
    tytul: str
    opis: str
    link: str
    rok: int | None = None
    instytucje: list[str] = field(default_factory=list)
    wojewodztwo: str | None = None
    status: str | None = None      # patent: "udzielony"|"zgloszenie"
    jezyk: str = "pl"              # "pl"|"en"|"inny"

@dataclass
class Zgloszenie:
    id: int | None
    wejscie: str            # "formularz"|"radar"
    tytul: str
    opis: str
    link: str | None
    instytucja: str
    typ_instytucji: str     # szkola_podstawowa|szkola_ponadpodstawowa|uczelnia|instytut|jst|inna_publiczna|firma|osoba_grupa
    typ_innowacji: str      # patrz Global Constraints
    etap: str               # pomysl|prototyp|wdrozone|zakonczone
    wiek_przedzial: str     # ponizej_16|16_30|powyzej_30|mieszany|nie_podano
    opis_en: str | None = None
    cytat: str | None = None       # radar: dowód z tekstu źródła
    demo: bool = False
    organizacja: str = "ogolny"    # slug profilu z konfiguracja/organizacje/

@dataclass
class WynikFiltra:
    filtr: str              # plagiat|kopia|patent|nowosc
    procent: float | None   # None = brak danych
    pasmo: str              # zielone|zolte|czerwone|brak_danych
    dowody: list[dict]      # {dokument_id, tytul, link, podobienstwo?, fragmenty?, ocena_ai?, uzasadnienie?}
    uwaga: str = ""
    wlasna_praca: bool = False

@dataclass
class Rekomendacja:
    nazwa: str
    powod: str
    reguly: list[str]
```

---

### Task 1: Szkielet, licencja, baza i wyszukiwanie
**Files:** Create `pyproject.toml`, `LICENSE`, `.env.example`, `radar/__init__.py`, `radar/config.py`, `radar/model.py`, `radar/db.py`, `testy/test_db.py`

**Interfaces – Produces:**
- `db.polacz(sciezka: Path | None = None) -> sqlite3.Connection`: tworzy schemat, gdy go brak. Tabele: `dokument`, `dokument_fts` (FTS5 `tytul, opis`, `tokenize='unicode61 remove_diacritics 2'`), `df(termin TEXT PRIMARY KEY, liczba INT)`, `zgloszenie`, `wynik` (z `czas_s REAL`, `koszt_usd REAL`), `decyzja`.
- `db.zapisz_dokumenty(con, docs: list[Dokument]) -> int`: upsert po `id`, aktualizuje FTS i `df`.
- `db.szukaj(con, terminy: list[str], limit: int = 50, typ: str | None = None) -> list[tuple[Dokument, float]]`: BM25, zapytanie `"t1"* OR "t2"* …`.
- `db.dokument(con, id) -> Dokument | None`; `db.liczba_dokumentow(con) -> dict[str, int]` (na źródło).
- `db.funkcja_df(con) -> tuple[Callable[[str], int], int]`: (df dla rdzenia z tabeli `df`, N = liczba dokumentów). Używają tego filtry kopii i patentu.
- `db.zapisz_zgloszenie(con, z) -> int`; `db.zgloszenie(con, id) -> Zgloszenie`.
- `db.zapisz_wyniki(con, zgl_id, wyniki: list[WynikFiltra], werdykt: str, komorka: str, rekomendacje: list[Rekomendacja], partnerzy: list[str], czas_s: float, koszt_usd: float)`; `db.karta(con, zgl_id) -> dict`.
- `db.zapisz_decyzje(con, zgl_id, decyzja: str, powod: str)`.

- [ ] **Krok 1:** Środowisko:
  - `git switch -c budowa`;
  - `uv venv .venv && uv pip install fastapi uvicorn jinja2 python-multipart httpx openpyxl pytest`;
  - zależności wpisz do `pyproject.toml`;
  - `LICENSE` = tekst z `https://raw.githubusercontent.com/spdx/license-list-data/main/text/EUPL-1.2.txt`;
  - `.env.example` z pustymi `OPENROUTER_API_KEY, EPO_OPS_KEY, EPO_OPS_SECRET, OPENALEX_API_KEY`.
- [ ] **Krok 2: Testy**
  - `test_szukaj_zwraca_trafny_dokument_pierwszy`: 3 dokumenty, zapytanie `["mikroplast","filtr"]`, pierwszy wynik ma id `"t:2"`;
  - `test_zapis_idempotentny`: dwa zapisy tego samego id, `liczba_dokumentow == {"t": 3}`;
  - `test_diakrytyki`: `szukaj(["zrodl"])` znajduje „źródło”.
- [ ] **Krok 3:** Uruchom `pytest testy/test_db.py -v`. Oczekiwany wynik: FAIL.
- [ ] **Krok 4:** Implementacja `config.py`, `model.py` i `db.py` według Interfaces. `config.wczytaj_env()` czyta `.env` bez zależności.
- [ ] **Krok 5:** `pytest testy/test_db.py -v`: PASS.
- [ ] **Krok 6:** Commit, razem z usunięciem starego prototypu i `docs/`: `git add -A && git commit -m "Szkielet: baza dokumentów z FTS5, licencja EUPL-1.2; usunięty wcześniejszy prototyp"`.

### Task 2: Tekst: normalizacja, n-gramy, TF-IDF, fragmenty plagiatu
**Files:** Create `radar/tekst.py`, `testy/test_tekst.py`

**Interfaces – Produces:**
- `tokeny(t: str) -> list[str]`: małe litery, bez diakrytyków, tylko `[a-z0-9]+`.
- `rdzen(token: str) -> str`: `token[:6]` dla długości > 6, inaczej bez zmian.
- `STOP: frozenset[str]`: około 150 polskich i angielskich słów funkcyjnych.
- `terminy(t: str, n: int = 15, df: Callable[[str], int] | None = None, N: int = 1) -> list[str]`: najwyższe tf·idf rdzeni spoza `STOP`.
- `podobienstwo(a: str, b: str, df: Callable[[str], int], N: int) -> float`: cosinus TF-IDF na rdzeniach, `idf = ln((N+1)/(df+1)) + 1`.
- `pokrycie_ngramow(zgl: str, dok: str, n: int = 8) -> tuple[float, list[str]]`: (udział n-gramów zgłoszenia obecnych w dokumencie, scalone fragmenty w **oryginalnej** pisowni zgłoszenia).
- `bez_html(t: str) -> str`.

- [ ] **Krok 1: Testy**
  - `tokeny("Źródło: Filtr-3D!") == ["zrodlo","filtr","3d"]`;
  - `pokrycie_ngramow(A, A)[0] == 1.0`;
  - połowa zdań skopiowana: `0.4 <= pokrycie <= 0.6`, a fragment zawiera skopiowane zdanie w oryginalnej pisowni;
  - `podobienstwo(x, x) ≈ 1.0`; teksty bez wspólnych słów: `0.0`;
  - `terminy` nie zwraca słów z `STOP`.
- [ ] **Krok 2:** FAIL → implementacja → `pytest testy/test_tekst.py -v` PASS.
- [ ] **Krok 3:** Commit `"Tekst: n-gramy, TF-IDF, fragmenty plagiatu"`.

### Task 3: Grzeczne pobieranie i źródła masowe (Mapa Dotacji, Interreg, RAD-on)
**Files:** Create `radar/siec.py`, `radar/zrodla/__init__.py`, `radar/zrodla/{mapadotacji,interreg,radon}.py`, `radar/cli.py` (polecenie `pobierz`), `testy/test_zrodla_masowe.py`, `testy/dane/{mapadotacji_1.json,radon_1.json,interreg_mini.xlsx}`

**Interfaces:**
- Produces: `siec.pobierz(url, *, params=None, headers=None, metoda="GET", dane=None, timeout=30) -> httpx.Response`. Robots per host z pamięcią podręczną, 1 rps na host, 3 ponowienia z backoffem 2/4/8 s przy 429/5xx, rzuca `siec.Zablokowane` przy zakazie w robots.
- Każdy moduł masowy ma `parsuj(surowe) -> list[Dokument]` (czysta funkcja, testowana na próbce) oraz `pobierz_wszystko(con, **opcje) -> int` (wznawialne, zapis partiami po 100).
- Stałe znane z dzisiejszych testów:
  - **Mapa Dotacji:** `https://mapadotacji.gov.pl/wp-json/wp/v2/projekty?wojewodztwa_projekty=327&per_page=100&page=N`, nagłówek `X-WP-Total` = 20 069; pola `id, link, title.rendered, content.rendered, date`; `wojewodztwo="podkarpackie"`; `typ="projekt"`. Beneficjenta nie ma w JSON: `mapadotacji.beneficjent(link) -> str | None` czyta stronę HTML projektu i jest wołane tylko dla dokumentów pokazywanych jako dowody lub partnerzy. Wynik zapisywany w `instytucje`.
  - **Interreg:** XLSX `https://interreg.gov.pl/wp-content/uploads/2026/11/Wykaz_projektow_Interreg_2021-2027_art_49_CPR_20261116.xlsx`, nagłówki w **2. wierszu**, około 258 projektów. Kolumny: `Numer projektu / Project no.` → id, `Tytul projektu / Project title`, `Opis projektu / Project description`, `Data rozpoczęcia realizacji / Project start date` → rok, `Nazwa partnera wiodącego i partnerów / Lead partner and partners name` → `instytucje` (podział po `" | "`), `Województwo lub region / Voivodeship or region ` (ze spacją na końcu). Link = strona listy.
  - **RAD-on:** `https://radon.nauka.gov.pl/opendata/polon/projects?resultNumbers=100`, `pagination.maxCount` = 48 853, kolejna strona przez `token` z `pagination` (parametr `token`, sprawdzić w kroku 1). Opis = `projectAbstractPl` albo `projectAbstractEn`. Tytuł = `projectTitlePl` albo `projectTitleEn`. `instytucje` = `implementingInstitutions[].institutionName`. **Nie zapisujemy `projectManagers`.** Link: `https://radon.nauka.gov.pl/dane/projekty-naukowe?uuid={projectUuid}` (sprawdzić w kroku 1; jeśli nie działa, link do API).

- [ ] **Krok 1:** Zapisz po jednej prawdziwej odpowiedzi do `testy/dane/`. Sprawdź parametr stronicowania RAD-on i link do projektu.
- [ ] **Krok 2: Testy parserów na próbkach.** Mapa Dotacji: `id == "mapadotacji:<id>"`, `opis` bez znaczników HTML. Interreg: `instytucje` ma ≥ 1 element. RAD-on: brak jakiegokolwiek klucza z nazwiskami. Do tego `test_robots_zakaz` na podstawionym robots.txt.
- [ ] **Krok 3:** FAIL → implementacja → PASS.
- [ ] **Krok 4:** Uruchom w tle:
  - `python -m radar.cli pobierz mapadotacji` (około 200 zapytań, około 4 min);
  - `python -m radar.cli pobierz interreg`;
  - `python -m radar.cli pobierz radon` (około 490 zapytań, około 9 min).

  Oczekiwane: `liczba_dokumentow` ≈ {mapadotacji: 20069, interreg: ~258, radon: ~48853}.
- [ ] **Krok 5:** Commit `"Źródła masowe: Mapa Dotacji, Interreg, RAD-on"`.

### Task 4: Klient AI i sześć funkcji
**Files:** Create `radar/ai.py`, `testy/test_ai.py`

**Interfaces – Produces** (każda funkcja zwraca `(wynik, koszt_usd)` i **nigdy nie rzuca wyjątku z powodu złej odpowiedzi**):
- `czat_json(system: str, user: str) -> tuple[dict, float]`: przy błędzie sieci lub JSON zwraca `({}, 0.0)`. Model z `config.MODEL` (domyślnie DeepSeek; dokładne ID sprawdzić w `GET https://openrouter.ai/api/v1/models`).
- `karta_z_tekstu(tytul, tekst) -> dict`: klucze `co, instytucja, typ_innowacji, etap, cytat`; `cytat` zachowany tylko wtedy, gdy `tekst.normalizowany` go zawiera.
- `tlumacz_zapytanie(opis) -> dict`: `{"opis_en": str, "terminy_en": list[str], "ipc": list[str]}`.
- `ten_sam_pomysl(zgl_opis, dokumenty: list[Dokument]) -> dict[str, dict]`: `{dok_id: {"ocena": "ten_sam"|"czesciowo"|"inny", "uzasadnienie": str}}`; ID spoza listy odrzucane.
- `rubryka_nowosci(zgl_opis, dokumenty: list[Dokument]) -> list[dict]`: 5 pozycji `{"pytanie": "Q1".."Q5", "odpowiedz": "tak"|"nie"|"nie_wiadomo", "dokument_id": str|None, "uzasadnienie": str}`; odpowiedź z `dokument_id` spoza listy zamieniana na `nie_wiadomo`.
- `czy_innowacja(tytul, tekst) -> dict`: `{"czy": "tak"|"nie"|"niepewne", "cytat": str}`, z cytatem sprawdzanym jak wyżej.
- `parafrazuj(tekst) -> str`: tylko do zestawu testowego.

- [ ] **Krok 1: Testy z podstawionym `czat_json` (monkeypatch)**
  - ID spoza listy → `nie_wiadomo`;
  - nie-JSON → wynik pusty bez wyjątku;
  - zmyślony cytat → `cytat is None`.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** Test na żywo (`pytest -m zywe`, pomijany bez klucza): `tlumacz_zapytanie("Filtr mikroplastiku inspirowany skrzelami ryb")` zwraca niepuste `terminy_en`.
- [ ] **Krok 4:** Commit `"AI: OpenRouter, karta, tłumaczenie, rubryka nowości z kontrolą ID"`.

### Task 5: Źródła na żądanie (Crossref, CORDIS, OpenAlex, EPO OPS)
**Files:** Create `radar/zrodla/{crossref,cordis,openalex,epo}.py`, `testy/test_zrodla_zadanie.py`, próbki w `testy/dane/`

**Interfaces:**
- Produces: każdy moduł ma `szukaj(terminy_en: list[str], limit: int = 20) -> list[Dokument]` i rzuca `zrodla.BrakDostepu(powod)`, gdy nie ma klucza albo źródło nie odpowiada. Wyniki zapisuje do `dokument` (pamięć podręczna), `jezyk="en"`.
- **Crossref:** `https://api.crossref.org/works?query.bibliographic=…&rows=20`; bez autorów; `instytucje` = `publisher`.
- **CORDIS:** `https://cordis.europa.eu/search/en?q=…&format=json` (strukturę ustalić na próbce z kroku 1).
- **OpenAlex:** `https://api.openalex.org/works?search=…&per_page=20&api_key=…`; abstrakt odbudowany z `abstract_inverted_index`; `instytucje` = `authorships[].institutions[].display_name`; bez nazwisk autorów.
- **EPO OPS:**
  - token OAuth: `POST https://ops.epo.org/3.2/auth/accesstoken` (client_credentials z `EPO_OPS_KEY:EPO_OPS_SECRET`);
  - wyszukiwanie: `GET https://ops.epo.org/3.2/rest-services/published-data/search/biblio?q=ta all "…"` z nagłówkiem `Range: 1-25`;
  - `id = "epo:{kraj}{numer}{kod}"`; status: kod zaczyna się od `B` → `udzielony`, od `A` → `zgloszenie`;
  - `instytucje` = zgłaszający (applicants);
  - link: `https://worldwide.espacenet.com/patent/search?q=pn%3D{kraj}{numer}{kod}`.

- [ ] **Krok 1:** Zapisz próbki odpowiedzi; EPO tylko wtedy, gdy są klucze. Jeśli ich nie ma, test parsera EPO na próbce z dokumentacji OPS.
- [ ] **Krok 2: Testy parserów**
  - `test_epo_status`: kod B1 → `udzielony`, A1 → `zgloszenie`;
  - `test_openalex_abstrakt_z_indeksu`;
  - `test_brak_klucza_rzuca_BrakDostepu` (EPO, OpenAlex).
- [ ] **Krok 3:** FAIL → implementacja → PASS.
- [ ] **Krok 4:** Commit `"Źródła na żądanie: Crossref, CORDIS, OpenAlex, EPO OPS"`.

### Task 6: Instytucje i cztery filtry
**Files:** Create `radar/instytucje.py`, `radar/filtry.py`, `testy/test_filtry.py`

**Interfaces:**
- Consumes: `tekst.*`, `ai.ten_sam_pomysl`, `ai.rubryka_nowosci`, `config.PROGI`.
- Produces:
  - `instytucje.normalizuj(n: str) -> frozenset[str]`: tokeny bez form prawnych i słów `sp, z, o, im, w, i`;
  - `instytucje.ta_sama(a: str, b: list[str]) -> bool`: Jaccard ≥ 0,6 albo zawieranie przy ≥ 3 tokenach;
  - `filtry.plagiat(z: Zgloszenie, kandydaci: list[Dokument]) -> WynikFiltra`;
  - `filtry.kopia(z, kandydaci, df, N) -> WynikFiltra`: liczy tylko `typ in {projekt, wpis, zgloszenie}`; dla `jezyk="en"` porównuje `z.opis_en`; AI tylko dla top-3 z podobieństwem ≥ 0,4;
  - `filtry.patent(z, kandydaci, df, N, dostepne: bool) -> WynikFiltra`: przy `dostepne=False` pasmo `brak_danych` z uwagą „EPO OPS niedostępne”. Zawsze dopisuje uwagę: „Zgłoszenia patentowe są publikowane po 18 miesiącach; młodszych nie widać.”;
  - `filtry.nowosc(z, kandydaci) -> WynikFiltra`: `procent = 100 * liczba_tak / 5`; same `nie_wiadomo` → `brak_danych`.
- Reguły:
  - własna praca: kandydat z `ta_sama(z.instytucja, d.instytucje)` nie podnosi pasma, a ustawia `wlasna_praca=True`;
  - wyjątek (duplikat): `d.zrodlo == "zgloszenie"`, ta sama instytucja i plagiat ≥ 90% → czerwone, `uwaga="duplikat zgłoszenia"`.

- [ ] **Krok 1: Testy** (AI podstawione)
  - plagiat 50% skopiowany od obcej instytucji → `czerwone`, a `dowody[0]["fragmenty"]` nie jest puste;
  - ten sam tekst od tej samej instytucji z `zrodlo="mapadotacji"` → `wlasna_praca=True`, pasmo `zielone`;
  - duplikat zgłoszenia → `czerwone`, `uwaga == "duplikat zgłoszenia"`;
  - kopia: podobieństwo 0,7 i AI `ten_sam` → `czerwone`; 0,7 i AI `inny` → `zolte`;
  - patent `dostepne=False` → `brak_danych`;
  - nowość: 1×tak → `czerwone`, 2×tak → `zolte`, 4×tak → `zielone`;
  - `ta_sama("Politechnika Rzeszowska im. Ignacego Łukasiewicza", ["POLITECHNIKA RZESZOWSKA"]) is True`.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** Commit `"Filtry: plagiat, kopia, patent, nowość; reguła własnej pracy i duplikatu"`.

### Task 7: Werdykt, profile organizacji, komórka, ścieżka, partnerzy
**Files:** Create `radar/werdykt.py`, `radar/organizacje.py`, `konfiguracja/organizacje/{pci,ogolny}.json`, `testy/test_werdykt.py`

Profil JSON: `{"slug","nazwa","opis","komorki":[{"id","nazwa","gdy":{"wiek_przedzial":[...],"typ_instytucji":[...]}}],"komorka_domyslna","sciezki":{"R1":"tekst rekomendacji dla tej organizacji", ...}}`. `organizacje.wczytaj(slug) -> dict` (nieznany slug → `ogolny`), `organizacje.lista() -> list[dict]`.

**Interfaces – Produces:**
- `werdykt(wyniki: list[WynikFiltra]) -> str`: jakiekolwiek `czerwone` → `"odrzucone_do_przegladu"`; jakiekolwiek `zolte` → `"do_przegladu"`; inaczej `"dalej"`.
- `komorka(z: Zgloszenie, profil: dict) -> str`: reguły `gdy` z profilu, pierwsza pasująca. Profil `pci` zapisuje dokładnie te reguły: `16_30` albo `szkola_ponadpodstawowa` → `mlodzi_16_30`; `uczelnia|instytut` → `naukowcy`; `jst|inna_publiczna|szkola_podstawowa` → `inni`; reszta → `ogolne`.
- `sciezka(z, wyniki, podobne: list[Dokument], profil: dict) -> list[Rekomendacja]`. Tekst rekomendacji z `profil["sciezki"][Rn]`, a gdy go brak, tekst domyślny. Reguły, każda z nazwą w `reguly`:
  - **R1** `techniczna` i etap `prototyp|wdrozone` i nowość `zielone` → „Akceleracja PCI / prototypowanie w Protolab”.
  - **R2** nowość ≥ 80% i patent `zielone` albo `wlasna_praca` → „Ochrona: rozważ zgłoszenie patentowe (UPRP) lub licencję”.
  - **R3** typ `organizacyjna|edukacyjna|spoleczna|procesowa` i brak `czerwone` → „Transfer do instytucji tego samego typu”.
  - **R4** wśród `podobne` są projekty z Mapy Dotacji lub Interreg → „Finansowanie: programy podobnych projektów”, z listą 3 tytułów i linków.
  - **R5** kopia `zolte` i nie `wlasna_praca` → „Współpraca zamiast dublowania: skontaktuj się z autorem podobnego projektu”.
  - Werdykt `odrzucone_do_przegladu` → tylko „Do przeglądu analityka: powody odrzucenia z linkami”.
- `partnerzy(z, podobne) -> list[str]`: do 5 różnych instytucji z `podobne`, z pominięciem własnej (`instytucje.ta_sama`).

- [ ] **Krok 1: Testy**
  - po jednym przypadku na każdą regułę R1–R5;
  - `komorka` dla 4 komórek;
  - `partnerzy` pomija własną instytucję.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** Commit `"Werdykt, komórki PCI, ścieżki i partnerzy"`.

### Task 8: Orkiestracja sprawdzenia
**Files:** Create `radar/sprawdz.py`, rozszerz `radar/cli.py` (`sprawdz <id>`), `testy/test_sprawdz.py`

**Interfaces:**
- Consumes: wszystko powyżej.
- Produces: `sprawdz(con, zgl_id: int) -> dict` (karta jak w `db.karta`). Kolejność:
  1. `ai.tlumacz_zapytanie` → zapisuje `opis_en`;
  2. `tekst.terminy` (PL) → `db.szukaj` top-50;
  3. każde źródło na żądanie z `terminy_en`, ze złapaniem `BrakDostepu` (zapamiętuje, które źródła były niedostępne);
  4. do kandydatów dołącza wcześniejsze zgłoszenia jako dokumenty `zrodlo="zgloszenie"`;
  5. cztery filtry; `nowosc` dostaje top-10 kandydatów według podobieństwa;
  6. werdykt, komórka, ścieżka, partnerzy (`mapadotacji.beneficjent` tylko dla pokazywanych);
  7. `db.zapisz_wyniki` z czasem i sumą kosztów AI;
  8. karta zawiera `pokrycie = {"zrodla": [...], "dokumentow": N, "niedostepne": [...]}`.

- [ ] **Krok 1: Testy na małej bazie z podstawionym AI i źródłami**
  - `test_przeplyw_odrzucenia`: zgłoszenie skopiowane z dokumentu → werdykt `odrzucone_do_przegladu`, dowód z linkiem;
  - `test_przeplyw_bez_epo`: patent `brak_danych`, werdykt policzony, `"epo" in karta["pokrycie"]["niedostepne"]`.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** Na żywo, na prawdziwej bazie: `python -m radar.cli sprawdz` na ręcznie wstawionym zgłoszeniu. Karta ma 4 wyniki, czas < 90 s, koszt < 0,05 $.
- [ ] **Krok 4:** Commit `"Sprawdzenie zgłoszenia od wyszukiwania do werdyktu"`.

### Task 9: Aplikacja WWW i API
**Files:** Create `radar/app.py`, `radar/templates/{baza,zglos,kolejka,karta,miary}.html`, `radar/static/styl.css`, `testy/test_app.py`

**Interfaces – Produces:**
- `GET /` → przekierowanie na `/kolejka`.
- `GET|POST /zglos`: pola z `Zgloszenie`. Walidacja: tytuł 5–200 znaków, opis 300–8000 znaków, typy ze słowników. Po zapisie sprawdzenie w tle (`BackgroundTasks`), przekierowanie na `/karta/{id}` z autoodświeżaniem, dopóki wynik nie jest gotowy.
- `GET /kolejka?werdykt=&komorka=&wejscie=` (katalog wszystkich) i `GET /o/{slug}/kolejka` (kolejka organizacji): najpierw `odrzucone_do_przegladu`, potem `do_przegladu`.
- `GET /szukaj?q=` i `GET /api/szukaj?q=`: `tekst.terminy` + `db.szukaj` po korpusie i zgłoszeniach (bez wywołań AI, więc tanio), wyniki pogrupowane według typu, z instytucją i pasmami filtrów dla zgłoszeń. Test: zapytanie z tytułu istniejącego zgłoszenia zwraca je na pierwszym miejscu.
- Formularz `/zglos` ma pole „Do kogo kierujesz” (lista z `organizacje.lista()`).
- `GET /karta/{id}`:
  - 4 paski (procent, pasmo, kolor);
  - dowody: linki i fragmenty obok siebie (`<mark>`);
  - linia pokrycia;
  - komórka, rekomendacje z regułami, partnerzy;
  - formularz decyzji: `potwierdz_odrzucenie|przywroc|przekaz` + powód.
- `POST /zglos/z-linku` (pole `link`): `siec.pobierz` + `tekst.bez_html` + `ai.karta_z_tekstu`, a potem formularz wypełniony do poprawienia przez człowieka (spec §6.1: karta z linku).
- `POST /karta/{id}/decyzja`, `GET /miary`.
- `/api/zgloszenia` (GET, POST), `/api/karta/{id}`; OpenAPI pod `/docs`.
- Limit: 5 POST na IP na godzinę i 200 na dobę (w pamięci), przekroczenie → 429 z komunikatem po polsku.
- Jinja2 z autoescape. Linki renderowane tylko przy schemacie `http(s)`. Formularz zawiera stałą informację: „Opis zgłoszenia jest analizowany przez model AI (DeepSeek przez OpenRouter, bez trenowania na danych).”

- [ ] **Krok 1: Testy (TestClient)**
  - opis 20 znaków → 422, bez zapisu;
  - zgłoszenie z `<script>alert(1)</script>` w tytule → na karcie `&lt;script&gt;`;
  - link `javascript:alert(1)` nie trafia do HTML jako href;
  - szósty POST z tego samego IP w godzinie → 429;
  - `/api/karta/{id}` zwraca JSON z kluczami `wyniki, werdykt, komorka, rekomendacje, partnerzy, pokrycie`.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** `uvicorn radar.app:app --port 8000`; przejdź w przeglądarce formularz → karta → decyzja. W konsoli nie ma błędów.
- [ ] **Krok 4:** Commit `"Aplikacja: formularz, kolejka, karta z dowodami, decyzje, API"`.
- [ ] **Krok 5 (punkt kontrolny):** Draft w HackTribe przed 20:00: tytuł, opis, link do repo.

### Task 10: Radar WWW (automatyczne wykrywanie)
**Files:** Create `konfiguracja/zrodla_www.csv`, `radar/zrodla/www.py`, rozszerz `radar/cli.py` (`radar`), `testy/test_www.py`

**Interfaces:**
- Produces:
  - `www.znajdz_kanal(html: str, url: str) -> str | None`: `<link rel="alternate" type="application/rss+xml|atom">`, a w drugiej kolejności `/feed`, `/rss`;
  - `www.wpisy_z_kanalu(xml: str) -> list[dict]`: `tytul, link, data, tekst`; odrzuca XML z `<!ENTITY`;
  - `www.wstepny_sygnal(tekst) -> tuple[int, list[str]]`: słowa: `zbudowal|skonstruowal|zaprojektowal|stworzyl|opracowal|wynalaz|prototyp|aplikacj|robot|patent|innowac|autorsk|startup` +2; `laureat|nagrod|finali|grant` +1; `jadlospis|wycieczk|akademi|rekolekc|zebrani|dyzur` −3; próg ≥ 3;
  - `www.uruchom(con, limit_zrodel: int) -> int`: kanały → wpisy z ostatnich 180 dni → sygnał ≥ 3 → `ai.czy_innowacja` → `tak` → `ai.karta_z_tekstu` → `Zgloszenie(wejscie="radar", link=…, cytat=…)` → `sprawdz`.
- `zrodla_www.csv` budowany dziś:
  - uczelnie Podkarpacia, wpisane ręcznie: PRz, UR, PANS Krosno, PANS Przemyśl, PANS Jarosław, WSIiZ;
  - technika, licea i branżowe centra umiejętności z województwa podkarpackiego z RSPO (publiczna wyszukiwarka `rspo.gov.pl`, tylko pola instytucji);
  - PCI;
  - maksymalnie 300 źródeł.

- [ ] **Krok 1: Testy**
  - `znajdz_kanal` na próbce HTML;
  - `wpisy_z_kanalu` odrzuca `<!ENTITY`;
  - `wstepny_sygnal("Uczniowie zbudowali robota, laureaci")[0] >= 3`;
  - `wstepny_sygnal("Jadłospis")[0] < 0`.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** `python -m radar.cli radar --limit 300` w tle. W kolejce pojawiają się zgłoszenia `wejscie=radar`.
- [ ] **Krok 4:** Commit `"Radar WWW: kanały RSS szkół i uczelni Podkarpacia"`.

### Task 11: Zestaw testowy i miary
**Files:** Create `walidacja/zestaw.py`, `walidacja/raport.py`, `walidacja/etykiety.csv` (wypełnia użytkownik), rozszerz `/miary`

**Interfaces – Produces:** `python -m radar.cli zestaw` tworzy zgłoszenia `demo=False` z oznaczeniem `oczekiwane` w tabeli `test`:
- 10 plagiatów: połowa zdań z dokumentu A + połowa z dokumentu B innej instytucji; oczekiwane: plagiat czerwone;
- 10 parafraz z `ai.parafrazuj`; oczekiwane: kopia ≥ żółte;
- 5 opisów z abstraktów EPO (tylko z kluczem, inaczej „nie sprawdzono”); oczekiwane: patent ≥ żółte;
- 20 wpisów do ręcznej etykiety „rutyna / nowość” w `etykiety.csv`: 10 z radaru o najniższym sygnale, 10 sfinansowanych projektów RAD-on.

`python -m radar.cli raport` zapisuje `walidacja/raport.md`: czułość dla każdego filtra, zgodność nowości z etykietami ręcznymi, mediana czasu i kosztu, pokrycie źródeł. Te same liczby pokazuje `/miary`.

- Tabela `test(zgl_id INT, rodzaj TEXT, filtr TEXT, oczekiwane TEXT)` jest tworzona w tym zadaniu (`walidacja/zestaw.py`), a nie w `db.polacz`.

- [ ] **Krok 1:** Test: `raport` na 3 sztucznych wynikach liczy czułość 2/3.
- [ ] **Krok 2:** FAIL → implementacja → PASS.
- [ ] **Krok 3:** Uruchom `zestaw`. Użytkownik wypełnia `etykiety.csv` (około 15 minut). Uruchom `raport`.
- [ ] **Krok 4:** Jeśli czułość kopii na parafrazach < 0,6: skoryguj progi w `PROGI` (zapisz zmianę w raporcie) albo zdecyduj o podejściu B.
- [ ] **Krok 5:** Commit `"Walidacja: zestaw testowy i raport miar"`.

### Task 12: Publikacja i materiały
**Files:** Create `Dockerfile`, `README.md`, `docs/prezentacja/` (PDF ≤ 10 slajdów)

- [ ] **Krok 1:** `Dockerfile` (python:3.14-slim, `uvicorn radar.app:app --host 0.0.0.0 --port 8000`). Plik `dane/radar.sqlite` jest dołączany do obrazu albo montowany jako wolumin, zależnie od hostingu wybranego przez użytkownika. Klucze jako sekrety hostingu.
- [ ] **Krok 2:** Wdrożenie. Sprawdź z zewnątrz: formularz → karta w < 90 s, `/docs` działa, szósty POST → 429.
- [ ] **Krok 3:** `README.md`:
  - problem, rozwiązanie, jak działa;
  - źródła danych z datami pobrania i licencjami;
  - założenia;
  - **ograniczenia**: 18 miesięcy zgłoszeń, źródła zablokowane, brak trafień ≠ nowość;
  - bezpieczeństwo i dane osobowe; skalowanie i integracja (API, konfiguracja źródeł i województwa);
  - uruchomienie;
  - wyniki z `walidacja/raport.md`;
  - wykorzystane AI i biblioteki;
  - zdanie: „Pierwszy commit (394f34c) zawiera wcześniejszy, porzucony prototyp; nie korzystamy z niego.”
- [ ] **Krok 4:** PDF ≤ 10 slajdów według kryteriów z §10 specyfikacji. Film ≤ 3 min: przypadek 1 (formularz → odrzucenie z dowodami) i przypadek 2 (radar → ścieżka i partnerzy).
- [ ] **Krok 5:** Scal `budowa` do `main`. Ostatni commit musi być po ostatniej wersji PDF.
