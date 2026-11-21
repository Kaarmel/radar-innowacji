"""Cztery filtry odrzucenia. Plagiat, kopia i patent liczy kod; AI tylko potwierdza (kopia, patent) albo ocenia
nowość według rubryki. Dopasowanie do pracy własnej instytucji nie podnosi pasma (wyjątek: duplikat zgłoszenia)."""
from . import ai, config, instytucje, tekst
from .model import Dokument, WynikFiltra, Zgloszenie

UWAGA_PATENT = "Zgłoszenia patentowe są publikowane po 18 miesiącach; młodszych nie widać."


def _wlasny(z: Zgloszenie, d: Dokument) -> bool:
    return instytucje.ta_sama(z.instytucja, d.instytucje)


def _tekst_dok(d: Dokument) -> str:
    return f"{d.tytul}. {d.opis}"


def _dowod(d: Dokument, **extra) -> dict:
    return {"dokument_id": d.id, "tytul": d.tytul, "link": d.link, "zrodlo": d.zrodlo, "rok": d.rok,
            "instytucje": d.instytucje[:3], "status": d.status, "wlasna": False, **extra}


def plagiat(z: Zgloszenie, kandydaci: list[Dokument]) -> WynikFiltra:
    p = config.PROGI["plagiat"]
    wyniki = []
    for d in kandydaci:
        udzial, fragmenty = tekst.pokrycie_ngramow(z.opis, _tekst_dok(d))
        if udzial > 0:
            wyniki.append((udzial * 100, d, fragmenty))
    wyniki.sort(key=lambda x: -x[0])
    dowody, najlepszy, wlasna, uwaga = [], 0.0, False, ""
    for proc, d, fr in wyniki[:5]:
        wl = _wlasny(z, d)
        dowody.append(_dowod(d, procent=round(proc, 1), fragmenty=fr[:5], wlasna=wl))
        if wl and d.zrodlo == "zgloszenie" and proc >= config.PROGI["duplikat_plagiat"]:
            return WynikFiltra("plagiat", round(proc, 1), "czerwone", dowody, uwaga="duplikat zgłoszenia")
        if wl:
            wlasna = True
        else:
            najlepszy = max(najlepszy, proc)
    if wlasna:
        uwaga = "Część tekstu pochodzi z wcześniejszych prac tej samej instytucji (kontynuacja własnej pracy)."
    pasmo = "czerwone" if najlepszy >= p["czerwone"] else "zolte" if najlepszy >= p["zolte"] else "zielone"
    return WynikFiltra("plagiat", round(najlepszy, 1), pasmo, dowody, uwaga=uwaga, wlasna_praca=wlasna)


def _podobne(z: Zgloszenie, kandydaci: list[Dokument], df, N) -> list[tuple[float, Dokument]]:
    out = []
    for d in kandydaci:
        zrodlowy = (z.opis_en or z.opis) if d.jezyk == "en" else z.opis
        out.append((tekst.podobienstwo(zrodlowy, _tekst_dok(d), df, N), d))
    return sorted(out, key=lambda x: -x[0])


def _porownanie(nazwa: str, z: Zgloszenie, kandydaci: list[Dokument], df, N, koszt: list | None, uwaga_stala: str = "") -> WynikFiltra:
    p = config.PROGI[nazwa]
    ranking = _podobne(z, kandydaci, df, N)
    obce = [(s, d) for s, d in ranking if not _wlasny(z, d)]
    wlasne = [(s, d) for s, d in ranking if _wlasny(z, d) and s >= p["zolte"]]
    do_ai = [d for s, d in obce[:3] if s >= p["zolte"]]
    oceny, k = ai.ten_sam_pomysl(z.opis, do_ai) if do_ai else ({}, 0.0)
    if koszt is not None and k:
        koszt.append(k)
    najlepszy = obce[0][0] if obce else 0.0
    potwierdzone = any(oceny.get(d.id, {}).get("ocena") == "ten_sam" for s, d in obce[:3] if s >= p["czerwone"])
    pasmo = "czerwone" if potwierdzone else "zolte" if najlepszy >= p["zolte"] else "zielone"
    uwagi = [uwaga_stala] if uwaga_stala else []
    if najlepszy >= p["czerwone"] and not oceny:
        uwagi.append("Wysokie podobieństwo bez potwierdzenia AI.")
    if wlasne:
        uwagi.append("Podobne dokumenty tej samej instytucji: kontynuacja własnej pracy (nie powód odrzucenia).")
    dowody = [_dowod(d, podobienstwo=round(s * 100, 1), ocena_ai=oceny.get(d.id, {}).get("ocena"),
                     uzasadnienie=oceny.get(d.id, {}).get("uzasadnienie", "")) for s, d in obce[:3] if s > 0]
    dowody += [_dowod(d, podobienstwo=round(s * 100, 1), wlasna=True) for s, d in wlasne[:2]]
    return WynikFiltra(nazwa, round(najlepszy * 100, 1), pasmo, dowody, uwaga=" ".join(uwagi), wlasna_praca=bool(wlasne))


def kopia(z: Zgloszenie, kandydaci: list[Dokument], df, N, koszt: list | None = None) -> WynikFiltra:
    return _porownanie("kopia", z, [d for d in kandydaci if d.typ in {"projekt", "wpis", "zgloszenie"}], df, N, koszt)


def patent(z: Zgloszenie, kandydaci: list[Dokument], df, N, dostepne: bool = True, koszt: list | None = None) -> WynikFiltra:
    patenty = [d for d in kandydaci if d.typ == "patent"]
    if not dostepne and not patenty:
        return WynikFiltra("patent", None, "brak_danych", [], uwaga=f"Źródła patentowe niedostępne. {UWAGA_PATENT}")
    return _porownanie("patent", z, patenty, df, N, koszt, uwaga_stala=UWAGA_PATENT)


def nowosc(z: Zgloszenie, kandydaci: list[Dokument], koszt: list | None = None) -> WynikFiltra:
    p = config.PROGI["nowosc"]
    odpowiedzi, k = ai.rubryka_nowosci(z.opis, kandydaci)
    if koszt is not None:
        koszt.append(k)
    linki = {d.id: d for d in kandydaci}
    dowody = [{**o, "link": linki[o["dokument_id"]].link if o.get("dokument_id") in linki else None,
               "tytul": linki[o["dokument_id"]].tytul if o.get("dokument_id") in linki else None} for o in odpowiedzi]
    if not odpowiedzi or all(o["odpowiedz"] == "nie_wiadomo" for o in odpowiedzi):
        return WynikFiltra("nowosc", None, "brak_danych", dowody, uwaga="AI nie oceniło nowości.")
    tak = sum(o["odpowiedz"] == "tak" for o in odpowiedzi)
    pasmo = "czerwone" if tak <= p["czerwone_max_tak"] else "zolte" if tak <= p["zolte_max_tak"] else "zielone"
    return WynikFiltra("nowosc", 100.0 * tak / 5, pasmo, dowody,
                       uwaga=f"Porównano z {len(kandydaci)} najbliższymi dokumentami.")
