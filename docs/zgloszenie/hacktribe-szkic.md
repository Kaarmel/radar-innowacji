# Szkic zgłoszenia (HackTribe)

**Tytuł:** Radar Innowacji: sam wyszukuje istniejące innowacje i ocenia je z dowodami

**Problem.** Wartościowe pomysły ze szkół, uczelni i samorządów zostają w miejscu powstania. Instytucje takie jak
Podkarpackie Centrum Innowacji szukają ich dziś ręcznie (bazy, strony, telefony do naukowców) i ręcznie sprawdzają,
czy pomysł nie jest kopią, plagiatem albo czy nie jest już opatentowany. Brakuje powtarzalnego procesu oceny z jasnymi kryteriami.

**Rozwiązanie.** Radar dla instytucji takich jak PCI (pierwszy profil), który:
1. sam wyszukuje innowacje: co godzinę (i na żądanie) czyta kanały RSS 172 stron szkół, uczelni, PCI i samorządów (AI przepuszcza tylko
   wpisy z konkretnym rozwiązaniem, wg Oslo Manual 2018; bez nazwisk), a co tydzień odświeża bazy projektów i patentów.
   Analityk może też ocenić projekt z wyszukiwarki („Oceń ten projekt”) albo z linku. To nie jest platforma do zgłaszania pomysłów;
2. przeszukuje ok. 88 tys. dokumentów: Mapa Dotacji UE (Podkarpacie), Interreg PL–SK, RAD-on (projekty i patenty
   polskich uczelni), a na żądanie patenty EPO, OpenAlex i Crossref. Wyszukiwarkę filtruje się po źródle i roku, katalog
   po werdykcie, wejściu i obszarze, a 2–4 projekty można porównać obok siebie;
3. przepuszcza zgłoszenie przez cztery filtry odrzucenia (plagiat, kopia pomysłu, patent, nowość). Każdy filtr ma procent,
   pasmo i link do dokumentu-dowodu, a przy plagiacie fragmenty obok siebie;
4. liczy **ocenę potencjału 0–100 według jawnego wzoru** (nowość, dojrzałość, mierzalna przewaga, zapotrzebowanie i transfer,
   możliwość ochrony, precedens finansowania, zgodność ze specjalizacjami). Wagi ustawia organizacja w swoim profilu;
5. wskazuje komórkę organizacji (dla PCI: młodzi 16–30, naukowcy, inni, ogólne), ścieżkę dalej (akceleracja, ochrona,
   transfer, finansowanie, współpraca) i instytucje, które działają w temacie;
6. tworzy kartę innowacji wg FAQ: obszar, status wdrożenia (5 poziomów), TRL 1–9, potencjał i wiarygodność, z oznaczeniem
   „fakt z danych / deklaracja / szacunek AI / reguła w kodzie”;
7. kieruje pozycje z flagą do kolejki analityka. Decyzję (potwierdź, przywróć, przekaż) podejmuje człowiek, z powodem w dzienniku.

**Nie „AI wrapper”.** Wyszukiwanie, plagiat, podobieństwo, reguły ścieżek i wzór potencjału liczy kod. AI (DeepSeek przez
OpenRouter) tłumaczy zapytanie, potwierdza kopie i odpowiada na 5 pytań rubryki nowości. Kod sprawdza, że każdy dokument,
na który powołuje się AI, był w wynikach. Jedno sprawdzenie trwa ok. 15–60 s (limit 150 s) i kosztuje ok. 0,001 $.

**Miary.** 52 przypadki ze znaną prawdą zbudowane z danych: plagiat 9/9, kopia 10/10, patent 5/5, własna praca 5/5,
duplikat 3/3. Na 50 nowych projektach wylosowanych po zamrożeniu rubryki (etykiety z głosowania 5 modeli, nie człowieka)
potencjał nowości jest wyższy niż rutyny w 89% par (AUC 0,89), lejek odrzucił 2 z 20 nowości i zatrzymał 29 z 30 rutyn,
a sam kolor nowości zgadza się z etykietą w 0,62 (n=48). Na 20 projektach, na których poprawialiśmy rubrykę, zgodność
wynosi 0,95, ale to nie jest niezależny pomiar.

**Dla kogo.** Zakładki z prostym opisem i demo dla analityka PCI, szkół i młodych (16–30), uczelni, gmin i firm.

**Warunki działania.** Strona /warunki: stan danych każdego źródła, harmonogram aktualizacji (timery systemd: bazy co tydzień,
radar co godzinę i na żądanie, EPO na żywo), trzy ścieżki AI (API, model lokalny, bez AI) i wymagania sprzętowe.

**Integracja i skalowanie.** REST API z dokumentacją OpenAPI (/docs), nowa organizacja = jeden plik JSON z komórkami,
ścieżkami i wagami, licencja EUPL-1.2.

**Demo:** https://radar-innowacji.skroban.tech/
**Repozytorium:** https://github.com/Kaarmel/radar-innowacji
