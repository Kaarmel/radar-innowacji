"""50 wpisów do ręcznej oceny → dane/etykiety.html (+ dane/etykiety_proba.json z punktami sygnałów do późniejszego porównania).

Losowanie warstwowe po punktach (≥5, 3–4, <3), maks. 1 wpis na szkołę, punkty ukryte (ocena „na ślepo”).
Strona zawiera fragmenty tekstów (imiona uczniów) → tylko lokalnie w dane/, nie publikować.
Wyniki: przycisk „Pobierz wyniki” zapisuje etykiety_wyniki.json (zapis roboczy w przeglądarce).
"""
import html
import json
import os
import random

from sygnaly import ocena

DANE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dane")


def proba(wpisy, ile=(17, 17, 16), ziarno=2026):
    los = random.Random(ziarno)
    los.shuffle(wpisy)
    warstwy = [lambda p: p >= 5, lambda p: 3 <= p < 5, lambda p: p < 3]
    wybrane, szkoly = [], set()
    for warunek, n in zip(warstwy, ile):
        k = 0
        for w in wpisy:
            if k < n and w["zrodlo_id"] not in szkoly and warunek(w["pkt"]):
                wybrane.append(w)
                szkoly.add(w["zrodlo_id"])
                k += 1
    los.shuffle(wybrane)
    return wybrane


SZABLON = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ocena wpisów</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px;background:#fafaf7;color:#1d1d1b}
.w{border:1px solid #ddd;border-radius:8px;padding:12px;margin:12px 0;background:#fff}.w.ok{opacity:.55}
.m{color:#666;font-size:13px}.t{font-size:14px;margin:6px 0}button{font:inherit;padding:6px 14px;margin-right:6px;border:1px solid #999;border-radius:6px;background:#fff;cursor:pointer}
button.on{background:#0b6e4f;color:#fff;border-color:#0b6e4f}input{font:inherit;width:100%;margin-top:6px;padding:4px;box-sizing:border-box}
#pasek{position:sticky;top:0;background:#fafaf7;padding:8px 0;border-bottom:1px solid #ddd}
</style></head><body>
<div id="pasek"><b>Ocena wpisów</b> · <span id="ile"></span> · <button id="pobierz">Pobierz wyniki</button></div>
<p class="m"><b>TAK</b> = oddolna inicjatywa: uczniowie, nauczyciele albo lokalna społeczność sami stworzyli, zbudowali lub uruchomili coś nowego
(projekt, wynalazek, aplikację, koło, akcję), co mogłoby się rozwinąć dalej.<br><b>NIE</b> = rutyna, uroczystość, ogłoszenie, wycieczka, zwykły udział w konkursie.
<b>?</b> = nie da się ocenić. Notatka opcjonalna. Zapis automatyczny w przeglądarce; na koniec „Pobierz wyniki”.</p>
<div id="lista"></div>
<script>
const D=__DANE__, K='etykiety_v1';
let S={}; try{S=JSON.parse(localStorage.getItem(K))||{}}catch(e){}
const zapisz=()=>{try{localStorage.setItem(K,JSON.stringify(S))}catch(e){}; licz()};
const licz=()=>document.getElementById('ile').textContent=`ocenione ${Object.values(S).filter(x=>x.o).length} / ${D.length}`;
const L=document.getElementById('lista');
D.forEach((w,i)=>{const d=document.createElement('div');d.className='w';d.innerHTML=
 `<div class="m">${i+1}. ${w.n} · ${w.d||'brak daty'}</div><a href="${w.l}" target="_blank" rel="noopener"><b>${w.t}</b></a><div class="t">${w.x}…</div>
 <button data-o="tak">TAK</button><button data-o="nie">NIE</button><button data-o="?">?</button><input placeholder="notatka (opcjonalnie)">`;
 const s=S[w.id]||(S[w.id]={}), inp=d.querySelector('input'), bs=d.querySelectorAll('button');
 const pokaz=()=>{bs.forEach(b=>b.classList.toggle('on',b.dataset.o===s.o));d.classList.toggle('ok',!!s.o)};
 bs.forEach(b=>b.onclick=()=>{s.o=b.dataset.o;pokaz();zapisz()}); inp.value=s.n||''; inp.oninput=()=>{s.n=inp.value;zapisz()};
 pokaz(); L.appendChild(d)});
document.getElementById('pobierz').onclick=()=>{const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([JSON.stringify(S,null,1)],{type:'application/json'}));a.download='etykiety_wyniki.json';a.click()};
licz();
</script></body></html>"""


def main():
    wpisy = [json.loads(l) for l in open(os.path.join(DANE, "wpisy.jsonl"), encoding="utf-8")]
    wpisy = [w for w in wpisy if w["link"].startswith(("http://", "https://"))]
    inst = {str(x["rspo"]): x["nazwa"] for x in map(json.loads, open(os.path.join(DANE, "instytucje.jsonl"), encoding="utf-8"))}
    for w in wpisy:
        w["pkt"] = ocena(w["tytul"] + " " + w["tekst"][:3000])[0]
    p = proba(wpisy)
    e = html.escape
    dane = [{"id": w["link"], "t": e(w["tytul"]), "l": e(w["link"]), "d": w["data"], "n": e(inst.get(str(w["zrodlo_id"]), w["www"])),
             "x": e(w["tekst"][:700])} for w in p]
    js = json.dumps(dane, ensure_ascii=False).replace("</", "<\\/")
    open(os.path.join(DANE, "etykiety.html"), "w", encoding="utf-8").write(SZABLON.replace("__DANE__", js))
    json.dump([{"link": w["link"], "zrodlo_id": w["zrodlo_id"], "pkt": w["pkt"]} for w in p],
              open(os.path.join(DANE, "etykiety_proba.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(p), "wpisów; punkty:", sorted(w["pkt"] for w in p))


if __name__ == "__main__":
    t = [{"zrodlo_id": i % 30, "pkt": i % 8} for i in range(300)]
    p = proba(t, (3, 3, 3))
    assert len(p) == 9 and len({w["zrodlo_id"] for w in p}) == 9
    assert sum(w["pkt"] >= 5 for w in p) == 3 and sum(w["pkt"] < 3 for w in p) == 3
    main()
