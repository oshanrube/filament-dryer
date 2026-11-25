// The dryer's own web page (http://filament-dryer-xxxx.local/) and the firmware update form.
#pragma once
#include <pgmspace.h>

static const char PAGE_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Filament dryer</title>
<style>
:root{--bg:#f6f7f9;--fg:#16181d;--muted:#5b6170;--card:#fff;--line:#e1e4ea;--acc:#2563eb;--bad:#c62828}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--fg:#e9ebef;--muted:#9aa1ad;--card:#1b1e23;--line:#2c3038;--acc:#6ea0ff;--bad:#ff6b6b}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif}
main{max-width:560px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:12px}
.row{display:flex;justify-content:space-between;padding:3px 0}.row span:first-child{color:var(--muted)}
.big{font-size:22px;font-weight:600}.bad{color:var(--bad);font-weight:600}
button,select,input{font:inherit;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
button.p{background:var(--acc);border-color:var(--acc);color:#fff}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
small{color:var(--muted)}
</style></head><body><main>
<h1 id="name">Filament dryer</h1>
<div class="card"><div class="big" id="mode">…</div><div id="fault"></div>
<div class="btns"><select id="mat"><option>PLA</option><option>PETG</option><option>ABS</option><option>ASA</option><option>TPU</option><option>NYLON</option><option>PC</option></select>
<button class="p" onclick="mode('dry')">Dry</button><button onclick="mode('keep_dry')">Keep dry</button><button onclick="mode('print')">Print</button><button onclick="mode('off')">Off</button></div>
<div class="btns" id="clr" hidden><button onclick="post('/api/fault/clear')">Clear fault</button></div></div>
<div class="card" id="vals"></div>
<div class="card"><b>Scale</b><div class="btns"><button onclick="post('/api/tare')">Tare (empty cradle)</button>
<input id="cal" type="number" placeholder="grams on cradle" style="width:130px"><button onclick="calib()">Calibrate</button></div>
<div class="btns"><input id="empty" type="number" placeholder="empty reel g" style="width:130px"><button onclick="setEmpty()">Set empty reel weight</button></div></div>
<small id="ver"></small> · <a href="/update">firmware update</a>
</main><script>
const $=id=>document.getElementById(id);
function row(k,v){return '<div class="row"><span>'+k+'</span><span>'+v+'</span></div>'}
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):''});show(await r.json())}
function mode(m){post('/api/mode',{mode:m,material:$('mat').value})}
function calib(){post('/api/calibrate',{grams:+$('cal').value})}
function setEmpty(){post('/api/config',{empty_reel_g:+$('empty').value})}
function f1(v){return (+v).toFixed(1)}
function show(s){if(s.error){alert(s.error);return}
$('name').textContent=s.name;$('ver').textContent='firmware '+s.version;
let m={off:'Off',dry:'Drying',keep_dry:'Keep dry',print:'Print mode'}[s.mode]||s.mode;
if(s.mode=='dry'){const r=s.dry_remaining_s;m+=' · '+s.material+' '+s.setpoint_c+' °C · '+Math.floor(r/3600)+' h '+Math.floor(r%3600/60)+' min left'}
else if(s.mode=='print')m+=' · '+s.material+' '+s.setpoint_c+' °C';else if(s.boost)m+=' · boost 45 °C';
$('mode').textContent=m;$('fault').innerHTML=s.fault!='none'?'<span class="bad">Fault: '+s.fault.replace(/_/g,' ')+'</span>':'';$('clr').hidden=s.fault=='none';
if(document.activeElement!==$('mat'))$('mat').value=s.material;
$('vals').innerHTML=row('Chamber',s.chamber.ok?f1(s.chamber.c)+' °C · '+Math.round(s.chamber.rh)+' % RH ('+s.chamber.sensor+')':'<span class="bad">no sensor</span>')
+row('Heater outlet',s.outlet.ok?f1(s.outlet.c)+' °C':'<span class="bad">no probe</span>')
+row('Heater',Math.round(s.heater.duty*100)+' %')+row('Blower / exhaust',(s.blower?'on':'off')+' / '+(s.exhaust?'on':'off'))
+(s.bay.ok?row('Bay',f1(s.bay.c)+' °C · '+Math.round(s.bay.rh)+' % RH'):'')
+row('Reel',s.scale.ok?Math.round(s.scale.grams_left)+' g left · '+Math.round(s.scale.metres_left)+' m (cradle '+Math.round(s.scale.grams)+' g)':'no scale reading')
+row('Filament',(s.filament.present?'present':'<span class="bad">not detected</span>')+' · moved '+Math.round(s.filament.motion_mm)+' mm')
+row('Wi-Fi',s.ip+' · '+s.rssi+' dBm')}
async function tick(){try{show(await (await fetch('/api/state')).json())}catch(e){}}
tick();setInterval(tick,2000);
</script></body></html>)HTML";

static const char UPDATE_HTML[] PROGMEM = R"HTML(<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Firmware update</title></head><body style="font:15px system-ui;max-width:520px;margin:24px auto;padding:0 16px">
<h1 style="font-size:20px">Firmware update</h1><p>Choose the app image (<code>dryer-1roll.bin</code>, not the <code>-full</code> one).
The heater switches off while the dryer restarts.</p>
<form method="POST" action="/update" enctype="multipart/form-data"><input type="file" name="firmware" accept=".bin"> <button>Upload</button></form>
<p><a href="/">back</a></p></body></html>)HTML";
