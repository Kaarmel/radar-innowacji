# Raport walidacji

Uruchomienie: 2026-11-21 23:59, przypadków: 102.

| Miara | Wartość |
|---|---|
| Plagiat: czułość | 9/9 (1.00) |
| Kopia: czułość | 10/10 (1.00) |
| Patent: czułość | 5/5 (1.00) |
| Własna praca: czułość | 5/5 (1.00) |
| Duplikat: czułość | 3/3 (1.00) |
| Nowość: zgodność z etykietą (głosowanie modeli) | 0.95 (n=19) |
| Średni potencjał: nowość / rutyna (głosowanie modeli) | 59.8 / 10.5 |
| Zestaw kontrolny, niezależny pomiar: zgodność nowości (głosowanie modeli) | 0.62 (n=48) |
| Zestaw kontrolny: średni potencjał nowość / rutyna (głosowanie modeli) | 66.8 / 22.0 |
| Zestaw kontrolny: potencjał nowości wyżej niż rutyny (AUC, bez progu) | 0.89 |
| Zestaw kontrolny: nowości odrzucone przez lejek | 2/20 |
| Zestaw kontrolny: rutyny zatrzymane (odrzucone lub do przeglądu) | 29/30 |
| Mediana czasu sprawdzenia | 39.5 s |
| Średni koszt AI na sprawdzenie | 0.00138 $ |

Przypadki ze znaną prawdą zbudowane z dzisiejszych danych (RAD-on, Mapa Dotacji): Plagiat: połowa zdań z projektu A + połowa z projektu B (inne instytucje); oczekiwane: plagiat czerwone; Kopia: projekt przepisany innymi słowami przez AI; oczekiwane: kopia żółta lub czerwona; Patent: opis patentu polskiej uczelni przepisany innymi słowami; oczekiwane: patent żółty lub czerwony; Własna praca: tekst projektu zgłoszony przez tę samą instytucję; oczekiwane: bez czerwonego plagiatu, oznaczone jako kontynuacja; Duplikat: to samo zgłoszenie wysłane drugi raz; oczekiwane: plagiat czerwony z uwagą „duplikat zgłoszenia”. Etykiety „rutyna / nowość” w walidacja/etykiety.csv to głosowanie 5 modeli: GPT-5.4-mini, Gemini 3.8 Flash, Claude Haiku 5.5, Mistral Small (OpenRouter) i Antigravity; większość głosów. Rubrykę nowości poprawiliśmy po pierwszym pomiarze na tych samych 20 projektach, więc zgodność nie jest niezależnym pomiarem, nie ocena człowieka; głosy każdego modelu: walidacja/etykiety_glosy.csv. Zestaw kontrolny (walidacja/kontrolne.csv): projekty wylosowane po zamrożeniu rubryki, etykiety: głosowanie 5 modeli: GPT-5.4-mini, Gemini 3.8 Flash, Claude Haiku 5.5, Mistral Small (OpenRouter) i Antigravity; większość głosów. Zestaw kontrolny: projekty wylosowane po zamrożeniu rubryki, rubryki po tym pomiarze nie zmieniano.
