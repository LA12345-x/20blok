const {chromium}=require('playwright');const fs=require('fs');
const F=__dirname+'/node_modules/@fontsource/';
const iss=JSON.parse(process.argv[2]);const fu=f=>'data:font/woff2;base64,'+fs.readFileSync(F+f).toString('base64');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1200,height:630}});
for(const i of iss){
const img='data:image/jpeg;base64,'+fs.readFileSync(i.cover).toString('base64');
await p.setContent(`<style>
@font-face{font-family:PF;font-weight:900;src:url(${fu('playfair-display/files/playfair-display-latin-900-normal.woff2')})}
@font-face{font-family:PF;font-weight:700;src:url(${fu('playfair-display/files/playfair-display-latin-700-normal.woff2')})}
@font-face{font-family:IN;font-weight:700;src:url(${fu('inter/files/inter-latin-700-normal.woff2')})}
*{margin:0;box-sizing:border-box}body{width:1200px;height:630px;background:#0b0b0b;display:flex;overflow:hidden}
.l{width:600px;flex:none;padding:0 56px;display:flex;flex-direction:column;justify-content:center;gap:26px;border-right:4px solid #e0473c}
.w{font:900 104px/0.9 PF;color:#fff;letter-spacing:-1px;white-space:nowrap}.w b{color:#e0473c;font-weight:900}
.k{font:700 24px IN;letter-spacing:4px;color:#e0473c;text-transform:uppercase}
.t{font:700 ${i.title.length>26?42:52}px/1.12 PF;color:#fff;text-wrap:balance}
.r{flex:1;background:url(${img}) ${i.pos||'center/cover'}}</style>
<div class=l><div class=w><b>20</b> BLOK</div><div class=k>Issue ${i.n} · ${i.month}</div><div class=t>${i.title}</div></div><div class=r></div>`,{waitUntil:'load'});
await p.evaluate(()=>document.fonts.ready);
await p.screenshot({path:i.out,type:'png'});}
await b.close();})();
