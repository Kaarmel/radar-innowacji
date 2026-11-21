"""Słowniki pól formularza i etykiety widoków (jedno miejsce dla formularza, API i szablonów)."""

TYPY_INSTYTUCJI = {
    "szkola_podstawowa": "Szkoła podstawowa",
    "szkola_ponadpodstawowa": "Szkoła ponadpodstawowa",
    "uczelnia": "Uczelnia",
    "instytut": "Instytut badawczy",
    "jst": "Samorząd (gmina, powiat, województwo)",
    "inna_publiczna": "Inna instytucja publiczna",
    "firma": "Firma",
    "ngo": "Organizacja pozarządowa",
    "osoba": "Osoba prywatna lub grupa nieformalna",
}
TYPY_INNOWACJI = {
    "techniczna": "Techniczna (produkt, urządzenie, oprogramowanie)",
    "organizacyjna": "Organizacyjna (nowy sposób działania instytucji)",
    "edukacyjna": "Edukacyjna (metoda, program, narzędzie dydaktyczne)",
    "spoleczna": "Społeczna (usługa dla mieszkańców, włączenie)",
    "procesowa": "Procesowa (usprawnienie procesu, cyfryzacja)",
}
ETAPY = {"pomysl": "Pomysł", "prototyp": "Prototyp lub pilotaż", "wdrozone": "Wdrożone", "zakonczone": "Zakończone"}
WIEK = {"ponizej_16": "Poniżej 16 lat", "16_30": "16–30 lat", "powyzej_30": "Powyżej 30 lat", "mieszany": "Zespół mieszany"}
WEJSCIA = {"formularz": "Formularz", "baza": "Projekt z bazy (ocena analityka)", "radar": "Radar (wykryte automatycznie)"}

WERDYKTY = {
    "odrzucone_do_przegladu": "Odrzucone automatycznie, do przeglądu",
    "do_przegladu": "Do przeglądu",
    "dalej": "Bez flag, dalej",
}
PASMA = {"zielone": "bez flagi", "zolte": "do sprawdzenia", "czerwone": "powód odrzucenia", "brak_danych": "brak danych"}
FILTRY = {
    "plagiat": ("Plagiat", "Jaka część tekstu zgłoszenia występuje dosłownie (ciągi 8 słów) w innym dokumencie."),
    "kopia": ("Kopia pomysłu", "Podobieństwo treści (TF-IDF); czerwone tylko gdy AI potwierdzi, że to ten sam pomysł."),
    "patent": ("Patent", "Podobieństwo do patentów EP i patentów polskich uczelni; czerwone tylko po potwierdzeniu AI."),
    "nowosc": ("Nowość", "Rubryka 5 pytań oceniana przez AI; każda odpowiedź wskazuje dokument-dowód."),
}
DECYZJE = {"potwierdz_odrzucenie": "Potwierdzam odrzucenie", "przywroc": "Przywracam (flaga nietrafna)",
           "przekaz": "Przekazuję dalej (do komórki lub eksperta)"}
STATUSY = {"nowe": "w kolejce", "w_toku": "sprawdzanie", "gotowe": "gotowe", "blad": "błąd sprawdzenia"}
# Harmonogram aktualizacji (realizują go timery systemd z wdrozenie/vm.sh) i świadome opóźnienia samych źródeł.
HARMONOGRAM = {
    "mapadotacji": {"tryb": "pobierane (API)", "co_ile": "co tydzień, poniedziałek 03:00",
                    "uwaga": "Projekty pojawiają się po podpisaniu umowy o dofinansowanie."},
    "interreg": {"tryb": "pobierane (plik XLSX)", "co_ile": "co miesiąc, 1. dnia 03:30",
                 "uwaga": "Lista projektów publikowana przez wspólny sekretariat programu."},
    "radon": {"tryb": "pobierane (API)", "co_ile": "co tydzień, wtorek 03:00",
              "uwaga": "Projekty naukowe wpisywane przez uczelnie i instytuty do RAD-on."},
    "radon_patenty": {"tryb": "pobierane (API)", "co_ile": "co tydzień, środa 03:00",
                      "uwaga": "Patenty i wzory udzielone polskim uczelniom. Zgłoszenia są jawne dopiero po 18 miesiącach."},
    "epo": {"tryb": "na żywo", "co_ile": "przy każdym sprawdzeniu (EPO publikuje nowe dokumenty co tydzień, w środy)",
            "uwaga": "Zgłoszenia patentowe są jawne dopiero po 18 miesiącach od daty pierwszeństwa: najnowszych nie widzi żadna baza."},
    "openalex": {"tryb": "na żywo", "co_ile": "przy każdym sprawdzeniu", "uwaga": "Publikacje z abstraktami; darmowy klucz."},
    "crossref": {"tryb": "na żywo", "co_ile": "przy każdym sprawdzeniu", "uwaga": "Metadane publikacji (DOI)."},
    "www": {"tryb": "kanały RSS", "co_ile": "codziennie 06:00, wpisy z ostatnich 180 dni",
            "uwaga": "172 strony szkół, uczelni, PCI i samorządów (konfiguracja/zrodla_www.csv)."},
}
ZRODLA = {
    "mapadotacji": ("Mapa Dotacji UE: projekty z Podkarpacia", "https://mapadotacji.gov.pl"),
    "interreg": ("Interreg Polska–Słowacja", "https://pl-sk.eu"),
    "radon": ("RAD-on: projekty naukowe", "https://radon.nauka.gov.pl"),
    "radon_patenty": ("RAD-on: patenty i wzory polskich uczelni", "https://radon.nauka.gov.pl"),
    "epo": ("EPO: patenty europejskie (na żądanie)", "https://data.epo.org/linked-data/"),
    "openalex": ("OpenAlex: publikacje naukowe (na żądanie)", "https://openalex.org"),
    "crossref": ("Crossref: publikacje (na żądanie)", "https://www.crossref.org"),
    "www": ("Radar WWW: strony szkół, uczelni i instytucji", ""),
    "zgloszenie": ("Wcześniejsze zgłoszenia", ""),
}
