# Radar Innowacji (projekt własny, lokalny)

Wyszukuje oddolne inicjatywy w szkołach i placówkach Podkarpacia na podstawie ich publicznych stron WWW.
Projekt rozpoczęty 21.11.2026. **Jeśli jakakolwiek część trafi do zgłoszenia na HackNation, trzeba ją wpisać w sekcji „Przygotowane przed hackathonem”** (FAQ: przygotowane zasoby „rzetelnie wymienić”).

## Przepływ
| Krok | Skrypt | Wynik |
|---|---|---|
| 1. Placówki z Podkarpacia (RSPO, TERYT gminy 18…, współrzędne, strona WWW) | `radar/instytucje.py` | `dane/instytucje.jsonl` |
| 2. Jedna strona na domenę | `radar/wejscie.py` | `dane/wejscie.csv` |
| 3. Źródło wpisów: kanał RSS albo podstrona aktualności | `radar/zrodla.py` | `dane/zrodla.csv` |
| 4. Wpisy: tytuł, data publikacji (+ skąd), link, tekst bez szablonu strony | `radar/wpisy.py` | `dane/wpisy.jsonl` |
| 5. Wstępne sygnały inicjatywy (bez LLM, każdy punkt z dowodem słownym) | `radar/sygnaly.py` | ranking |
| 6. Liczby o Podkarpaciu (FE 2014–2020, Mapa Dotacji, RSPO, pokrycie źródeł) | `radar/liczby.py` | `liczby.md` |
| 7. Widok: mapa placówek + ranking wpisów | `radar/widok.py` | `widok.html` |
| 8. (następny krok, wymaga klucza LLM) karta inicjatywy i ocena potencjału z cytatem | | |

Całość nocą: `radar/noc.sh` (kroki 2–7, wznawialne; log w `dane/logi/`).
Dane źródłowe czytane z `../HackNation 2026/dane_przygotowane/` (tylko odczyt). `dane/` jest poza gitem.

## Stan (21.11.2026)
| Co | Wynik |
|---|---|
| RSPO | **2 921 placówek z Podkarpacia** (TERYT 18), 78% ze stroną WWW; kompletne: 2 921 zapisanych + 1 793 pominiętych (spoza województwa lub prowadzone przez osoby) = 4 714 kandydatów |
| Strony (jedna na domenę) | 1 445: odpowiada 1 279, z tego 1 154 ma RSS albo aktualności; błąd 129 (85 domen nie istnieje, 22× 404, reszta certyfikat/czas, sprawdzone curl-em po ponowieniu); robots.txt 27; obca domena 10 |
| Wpisy | **7 061 z 1 008 szkół** (87% szkół ze źródłem); z datą 6 460 (RSS 5 363), z ostatnich 30 dni 4 218; 178 dat odrzuconych jako data szablonu |
| Sygnały | 920 wpisów ≥ 3 pkt, 237 ≥ 5 pkt. Góra rankingu trafna w części (konkursy naukowe, robotyka, granty), ale z szumem (pikniki, wizyty Erasmus, Miesiąc Bibliotek); 3–4 pkt to głównie szum. Oceniane na oko; prawdziwym testem jest 50 wpisów oznaczonych ręcznie |
| Widok | sprawdzony w przeglądarce 21.11 wieczorem: 2 921 punktów, 1 008 zielonych, filtry działają, bez błędów w konsoli, linki tylko http(s), bez tekstu wpisów |
| Kopie przed czyszczeniem | `dane/wpisy_przed_czyszczeniem.jsonl`, `dane/zrodla_przed_czyszczeniem.csv` |

## Poprawki po pierwszym pełnym przebiegu (21.11)
- EduPage: link artykułu otwiera całą listę (ten sam tekst w każdym wpisie) → tekst z opisu RSS, gdy artykuł nic nie daje.
- „Czytaj więcej” jako tekst linku → tytuł z najdłuższego linku pod ten sam adres albo z nagłówka tuż przed linkiem.
- `<base href>` uwzględniany przy składaniu adresów (wcześniej 404).
- Filtr stron technicznych: „rodo” łapało „międzynarodowy” → dopasowanie od początku słowa.
- Domeny przejęte przez obce strony (handel domenami, blogi): lista `OBCE_HOSTY` w `zrodla.py`, dokładna nazwa hosta (szkoły mają strony na `*.webd.pl`).
- Ta sama data we wszystkich ≥ 3 wpisach źródła = data szablonu → usuwana. Tytuły bez „czytaj dalej… na temat:”, „» ”, sklejonych cyfr daty.

## Zasady
- robots.txt sprawdzany dla **każdego** adresu (jeden parser na host). 401/403 na robots.txt traktujemy jako zakaz (ostrożniej niż RFC 9309, który wtedy pozwala); brak pliku = zgoda. 1 zapytanie na sekundę, identyfikujący się User-Agent.
- Błędy sieci nie są ostateczne: ponowne uruchomienie ponawia strony z błędem; gdy RSS zawiedzie albo jest pusty, bierzemy podstronę aktualności.
- TLS weryfikowany. Pobieranie przez systemowy curl, bo wiele stron szkół ma niepełny łańcuch certyfikatów (np. Certum), którego Python nie uzupełnia; przy błędzie próbujemy domeny bez `www.`.
- Dane osobowe: z RSPO tylko pola instytucji (biała lista); placówki prowadzone przez osobę fizyczną pomijamy. Wpisy szkół zawierają imiona uczniów i nauczycieli: surowy tekst zostaje lokalnie w `dane/`, **widok pokazuje tylko tytuł, sygnały i link**, a przyszłe karty inicjatyw nie zawierają nazwisk (kto = instytucja, koło, rola).
- Kanały RSS z deklaracją `<!ENTITY` odrzucamy; w widoku tylko linki http(s); Leaflet z SRI.

## Znane ograniczenia
- Sygnały to dopasowanie słów, nie rozumienie tekstu: „projekt” w ogłoszeniu o kursie też daje punkty. To filtr przed LLM, nie ocena.
- Część adresów WWW w RSPO jest nieaktualna (domeny nie istnieją albo certyfikat na inną nazwę); lista obcych domen jest ręczna.
- 6% wpisów bez daty: część to strony stałe (np. „Proponowany zestaw podręczników”) wzięte z podstrony aktualności.
- Folder jest w Google Drive: nadpisywanie pliku logu w trakcie synchronizacji potrafi przerwać skrypt bez komunikatu, dlatego każdy przebieg pisze do nowego logu.

## Uruchomienie
```bash
python3 radar/instytucje.py          # ok. 80 min, wznawialne
radar/noc.sh                         # reszta
open widok.html
```
Każdy skrypt ma na starcie test `assert`.
