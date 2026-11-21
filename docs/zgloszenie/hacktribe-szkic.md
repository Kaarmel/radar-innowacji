# Szkic zgłoszenia (HackTribe)

**Tytuł:** Radar Innowacji: wyszukiwanie i ocena innowacji z dowodami

**Problem.** Wartościowe pomysły ze szkół, uczelni i samorządów zostają w miejscu powstania. Instytucje takie jak
Podkarpackie Centrum Innowacji szukają ich dziś ręcznie (bazy, strony, telefony do naukowców) i ręcznie sprawdzają,
czy pomysł nie jest kopią, plagiatem albo czy nie jest już opatentowany. Brakuje powtarzalnego procesu oceny z jasnymi kryteriami.

**Rozwiązanie.** System dla firm i instytucji (PCI jest jednym z profili), który:
1. przyjmuje zgłoszenie formularzem, z linku albo z bazy projektów (analityk klika „Oceń ten projekt”);
2. przeszukuje ok. 88 tys. dokumentów: Mapa Dotacji UE (Podkarpacie), Interreg PL–SK, RAD-on (projekty i patenty
   polskich uczelni), a na żądanie patenty EPO, OpenAlex i Crossref;
3. przepuszcza zgłoszenie przez cztery filtry odrzucenia (plagiat, kopia pomysłu, patent, nowość). Każdy filtr ma procent,
   pasmo i link do dokumentu-dowodu, a przy plagiacie fragmenty obok siebie;
4. liczy **ocenę potencjału 0–100 według jawnego wzoru** (nowość, dojrzałość, mierzalna przewaga, zapotrzebowanie i transfer,
   możliwość ochrony, precedens finansowania, zgodność ze specjalizacjami). Wagi ustawia organizacja w swoim profilu;
5. wskazuje komórkę organizacji (dla PCI: młodzi 16–30, naukowcy, inni, ogólne), ścieżkę dalej (akceleracja, ochrona,
   transfer, finansowanie, współpraca) i instytucje, które działają w temacie;
6. kieruje pozycje z flagą do kolejki analityka. Decyzję (potwierdź, przywróć, przekaż) podejmuje człowiek, z powodem w dzienniku.

**Nie „AI wrapper”.** Wyszukiwanie, plagiat, podobieństwo, reguły ścieżek i wzór potencjału liczy kod. AI (DeepSeek przez
OpenRouter) tłumaczy zapytanie, potwierdza kopie i odpowiada na 5 pytań rubryki nowości. Kod sprawdza, że każdy dokument,
na który powołuje się AI, był w wynikach. Jedno sprawdzenie trwa ok. 15–60 s i kosztuje ok. 0,001 $.

**Integracja i skalowanie.** REST API z dokumentacją OpenAPI (/docs), nowa organizacja = jeden plik JSON z komórkami,
ścieżkami i wagami, licencja EUPL-1.2.

**Demo:** https://radar-innowacji.skroban.tech/
**Repozytorium:** https://github.com/Kaarmel/radar-innowacji
