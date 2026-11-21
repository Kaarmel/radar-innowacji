# Raport walidacji

Uruchomienie: 2026-11-21 21:18, przypadków: 49.

| Miara | Wartość |
|---|---|
| Plagiat: czułość | 9/9 (1.00) |
| Kopia: czułość | 10/10 (1.00) |
| Patent: czułość | 5/5 (1.00) |
| Własna praca: czułość | 5/5 (1.00) |
| Duplikat: czułość | 3/3 (1.00) |
| Nowość: zgodność z etykietą (głosowanie modeli) | 0.56 (n=16) |
| Średni potencjał: nowość / rutyna (głosowanie modeli) | 28.1 / 18.3 |
| Mediana czasu sprawdzenia | 43.6 s |
| Średni koszt AI na sprawdzenie | 0.00128 $ |

Przypadki ze znaną prawdą zbudowane z dzisiejszych danych (RAD-on, Mapa Dotacji): Plagiat: połowa zdań z projektu A + połowa z projektu B (inne instytucje); oczekiwane: plagiat czerwone; Kopia: projekt przepisany innymi słowami przez AI; oczekiwane: kopia żółta lub czerwona; Patent: opis patentu polskiej uczelni przepisany innymi słowami; oczekiwane: patent żółty lub czerwony; Własna praca: tekst projektu zgłoszony przez tę samą instytucję; oczekiwane: bez czerwonego plagiatu, oznaczone jako kontynuacja; Duplikat: to samo zgłoszenie wysłane drugi raz; oczekiwane: plagiat czerwony z uwagą „duplikat zgłoszenia”. Etykiety „rutyna / nowość” w walidacja/etykiety.csv to głosowanie 5 modeli: GPT-5.4-mini, Gemini 3.8 Flash, Claude Haiku 5.5, Mistral Small (OpenRouter) i Antigravity; większość głosów, nie ocena człowieka; głosy każdego modelu: walidacja/etykiety_glosy.csv.
