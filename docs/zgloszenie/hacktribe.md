# Zgłoszenie HackTribe: teksty do wklejenia

Każda sekcja to jedno pole formularza. Liczby: stan na 22.11.2026.

---

**Nazwa projektu:** Radar Innowacji

**Zadanie:** Radar innowacji (Podkarpackie Centrum Innowacji)

**Repozytorium:** https://github.com/Kaarmel/radar-innowacji

**Załącznik PDF:** `docs/prezentacja/radar-innowacji.pdf` (10 slajdów, ok. 2 MB)

---

## Opis rozwiązania

Radar Innowacji sam wyszukuje innowacje w Polsce i ocenia je z dowodami. Decyzję podejmuje człowiek.

**Problem.** Analityk centrum innowacji, takiego jak PCI, dowiaduje się o innowacjach przypadkiem. Opisy giną na stronach
szkół, uczelni i gmin. To, czy projekt jest nowy, czy to nie kopia albo plagiat i czy nie blokuje go patent, sprawdza ręcznie.

**Jak działa.**
1. **Odkrywa:** co godzinę (i na żądanie) sprawdza 172 strony szkół, uczelni i instytucji (125 ma kanał RSS). AI odrzuca wydarzenia, szkolenia i zakupy.
2. **Sprawdza:** 4 filtry odrzucenia (plagiat, kopia pomysłu, patent, nowość) na tle 338 373 dokumentów: projektów z dotacją,
   projektów naukowych i patentów, a do tego EPO, OpenAlex i Crossref na żywo. Każdy wynik ma procent i link do dowodu.
3. **Ocenia:** potencjał 0–100 z jawnego wzoru (nowość, dojrzałość, zapotrzebowanie, specjalizacje regionu, ochrona, finansowanie)
   i karta innowacji: status wdrożenia, TRL, wiarygodność, każde pole oznaczone jako fakt, deklaracja albo szacunek AI.
4. **Kieruje:** komórka PCI, ścieżka dalej z miernikiem skuteczności, instytucje do współpracy. Analityk decyduje jednym kliknięciem,
   a powód trafia do dziennika.

Firmy i uczelnie mają „Szukam rozwiązania” i „Oceń projekt” (z bazy albo z linku).

## Przyjęte podejście

**Design thinking.** Zaczęliśmy od mentorów PCI: odkrywać innowacje, które już istnieją, zamiast czekać na zgłoszenia; cztery powody
odrzucenia; procent i dowód przy każdej liczbie. Pytanie projektowe: jak sprawić, żeby analityk dowiadywał się o innowacji pierwszy
i od razu miał dowody do decyzji? Prototyp działa na publicznym serwerze; testujemy go na zestawie kontrolnym i na żywo.

**Kod tam, gdzie się da.** Wyszukiwanie, plagiat, podobieństwo, reguły ścieżek i wzór potencjału liczy kod. AI (DeepSeek przez
OpenRouter) ocenia tylko, czy wpis opisuje innowację, nowość według rubryki i czy podobny projekt to ten sam pomysł. Kod odrzuca
każdy dowód spoza wyników wyszukiwania.

**Dane, założenia, ograniczenia.** Tylko publiczne źródła, robots.txt, bez nazwisk. Zgłoszenia patentowe są jawne po 18 miesiącach.
Etykiety testu pochodzą z głosowania 5 modeli, nie od człowieka. Podobieństwo po słowach bywa mylące, dlatego każdą flagę i każdą
rekomendację zatwierdza analityk.

## Dotychczasowy postęp

Działa teraz: https://radar-innowacji.skroban.tech
- Radar przeczytał 1 519 wpisów i wybrał 13 innowacji do oceny. Dwa fałszywe wykrycia (zajęcia i wydarzenie) odrzucił człowiek,
  a bramkę AI uszczelniliśmy.
- Baza: 338 373 dokumentów (Mapa Dotacji UE z całej Polski, RAD-on, patenty uczelni, Biuletyn UPRP, Interreg), odświeżana według harmonogramu.
- Test: 52 przypadki ze znaną prawdą wykryte w całości. Zestaw kontrolny 50 nowych projektów: AUC 0,89, 29 z 30 rutyn zatrzymanych,
  2 z 20 nowości odrzucone.
- Jedno sprawdzenie trwa ok. 17 s i kosztuje ok. 0,001 $. REST API z dokumentacją, testy automatyczne, licencja EUPL-1.2.

Dalej: logowanie analityków, kalibracja wag na decyzjach z dziennika, powiadomienia dla komórek PCI.

## Materiały dodatkowe (linki)

- Demo: https://radar-innowacji.skroban.tech
- Film (ok. 2 min): https://github.com/Kaarmel/radar-innowacji/blob/main/docs/prezentacja/radar-innowacji-film.mp4
- Prezentacja PDF: https://github.com/Kaarmel/radar-innowacji/blob/main/docs/prezentacja/radar-innowacji.pdf
- Przypadek 1, automatyczne wykrycie: https://radar-innowacji.skroban.tech/karta/7
- Przypadek 2, ocena projektu z bazy: https://radar-innowacji.skroban.tech/karta/18
- Miary i test: https://radar-innowacji.skroban.tech/miary
- Warunki działania (aktualność danych, harmonogram, AI, wymagania): https://radar-innowacji.skroban.tech/warunki
- API: https://radar-innowacji.skroban.tech/docs
