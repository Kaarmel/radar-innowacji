# Pitch finałowy (5 minut) i pytania jury

Na finale prezentacja nie jest nagrywana. Mówimy do jury, a demo pokazujemy na żywo na https://radar-innowacji.skroban.tech.
Zakładki otwarte wcześniej: strona główna, karta 7, karta 18, kolejka PCI, /miary.
Plan B na wypadek braku sieci: PDF (`docs/prezentacja/radar-innowacji.pdf`) i film.

## Scenariusz (5:00)

**0:00–0:30 · Haczyk.** Slajd 1.
„Miesiąc temu technikum w Trzcianie opisało w aktualnościach koncepcję aplikacji RescuePet do zgłaszania rannych zwierząt.
Nikt jej nigdzie nie zgłaszał. Wczoraj radar sam ją znalazł, a pół minuty później była w kolejce PCI, z oceną 74 na 100 i linkiem do każdego dowodu.
To jest Radar Innowacji.”

**0:30–1:10 · Problem (empatia).** Slajdy 2–3.
Analityk PCI dowiaduje się o innowacjach przypadkiem. Szuka ręcznie: bazy, strony szkół, telefony.
Każdy projekt sprawdza sam: czy jest nowy, czy to kopia albo plagiat, czy nie blokuje go patent. Powody decyzji nigdzie nie zostają.
Mentorzy PCI powiedzieli nam wprost: odkrywać to, co już istnieje, i dawać procent z dowodem.

**1:10–2:40 · Demo (pomysł i prototyp).** Slajdy 4–7 albo na żywo.
1. Strona główna: lejek. Z 1 519 wpisów zostało 13 innowacji. Przycisk „Sprawdź źródła teraz”.
2. Karta 7: cytat ze strony szkoły, cztery filtry z procentami, potencjał z jawnego wzoru, ścieżka i miernik skuteczności.
3. „Szukam rozwiązania”: drony → AirNest → „Oceń ten projekt”. Karta 18 gotowa w 17 sekund: potencjał 87, partnerzy, ścieżka.

**2:40–3:30 · Test (uczciwie).** Slajd 8.
Na 50 nowych projektach ranking potencjału trafia w 89% par. Bramka zatrzymała 29 z 30 rutyn i odrzuciła 2 z 20 nowości.
W nocy AI przepuściło zajęcia straży miejskiej z maskotką. Analityk odrzucił je jedną decyzją, a my uszczelniliśmy bramkę.
Etykiety pochodzą z głosowania modeli, więc każde odrzucenie przegląda człowiek.

**3:30–4:30 · Wdrożenie.** Slajd 9.
Działa teraz na jednym serwerze (1 vCPU, 4 GB RAM): 338 473 dokumentów, radar co godzinę, bazy co tydzień.
Jedno sprawdzenie kosztuje ok. 0,001 $. REST API, licencja EUPL. Nowa organizacja to jeden plik z kryteriami i wagami.
Dalej: logowanie analityków i kalibracja wag na decyzjach z dziennika.

**4:30–5:00 · Zamknięcie.** Slajd 10.
„Radar sprawia, że analityk dowiaduje się o innowacji pierwszy i od razu ma dowody. Decyzja zostaje przy człowieku.
Od poniedziałku może pracować dla PCI.”

## Pytania jury: krótkie odpowiedzi

| Pytanie | Odpowiedź |
|---|---|
| To tylko nakładka na AI? | Nie. Wyszukiwanie, plagiat, podobieństwo, reguły i wzór potencjału liczy kod. AI ocenia nowość i czy wpis to innowacja, a kod odrzuca dowody spoza wyników. Bez AI też działa (filtry kodu). |
| Skąd wiecie, że to działa? | 52 przypadki ze znaną prawdą: wszystkie wykryte. Zestaw kontrolny 50 projektów wylosowanych po zamrożeniu rubryki: AUC 0,89, 29 z 30 rutyn zatrzymanych. Słabość: sam kolor nowości zgadza się w 0,62, więc dużo trafia „do sprawdzenia”. |
| Kto podejmuje decyzję? | Zawsze człowiek. System flaguje i podaje dowody; decyzja i powód trafiają do dziennika. |
| RODO i dane osobowe? | Nie zapisujemy nazwisk: z RAD-on i Biuletynu UPRP pomijamy twórców i kierowników, z wpisów szkół instytucję i streszczenie. |
| Patenty w toku? | EPO na żywo (także zgłoszenia), Biuletyn UPRP z 52 numerów. Zgłoszenia są jawne po 18 miesiącach i karta o tym przypomina. |
| Ile kosztuje utrzymanie? | Serwer 1 vCPU i 4 GB RAM; AI ok. 0,001 $ za sprawdzenie albo model lokalny bez kosztów API. |
| Jak dodać inną organizację lub województwo? | Plik JSON z komórkami, ścieżkami i wagami; lista stron w CSV; Mapa Dotacji już obejmuje całą Polskę. |
| Strony bez RSS? | Dziś radar czyta 125 ze 172 stron, które mają kanał RSS lub Atom. Parser stron z aktualnościami to następny krok. |
| Skąd wagi potencjału? | Eksperckie, jawne w profilu organizacji. Dziennik decyzji analityków posłuży do kalibracji. |
| Dlaczego przy RescuePet są projekty o bezdomności? | Dopasowanie po słowie „bezdomnych” (zwierzęta, nie ludzie). Dlatego każdy punkt ma link: analityk widzi to od razu. Ograniczenie opisane w README; następny krok to potwierdzanie partnerów przez AI, tak jak przy kopii. |
| Czym różni się od wyszukiwarki? | Wyszukiwarka czeka na pytanie. Radar sam znajduje nowe wpisy, ocenia je i kładzie analitykowi gotową kartę do decyzji. |
