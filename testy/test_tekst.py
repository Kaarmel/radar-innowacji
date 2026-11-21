import math

from radar import tekst

A = ("Uczniowie technikum zbudowali filtr wody inspirowany skrzelami ryb. Urządzenie zatrzymuje drobiny mikroplastiku "
     "bez użycia wymiennych wkładów. Prototyp przetestowano w szkolnym laboratorium na próbkach z pobliskiej rzeki.")
B = ("Gmina wyremontowała płytę rynku i posadziła nowe drzewa. Mieszkańcy zyskali ławki, fontannę oraz oświetlenie "
     "energooszczędne. Prace prowadzono etapami przez cały rok budżetowy w porozumieniu z konserwatorem zabytków.")


def test_tokeny():
    assert tekst.tokeny("Źródło: Filtr-3D!") == ["zrodlo", "filtr", "3d"]


def test_pokrycie_identyczne():
    assert tekst.pokrycie_ngramow(A, A)[0] == 1.0


def test_pokrycie_polowa_i_fragment_w_oryginale():
    zdania_a = A.split(". ")
    zdania_b = B.split(". ")
    zgl = ". ".join([zdania_a[0], zdania_a[1], zdania_b[0], zdania_b[1]])  # skopiowany ciągły blok
    p, fragmenty = tekst.pokrycie_ngramow(zgl, A)
    assert 0.3 <= p <= 0.65
    assert any("zbudowali filtr wody inspirowany skrzelami ryb" in f for f in fragmenty)


def test_pokrycie_krotki_tekst():
    assert tekst.pokrycie_ngramow("za krótko", A) == (0.0, [])


def test_podobienstwo():
    df, n = (lambda t: 1), 10
    assert math.isclose(tekst.podobienstwo(A, A, df, n), 1.0, rel_tol=1e-9)
    assert tekst.podobienstwo("kot pies", "rynek fontanna", df, n) == 0.0


def test_terminy_bez_stop():
    t = tekst.terminy("Projekt w szkole i na rynku oraz dla gminy filtr wody filtr", n=5)
    assert "filtr" in t
    assert not ({"w", "i", "na", "oraz", "dla"} & set(t))


def test_bez_html():
    assert tekst.bez_html("<p>Ala &amp; <b>kot</b></p>\n<br/>x") == "Ala & kot x"
