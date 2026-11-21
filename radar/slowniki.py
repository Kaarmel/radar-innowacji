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
from .klasyfikacja import OSLO, POCHODZENIE  # noqa: E402,F401  (dla szablonów: s.OSLO, s.POCHODZENIE)

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
def czas_pl(ts: float, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Czas w strefie Europe/Warsaw niezależnie od strefy serwera (serwer demo działa w UTC)."""
    import datetime
    from zoneinfo import ZoneInfo
    return datetime.datetime.fromtimestamp(ts, ZoneInfo("Europe/Warsaw")).strftime(fmt)


def stan_na(klucz: str, stan: dict) -> float:
    """Kopia lokalna: najstarszy rekord (dociąganie pojedynczych rekordów nie odmładza całego źródła); na żywo: ostatnie zapytanie."""
    return stan["pobrano_do"] if HARMONOGRAM.get(klucz, {}).get("tryb") == "na żywo" else stan["pobrano_od"]


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


# Zakładki „Dla kogo”: ta sama aplikacja opisana językiem konkretnej osoby, z przyciskami do działającego demo.
ROLE = {
    "analityk": {
        "nazwa": "Analityk PCI",
        "kto": "Opiekun innowacji w Podkarpackim Centrum Innowacji",
        "korzysc": "Radar sam znajduje projekty w regionie, a Ty dostajesz gotowe karty z dowodami do decyzji.",
        "kroki": ["Codziennie radar czyta strony szkół, uczelni i gmin, a co tydzień odświeża bazy dotacji, projektów badawczych i patentów.",
                  "Każdy znaleziony projekt dostaje kartę: czy jest nowy, czy to kopia albo plagiat, czy blokuje go patent i jaki ma potencjał.",
                  "Przeglądasz tylko pozycje z flagą i jednym kliknięciem potwierdzasz albo zmieniasz decyzję."],
        "zobaczysz": ["Procent i kolor przy każdym filtrze, z linkiem do dokumentu, który jest dowodem.",
                      "Komórkę PCI (młodzi 16–30, naukowcy, inni) i proponowaną ścieżkę wsparcia.",
                      "Kto w regionie robi już coś podobnego: potencjalni partnerzy i ich projekty."],
        "demo": [("Wykryte projekty w kolejce PCI", "/o/pci/kolejka"), ("Przykładowa karta: RescuePet", "/karta/7"),
                 ("Skąd są dane i jak są świeże", "/warunki")],
    },
    "mlodzi": {
        "nazwa": "Szkoła i młodzi twórcy (16–30)",
        "kto": "Uczniowie, studenci, nauczyciele i koła naukowe",
        "korzysc": "Twój projekt może zostać zauważony, nawet jeśli nikt go nigdzie nie zgłaszał.",
        "kroki": ["Opisujesz projekt w aktualnościach szkoły albo uczelni, tak jak zwykle.",
                  "Radar to zauważa, sprawdza, czy podobne rozwiązanie już istnieje, i przygotowuje kartę dla PCI.",
                  "Opiekun z PCI może się odezwać z mentoringiem, konkursem albo pomocą w ochronie pomysłu."],
        "zobaczysz": ["Czy podobny pomysł już istnieje (z linkami) i co wyróżnia Twój.",
                      "Na jakim etapie jest projekt i jaki może być następny krok: mentoring, prototyp, konkurs.",
                      "Bez nazwisk: radar zapisuje szkołę i krótkie streszczenie, nie dane uczniów."],
        "demo": [("Przykład: aplikacja RescuePet", "/karta/7"), ("Przykład: osłona termiczna z mini-hackathonu", "/karta/5"),
                 ("Wszystkie projekty młodych", "/kolejka?komorka=mlodzi_16_30")],
    },
    "naukowcy": {
        "nazwa": "Uczelnia i naukowcy",
        "kto": "Zespoły badawcze i centra transferu technologii",
        "korzysc": "Sprawdzisz, czy wynik badań jest nowy na tle patentów i publikacji, zanim zaczniesz go chronić albo sprzedawać.",
        "kroki": ["Wpisujesz temat albo wklejasz opis wyniku badań.",
                  "System przeszukuje patenty (EPO i polskie przez RAD-on), publikacje oraz projekty z dotacją.",
                  "Od razu widzisz najbliższe dokumenty; „Oceń ten projekt” dodaje ocenę nowości z uzasadnieniem do każdego pytania."],
        "zobaczysz": ["Patenty i zgłoszenia patentowe zbliżone do pomysłu, z linkami.",
                      "Własne wcześniejsze prace oznaczone jako kontynuacja, a nie kopia.",
                      "Podpowiedź: ochrona patentowa, licencja albo partner przemysłowy."],
        "demo": [("Szukaj: magazyn energii", "/szukaj?q=magazyn+energii"),
                 ("Szukaj: sztuczna inteligencja w diagnostyce", "/szukaj?q=sztuczna+inteligencja+diagnostyka"),
                 ("Jak dokładny jest system", "/miary")],
    },
    "gmina": {
        "nazwa": "Gmina i urząd",
        "kto": "Wójtowie, burmistrzowie, wydziały rozwoju i inwestycji",
        "korzysc": "Zobaczysz, które gminy wdrożyły już podobne rozwiązanie z dotacją i kogo zapytać o doświadczenia.",
        "kroki": ["Wpisujesz problem, na przykład „oświetlenie uliczne” albo „telemedycyna”.",
                  "Wyszukiwarka pokazuje projekty z Mapy Dotacji UE, Interreg i RAD-on z linkiem do źródła.",
                  "Ciekawe rozwiązanie z własnej gminy przekazujesz do oceny w PCI."],
        "zobaczysz": ["Projekty, które już dostały dotację: dowód, że pomysł da się sfinansować.",
                      "Link do opisu w oficjalnym serwisie; beneficjenta karta pobiera po kliknięciu „Oceń ten projekt”.",
                      "Innowacje samorządów z regionu, wykryte na stronach urzędów."],
        "demo": [("Szukaj: oświetlenie uliczne", "/szukaj?q=o%C5%9Bwietlenie+uliczne"), ("Szukaj: telemedycyna", "/szukaj?q=telemedycyna"),
                 ("Katalog ocenionych projektów", "/kolejka")],
    },
    "firma": {
        "nazwa": "Firma szukająca rozwiązania",
        "kto": "Małe i średnie firmy oraz przemysł z regionu",
        "korzysc": "Znajdziesz, kto w regionie pracuje już nad Twoim problemem: zespół z uczelni, szkoła albo inna firma.",
        "kroki": ["Opisujesz problem swoimi słowami.",
                  "Wyszukiwarka od razu przegląda projekty z dotacją, projekty badawcze, patenty i ocenione innowacje.",
                  "Kontaktujesz się z instytucją z karty albo prosisz PCI o pośrednictwo."],
        "zobaczysz": ["Listę najbliższych projektów i patentów z odnośnikami do źródła.",
                      "Uczelnie i firmy z projektów badawczych RAD-on, które pracowały nad tematem.",
                      "Dane gotowe do podpięcia pod systemy firmy przez API."],
        "demo": [("Szukaj: recykling tworzyw", "/szukaj?q=recykling+tworzyw"), ("Szukaj: drony w rolnictwie", "/szukaj?q=drony+w+rolnictwie"),
                 ("API dla systemów firmy", "/docs")],
    },
}
