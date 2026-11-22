"""Wygląd w stylu PCI (pcinn.org): granat, font Lato z własnej kopii (SIL OFL, bez zapytań do Google), kwadratowe przyciski."""
from .test_app import klient  # noqa: F401


def test_font_lato_serwowany_lokalnie(klient):
    css = klient.get("/static/styl.css").text
    assert "font-family: 'Lato'" in css and "googleapis" not in css and "gstatic" not in css
    for plik in ("lato-400-latin-ext", "lato-700-latin-ext", "lato-900-latin-ext", "lato-400-latin"):
        assert klient.get(f"/static/fonts/{plik}.woff2").status_code == 200, plik
    assert "SIL OPEN FONT LICENSE" in klient.get("/static/fonts/OFL.txt").text.upper()


def test_motyw_pci_i_przycisk_w_menu(klient):
    css = klient.get("/static/styl.css").text
    assert "--pci-granat: #001A49" in css and "--pci-niebieski: #035487" in css
    s = klient.get("/").text
    assert '<a class="cta" href="/o/pci/kolejka"' in s
