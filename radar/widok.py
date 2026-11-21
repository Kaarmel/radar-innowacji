"""Statyczny widok radaru → widok.html (mapa placówek + ranking wpisów z sygnałami i linkiem do źródła).

Użycie: python3 radar/widok.py [dane/wpisy.jsonl]   (domyślnie dane/wpisy_proba.jsonl)
Bez fragmentów tekstu wpisów (zawierają imiona uczniów i nauczycieli): tylko tytuł, sygnały i link do źródła.
Otwierasz widok.html w przeglądarce; mapa (Leaflet, OpenStreetMap) wymaga internetu, lista działa bez niego.
"""
import html
import json
import os
import sys

from sygnaly import ocena

TU = os.path.dirname(os.path.abspath(__file__))
DANE = os.path.join(TU, "..", "dane")


def dane(plik_wpisow):
    inst = {str(x["rspo"]): x for x in map(json.loads, open(os.path.join(DANE, "instytucje.jsonl"), encoding="utf-8"))}
    wpisy = []
    for x in map(json.loads, open(plik_wpisow, encoding="utf-8")):
        if not x["link"].startswith(("http://", "https://")):
            continue  # link z obcej strony: tylko http(s), żadnych javascript:
        i = inst.get(str(x["zrodlo_id"]), {})
        pkt, syg = ocena(x["tytul"] + " " + x["tekst"][:3000])
        wpisy.append({"t": x["tytul"], "l": x["link"], "d": x["data"], "p": pkt, "s": syg,
                      "n": i.get("nazwa", x["www"]), "pow": i.get("powiat", "?"), "id": str(x["zrodlo_id"])})
    wpisy.sort(key=lambda w: (w["p"], w["d"] or ""), reverse=True)  # najpierw punkty, potem najnowsze
    ze_zrodlem = {w["id"] for w in wpisy}
    punkty = [{"n": x["nazwa"], "la": x["lat"], "lo": x["lon"], "pow": x["powiat"], "w": bool(x["www"]),
               "r": k in ze_zrodlem} for k, x in inst.items() if x.get("lat")]
    return punkty, wpisy


SZABLON = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radar Innowacji</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="anonymous">
<style>
:root{--bg:#fafaf7;--fg:#1d1d1b;--mut:#6b6b66;--line:#e2e1db;--acc:#0b6e4f;--neg:#a33}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--mut:#9a9a93;--line:#2c2c29;--acc:#4fc195;--neg:#e58}}
body{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:16px;border-bottom:1px solid var(--line)}h1{font-size:20px;margin:0 0 4px}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:0;height:calc(100vh - 92px)}
#mapa{height:100%}#lista{overflow:auto;padding:0 16px 16px}
@media (max-width:800px){.wrap{display:block;height:auto}#mapa{height:300px}}
.w{border-bottom:1px solid var(--line);padding:12px 0}.w a{color:var(--fg);font-weight:600;text-decoration:none}.w a:hover{text-decoration:underline}
.meta{color:var(--mut);font-size:13px}.s{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:10px;padding:0 7px;margin:3px 4px 0 0}
.p{float:right;font-weight:700;color:var(--acc)}.p.neg{color:var(--neg)}select,input{font:inherit;padding:4px;margin-right:8px}
</style></head><body>
<header><h1>Radar Innowacji · Podkarpacie</h1><div class="meta">__OPIS__</div>
<div style="margin-top:6px"><select id="pow"><option value="">wszystkie powiaty</option></select>
<label><input type="checkbox" id="tylko" checked> tylko wpisy z sygnałem (≥ 3 pkt)</label></div></header>
<div class="wrap"><div id="mapa"></div><div id="lista"></div></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin="anonymous"></script>
<script>
const P=__PUNKTY__, W=__WPISY__;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const sel=document.getElementById('pow');
[...new Set(P.map(p=>p.pow))].sort().forEach(p=>sel.add(new Option(p,p)));
function lista(){const pw=sel.value,t=document.getElementById('tylko').checked;
 const v=W.filter(w=>(!pw||w.pow===pw)&&(!t||w.p>=3));
 document.getElementById('lista').innerHTML=`<p class="meta">${v.length} wpisów</p>`+v.map(w=>`<div class="w"><span class="p ${w.p<0?'neg':''}">${w.p}</span>
 <a href="${esc(w.l)}" target="_blank" rel="noopener">${esc(w.t)}</a><div class="meta">${esc(w.n)} · pow. ${esc(w.pow)} · ${esc(w.d||'brak daty')}</div>
 <div>${Object.entries(w.s).map(([k,x])=>`<span class="s">${esc(k)}: „${esc(x)}”</span>`).join('')}</div></div>`).join('');}
sel.onchange=lista;document.getElementById('tylko').onchange=lista;lista();
if(window.L){const m=L.map('mapa').setView([49.95,22.1],8);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(m);
 P.forEach(p=>L.circleMarker([p.la,p.lo],{radius:p.r?6:3,weight:0,fillOpacity:.75,fillColor:p.r?'#0b6e4f':(p.w?'#8a8a84':'#cfcfc8')}).bindTooltip(esc(p.n)).addTo(m));}
else document.getElementById('mapa').textContent='Mapa wymaga internetu.';
</script></body></html>"""


def main(plik=os.path.join(DANE, "wpisy_proba.jsonl")):
    punkty, wpisy = dane(plik)
    opis = (f"{len(punkty)} placówek z RSPO (zielone: wpisy pobrane, szare: ma stronę WWW, jasne: bez strony) · "
            f"{len(wpisy)} wpisów · punkty = wstępne sygnały inicjatywy (radar/sygnaly.py), nie ocena potencjału")
    # JSON w <script>: „</” rozbite, żeby tekst z obcych stron nie zamknął skryptu
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    out = SZABLON.replace("__OPIS__", html.escape(opis)).replace("__PUNKTY__", js(punkty)).replace("__WPISY__", js(wpisy))
    wy = os.path.join(TU, "..", "widok.html")
    open(wy, "w", encoding="utf-8").write(out)
    print(wy, len(punkty), "placówek,", len(wpisy), "wpisów")


if __name__ == "__main__":
    assert json.dumps("</script>").replace("</", "<\\/") == '"<\\/script>"'
    main(*sys.argv[1:2])
