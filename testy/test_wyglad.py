"""Wygląd: kolory i font PCI (granat, Lato z własnej kopii, SIL OFL), ale własny układ: jasny nagłówek bez bloku CTA, znacznik z logo."""
from .test_app import klient  # noqa: F401


def test_font_lato_serwowany_lokalnie(klient):
    css = klient.get("/static/styl.css").text
    assert "font-family: 'Lato'" in css and "googleapis" not in css and "gstatic" not in css
    for plik in ("lato-400-latin-ext", "lato-700-latin-ext", "lato-900-latin-ext", "lato-400-latin"):
        assert klient.get(f"/static/fonts/{plik}.woff2").status_code == 200, plik
    assert "SIL OPEN FONT LICENSE" in klient.get("/static/fonts/OFL.txt").text.upper()


def test_motyw_pci_i_menu_bez_bloku_cta(klient):
    css = klient.get("/static/styl.css").text
    assert "--pci-granat: #001A49" in css and "--pci-niebieski: #035487" in css and "--logo-zielony: #6BB437" in css
    s = klient.get("/").text
    menu = s[s.index('<nav aria-label="Główne"'):s.index("</nav>")]
    assert 'class="cta"' not in menu and menu.index('href="/o/pci/kolejka"') < menu.index('href="/szukaj"')
