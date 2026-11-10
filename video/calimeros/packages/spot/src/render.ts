import { sealVisualTrack } from "@hypit/composition";
import type { VisualElement } from "@hypit/composition";
import { htmlVisual } from "@hypit/html-program";
import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalWindowFor } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { logoDataUri } from "./logo-data.js";

export const beatKinds = ["hook", "crunch", "juicy", "menu", "share", "end"] as const;
export type BeatKind = typeof beatKinds[number];
export type Beat = { id: string; kind: BeatKind; text: string; sub: string; at: TemporalInstant };
export type SpotOptions = { id: string; cta: string };

/* ---------- brand palette ---------- */
const RED = "#D62300", RED_DARK = "#A81B00", YELLOW = "#FFC72C", CREAM = "#FFF4D6", BROWN = "#5A2A0A", WHITE = "#FFFFFF";

/* ---------- illustrations (1080-wide stage units) ---------- */
function meatPath(cx: number, cy: number, rx: number, ry: number, rot: number) {
  const points: string[] = [];
  for (let i = 0; i <= 72; i++) {
    const a = (i / 72) * Math.PI * 2;
    const bump = 1 + 0.06 * Math.sin(a * 9) + 0.035 * Math.sin(a * 17 + 1.3) + 0.025 * Math.sin(a * 5 + 0.4);
    const x = Math.cos(a) * rx * bump, y = Math.sin(a) * ry * bump;
    const xr = x * Math.cos(rot) - y * Math.sin(rot), yr = x * Math.sin(rot) + y * Math.cos(rot);
    points.push(`${(cx + xr).toFixed(1)},${(cy + yr).toFixed(1)}`);
  }
  return `M${points.join("L")}Z`;
}
function crumbs(seed: number, count: number, cx: number, cy: number, rx: number, ry: number) {
  let s = seed, out = "";
  const rnd = () => (s = (s * 9301 + 49297) % 233280) / 233280;
  for (let i = 0; i < count; i++) {
    const a = rnd() * Math.PI * 2, d = Math.sqrt(rnd());
    const x = cx + Math.cos(a) * rx * d, y = cy + Math.sin(a) * ry * d, r = 4 + rnd() * 9;
    out += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${rnd() > .5 ? "#FFD27A" : "#9C4A12"}" opacity="${(.45 + rnd() * .4).toFixed(2)}"/>`;
  }
  return out;
}
const BITES: Array<[number, number, number]> = [[340, 60, 62], [378, 128, 54], [290, 24, 48]];
function meatPoints(bitten: boolean) {
  const cx = 240, cy = 165, rx = 150, ry = 118, rot = -0.62, pts: Array<[number, number, boolean]> = [];
  for (let i = 0; i <= 96; i++) {
    const a = (i / 96) * Math.PI * 2;
    const bump = 1 + 0.06 * Math.sin(a * 9) + 0.035 * Math.sin(a * 17 + 1.3) + 0.025 * Math.sin(a * 5 + 0.4);
    const x = Math.cos(a) * rx * bump, y = Math.sin(a) * ry * bump;
    let px = cx + x * Math.cos(rot) - y * Math.sin(rot), py = cy + x * Math.sin(rot) + y * Math.cos(rot), cut = false;
    if (bitten) for (const [bx, by, br] of BITES) {
      const dx = px - bx, dy = py - by, d = Math.hypot(dx, dy);
      if (d < br) { const k = br / Math.max(d, 1e-3); px = bx + dx * k; py = by + dy * k; cut = true; }
    }
    pts.push([px, py, cut]);
  }
  return pts;
}
const pathOf = (pts: Array<[number, number, boolean]>) => `M${pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L")}Z`;
function drumstick(_prefix: string, bitten = false) {
  const outline = pathOf(meatPoints(false));
  return `<svg viewBox="0 0 420 420" class="drum">
  <g class="bone">
    <path d="M150 250 L70 335" stroke="#E9D6B4" stroke-width="44" stroke-linecap="round"/>
    <path d="M150 250 L70 335" stroke="#FFF6E4" stroke-width="30" stroke-linecap="round"/>
    <circle cx="48" cy="338" r="30" fill="#FFF6E4" stroke="#E9D6B4" stroke-width="7"/>
    <circle cx="70" cy="370" r="28" fill="#FFF6E4" stroke="#E9D6B4" stroke-width="7"/>
  </g>
  <path d="${outline}" fill="#B85A16" stroke="#7A320A" stroke-width="6" stroke-linejoin="round"/>
  <path d="${meatPath(232, 152, 128, 96, -0.62)}" fill="#E08A2B"/>
  <path d="${meatPath(220, 135, 92, 64, -0.62)}" fill="#F2A842"/>
  <path d="${meatPath(205, 118, 50, 30, -0.62)}" fill="#FFD27A" opacity=".8"/>
  ${crumbs(7, 60, 232, 158, 110, 80)}
  ${bitten ? `<g transform="rotate(-38 300 95)">
    <ellipse cx="300" cy="95" rx="84" ry="56" fill="#7A320A"/>
    <ellipse cx="300" cy="95" rx="74" ry="47" fill="#C96B1E"/>
    <ellipse cx="300" cy="97" rx="64" ry="39" fill="#F7DDB6"/>
    <path d="M250 92 q50 -18 100 0 M258 108 q42 -14 86 0 M268 80 q34 -10 66 0" stroke="#E7B98A" stroke-width="5" fill="none" stroke-linecap="round"/>
    <ellipse cx="282" cy="86" rx="16" ry="7" fill="#fff" opacity=".85"/>
  </g>` : ""}
  <ellipse cx="190" cy="105" rx="44" ry="16" fill="#fff" opacity=".3" transform="rotate(-35 190 105)"/>
</svg>`;
}
const fries = `<svg viewBox="0 0 300 300"><g fill="#FFC72C" stroke="#D99A00" stroke-width="4">
  <rect x="78" y="40" width="26" height="150" rx="6" transform="rotate(-10 91 115)"/><rect x="112" y="22" width="26" height="160" rx="6"/>
  <rect x="146" y="30" width="26" height="160" rx="6" transform="rotate(6 159 110)"/><rect x="180" y="44" width="26" height="150" rx="6" transform="rotate(14 193 119)"/>
  <rect x="96" y="58" width="24" height="140" rx="6" transform="rotate(4 108 128)"/><rect x="162" y="56" width="24" height="140" rx="6" transform="rotate(-6 174 126)"/></g>
  <path d="M55 120 L245 120 L222 285 L78 285 Z" fill="${RED}" stroke="${RED_DARK}" stroke-width="6" stroke-linejoin="round"/>
  <path d="M150 165 c-22 0 -34 28 -34 52 c0 22 15 34 34 34 c19 0 34 -12 34 -34 c0 -24 -12 -52 -34 -52z" fill="#FFF6E4"/>
  <path d="M116 222 l12 -10 l10 12 l12 -12 l12 12 l10 -12 l12 10" stroke="${RED}" stroke-width="5" fill="none"/></svg>`;
const burger = `<svg viewBox="0 0 300 300">
  <path d="M40 140 Q40 50 150 50 Q260 50 260 140 Z" fill="#EFA640" stroke="#B86A14" stroke-width="6"/>
  ${[[95, 90], [140, 75], [185, 88], [120, 112], [170, 110], [215, 115], [80, 120]].map(([x, y]) => `<ellipse cx="${x}" cy="${y}" rx="7" ry="4" fill="#FFF3D0"/>`).join("")}
  <path d="M30 150 q15 -16 30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0 l0 14 l-240 0z" fill="#4CB944" stroke="#2E8A2A" stroke-width="4"/>
  <path d="${meatPath(150, 192, 128, 30, 0)}" fill="#D47A22" stroke="#7A320A" stroke-width="6"/>
  <rect x="40" y="215" width="220" height="10" fill="#FFE07A"/>
  <path d="M42 228 L258 228 Q258 270 220 270 L80 270 Q42 270 42 228Z" fill="#EFA640" stroke="#B86A14" stroke-width="6"/></svg>`;
const bucket = `<svg viewBox="0 0 300 300">
  <path d="M40 90 L260 90 L232 290 L68 290 Z" fill="#fff" stroke="${RED_DARK}" stroke-width="6" stroke-linejoin="round"/>
  <g fill="${RED}">${[0, 1, 2, 3, 4].map(i => { const top = (k: number) => 40 + k * 22, bot = (k: number) => 68 + k * 16.4;
    const l = i * 2 + 0.5, r = l + 1; return `<path d="M${top(l)} 90 L${top(r)} 90 L${bot(r)} 290 L${bot(l)} 290Z"/>`; }).join("")}</g>
  <rect x="30" y="76" width="240" height="30" rx="10" fill="${RED}" stroke="${RED_DARK}" stroke-width="6"/>
  <circle cx="150" cy="190" r="48" fill="${YELLOW}" stroke="${RED_DARK}" stroke-width="6"/>
  <path d="M150 158 c-18 0 -27 22 -27 40 c0 17 12 26 27 26 c15 0 27 -9 27 -26 c0 -18 -9 -40 -27 -40z" fill="#fff"/></svg>`;
const wingsIcon = (p: string) => `<div class="wing w1">${drumstick(p + "a")}</div><div class="wing w2">${drumstick(p + "b")}</div><div class="wing w3">${drumstick(p + "c")}</div>`;
const steam = `<svg viewBox="0 0 300 300" class="steam">${[60, 150, 240].map((x, i) =>
  `<path class="puff" data-i="${i}" d="M${x} 280 q-30 -40 0 -80 t0 -80 t0 -80" stroke="#F0B65A" stroke-width="18" fill="none" stroke-linecap="round"/>`).join("")}</svg>`;
const burst = `<svg viewBox="-100 -100 200 200" class="burst"><polygon points="${Array.from({ length: 28 }, (_, i) => {
  const a = (i / 28) * Math.PI * 2, r = i % 2 ? 62 : 96; return `${(Math.cos(a) * r).toFixed(1)},${(Math.sin(a) * r).toFixed(1)}`;
}).join(" ")}" fill="${RED}" stroke="#fff" stroke-width="7" stroke-linejoin="round"/></svg>`;
const flyingCrumbs = Array.from({ length: 26 }, (_, i) => `<i class="crumb" data-i="${i}"></i>`).join("");

/** All scenes, their handoffs and motion share one stage; times are already resolved Instants. */
export function renderSpot(timeline: Timeline, within: SpatialFrame, window: TemporalWindow,
  font: FontStackRef, headline: FontStackRef, beats: readonly Beat[], options: SpotOptions) {
  assertTemporalWindowFor(window, { subjectId: options.id, timeline });
  if (beats.some(beat => beat.at.frame < window.span.startFrame || beat.at.frame >= window.span.endFrameExclusive)) throw new Error("Spot beats must start inside the window.");
  let order = 0;
  const text = (id: string, value: string, size: number, color: string, face: FontStackRef, lineHeight = 1): VisualElement => ({
    id, kind: "text", parent: "spot", order: ++order, text: value, fonts: face.faces,
    style: [{ name: "font-size", value: `${size}px` }, { name: "line-height", value: lineHeight }, { name: "color", value: color }],
  });
  const children: VisualElement[] = [];
  const sections = beats.map((beat, i) => {
    const t = `t-${i}`, s = `s-${i}`;
    const head = (size: number, color: string) => { children.push(text(t, beat.text, size, color, headline, .95)); return `<div class="hl">{{${t}}}</div>`; };
    const sub = (size: number, color: string) => { if (!beat.sub) return ""; children.push(text(s, beat.sub, size, color, font, 1.15)); return `<div class="sub">{{${s}}}</div>`; };
    switch (beat.kind) {
      case "hook": return `<section class="scene hook" data-kind="hook"><div class="rays"></div>
        <div class="crumbs">${flyingCrumbs}</div><div class="drumwrap">${drumstick("cal-h")}</div>
        <div class="burstwrap">${burst}<div class="title">${head(250, WHITE)}</div></div><div class="subwrap">${sub(64, BROWN)}</div></section>`;
      case "crunch": return `<section class="scene crunch" data-kind="crunch"><div class="rays"></div>
        <div class="title">${head(200, YELLOW)}</div><div class="drumwrap">${drumstick("cal-c")}</div>
        <div class="sparks">${Array.from({ length: 8 }, (_, k) => `<b data-i="${k}"></b>`).join("")}</div><div class="subwrap">${sub(84, WHITE)}</div></section>`;
      case "juicy": return `<section class="scene juicy" data-kind="juicy"><div class="rays"></div>
        <div class="title">${head(240, RED)}</div><div class="steamwrap">${steam}</div><div class="drumwrap">${drumstick("cal-j", true)}</div>
        <div class="subwrap">${sub(84, BROWN)}</div></section>`;
      case "menu": {
        const labels = beat.sub.split("|").map(label => label.trim()).filter(Boolean).slice(0, 4);
        const icons = [bucket, wingsIcon("cal-w"), burger, fries];
        const cards = labels.map((label, k) => { children.push(text(`m-${i}-${k}`, label, 78, RED, headline, 1));
          return `<div class="card" data-i="${k}"><div class="icon">${icons[k] ?? ""}</div><div class="label">{{m-${i}-${k}}}</div></div>`; }).join("");
        return `<section class="scene menu" data-kind="menu"><div class="rays"></div><div class="title">${head(150, RED)}</div><div class="grid">${cards}</div></section>`;
      }
      case "share": return `<section class="scene share" data-kind="share"><div class="rays"></div>
        <div class="title">${head(220, YELLOW)}</div>
        <div class="bucketwrap">${[0, 1, 2, 3].map(k => `<div class="pop" data-i="${k}">${drumstick(`cal-s${k}`)}</div>`).join("")}<div class="bk">${bucket}</div></div>
        <div class="subwrap">${sub(88, WHITE)}</div></section>`;
      case "end": {
        children.push(text("cta", options.cta, 84, WHITE, headline, 1));
        return `<section class="scene end" data-kind="end"><div class="rays"></div><div class="glow"></div>
          <div class="logo"><img src="${logoDataUri}" alt=""/></div><div class="title">${head(104, RED)}</div>
          <div class="ctawrap"><div class="cta">{{cta}}</div></div><div class="subwrap">${sub(50, BROWN)}</div></section>`;
      }
    }
  }).join("");
  const start = window.span.startFrame;
  const program = htmlVisual({
    html: `<div class="stage">${sections}</div>`,
    css: `:scope{overflow:hidden;background:${YELLOW}}
      .stage{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0;transform:scale(${within.widthPx / 1080})}
      .scene{position:absolute;inset:0;overflow:hidden;display:none}
      .rays{position:absolute;left:50%;top:50%;width:3200px;height:3200px;margin:-1600px 0 0 -1600px}
      .hook{background:${YELLOW}}.hook .rays{background:repeating-conic-gradient(#FFB300 0 9deg,${YELLOW} 9deg 18deg)}
      .crunch{background:${RED}}.crunch .rays{background:repeating-conic-gradient(${RED_DARK} 0 9deg,${RED} 9deg 18deg)}
      .juicy{background:${CREAM}}.juicy .rays{background:repeating-conic-gradient(#FFE7A6 0 9deg,${CREAM} 9deg 18deg)}
      .menu{background:${YELLOW}}.menu .rays{background:repeating-conic-gradient(#FFB300 0 9deg,${YELLOW} 9deg 18deg)}
      .share{background:${RED}}.share .rays{background:repeating-conic-gradient(${RED_DARK} 0 9deg,${RED} 9deg 18deg)}
      .end{background:${YELLOW}}.end .rays{background:repeating-conic-gradient(#FFB300 0 7deg,${YELLOW} 7deg 14deg)}
      .title,.subwrap{position:absolute;left:40px;right:40px;text-align:center}
      .hl{text-transform:uppercase;letter-spacing:2px;paint-order:stroke fill}
      .sub{font-weight:800;paint-order:stroke fill}
      .drum{width:100%;height:100%;overflow:visible}
      .hook .hl{-webkit-text-stroke:14px ${BROWN};text-shadow:0 14px 0 ${BROWN}}
      .hook .drumwrap{position:absolute;left:150px;top:820px;width:780px;height:780px}
      .hook .burstwrap{position:absolute;left:40px;right:40px;top:170px;height:600px}
      .hook .burst{position:absolute;left:50%;top:50%;width:820px;height:820px;margin:-410px 0 0 -410px}
      .hook .title{top:200px}.hook .subwrap{top:1650px}
      .hook .sub{background:#fff;display:inline-block;padding:18px 36px;border-radius:60px;box-shadow:0 10px 0 ${BROWN}}
      .crumbs{position:absolute;inset:0}.crumb{position:absolute;left:0;top:0;width:26px;height:26px;border-radius:40%;background:#E08A2B;box-shadow:inset -4px -4px 0 #9C4A12}
      .crunch .title{top:180px}.crunch .hl{-webkit-text-stroke:12px ${RED_DARK};text-shadow:0 14px 0 #6E1200}
      .crunch .drumwrap{position:absolute;left:90px;top:520px;width:900px;height:900px}
      .crunch .subwrap{top:1560px}.crunch .sub{text-shadow:0 8px 0 #6E1200}
      .sparks b{position:absolute;width:70px;height:70px;background:#fff;clip-path:polygon(50% 0,62% 38%,100% 50%,62% 62%,50% 100%,38% 62%,0 50%,38% 38%)}
      .juicy .title{top:170px}.juicy .hl{-webkit-text-stroke:12px #fff;text-shadow:0 14px 0 ${RED_DARK}}
      .juicy .drumwrap{position:absolute;left:110px;top:620px;width:880px;height:880px}
      .juicy .steamwrap{position:absolute;left:470px;top:330px;width:420px;height:420px;opacity:.9}
      .juicy .subwrap{top:1600px}
      .menu .title{top:150px}.menu .hl{-webkit-text-stroke:10px #fff;text-shadow:0 10px 0 ${RED_DARK}}
      .grid{position:absolute;left:60px;right:60px;top:520px;display:grid;grid-template-columns:1fr 1fr;gap:44px}
      .card{height:600px;background:#fff;border-radius:48px;box-shadow:0 18px 0 ${RED_DARK};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border:8px solid ${RED}}
      .card .icon{width:340px;height:340px;position:relative}.card .icon svg{width:100%;height:100%}
      .wing{position:absolute;width:210px;height:210px}.w1{left:10px;top:30px;transform:rotate(-20deg)}.w2{left:130px;top:10px;transform:rotate(15deg)}.w3{left:70px;top:130px;transform:rotate(-5deg)}
      .share .title{top:170px}.share .hl{-webkit-text-stroke:12px ${RED_DARK};text-shadow:0 14px 0 #6E1200}
      .bucketwrap{position:absolute;left:160px;top:600px;width:760px;height:900px}
      .bk{position:absolute;left:0;top:140px;width:760px;height:760px}.bk svg{width:100%;height:100%}
      .pop{position:absolute;width:360px;height:360px;top:120px}
      .pop[data-i="0"]{left:30px}.pop[data-i="1"]{left:200px}.pop[data-i="2"]{left:380px}.pop[data-i="3"]{left:110px}
      .share .subwrap{top:1600px}.share .sub{text-shadow:0 8px 0 #6E1200}
      .end .glow{position:absolute;left:90px;top:330px;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,#fff 0,#fff8 40%,#fff0 70%)}
      .end .logo{position:absolute;left:90px;top:400px;width:900px;height:672px}.end .logo img{width:100%;height:100%;filter:drop-shadow(0 18px 0 #0003)}
      .end .title{top:1150px}.end .hl{-webkit-text-stroke:10px #fff;letter-spacing:1px}
      .ctawrap{position:absolute;left:0;right:0;top:1400px;text-align:center}
      .cta{display:inline-block;background:${RED};padding:34px 80px 26px;border-radius:90px;box-shadow:0 14px 0 ${RED_DARK};-webkit-text-stroke:0}
      .end .subwrap{top:1640px}`,
    data: { starts: beats.map(beat => beat.at.frame - start), end: window.span.endFrameExclusive - start, wipe: 9 },
    setup: `const scenes=[...root.querySelectorAll('.scene')];
      const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)), ease=t=>1-Math.pow(1-clamp(t),3);
      const back=t=>{t=clamp(t);const c=1.9;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2);};
      const pop=(age,dur)=>age<0?0:back(age/dur);
      const q=(el,s)=>el.querySelector(s), qa=(el,s)=>[...el.querySelectorAll(s)];
      const crumbData=Array.from({length:26},(_,i)=>{const a=-Math.PI*(0.08+0.84*((i*37)%26)/26);const v=18+((i*53)%17);return{vx:Math.cos(a)*v,vy:Math.sin(a)*v-6,r:(i*29)%360,s:.6+((i*13)%10)/12};});
      const anim={
        hook(el,a){
          q(el,'.rays').style.transform='rotate('+(a*0.6)+'deg)';
          const drop=ease(a/6), impact=a-6;
          const squash=impact>=0&&impact<8?Math.sin(impact/8*Math.PI)*0.12:0;
          q(el,'.drumwrap').style.transform='translateY('+(-520*(1-drop))+'px) rotate('+(-30+30*drop+Math.sin(a*.15)*3)+'deg) scale('+(1+squash)+','+(1-squash)+')';
          const shake=impact>=0&&impact<12?(12-impact)*1.6:0;
          el.style.transform='translate('+(Math.sin(a*2.7)*shake)+'px,'+(Math.cos(a*3.1)*shake)+'px)';
          const b=pop(impact,9);
          q(el,'.burst').style.transform='scale('+b+') rotate('+(a*1.2)+'deg)';
          q(el,'.title').style.transform='scale('+(impact<0?0:back((impact)/7)*(1+0.04*Math.sin(a*.5)))+') rotate(-6deg)';
          qa(el,'.crumb').forEach((c,i)=>{const d=crumbData[i], t=impact; if(t<0){c.style.opacity='0';return;}
            c.style.opacity=String(clamp(1-t/40));
            c.style.transform='translate('+(540+d.vx*t)+'px,'+(1150+d.vy*t+0.9*t*t)+'px) rotate('+(d.r+t*12)+'deg) scale('+d.s+')';});
          const s=q(el,'.subwrap'); s.style.opacity=String(ease((a-14)/8)); s.style.transform='translateY('+(60*(1-ease((a-14)/8)))+'px)';
        },
        crunch(el,a){
          q(el,'.rays').style.transform='rotate('+(-a*0.5)+'deg)';
          q(el,'.title').style.transform='scale('+(a<2?0:(1+1.4*(1-ease((a-2)/7))))+')'; q(el,'.title').style.opacity=String(clamp((a-2)/3));
          q(el,'.drumwrap').style.transform='rotate('+(-14+a*0.35)+'deg) scale('+(0.9+0.15*ease(a/30))+')';
          qa(el,'.sparks b').forEach((b,i)=>{const p=(a*0.9+i*9)%36/36, x=[210,830,260,800,150,900,480,620][i], y=[700,640,1240,1300,980,980,560,1420][i];
            b.style.left=x+'px';b.style.top=y+'px';b.style.transform='scale('+Math.sin(p*Math.PI)+') rotate('+(p*90)+'deg)';});
          const s=q(el,'.subwrap'); s.style.opacity=String(ease((a-10)/8)); s.style.transform='translateX('+(-400*(1-ease((a-10)/8)))+'px)';
        },
        juicy(el,a){
          q(el,'.rays').style.transform='rotate('+(a*0.4)+'deg)';
          q(el,'.title').style.transform='scale('+pop(a-2,8)+') rotate(4deg)';
          q(el,'.drumwrap').style.transform='translateY('+(Math.sin(a*.12)*14)+'px) rotate('+(8+Math.sin(a*.08)*3)+'deg)';
          qa(el,'.puff').forEach((p,i)=>{const t=((a+i*10)%34)/34; p.style.opacity=String(Math.sin(t*Math.PI)*0.9); p.style.transform='translateY('+(-90*t)+'px)';});
          const s=q(el,'.subwrap'); s.style.opacity=String(ease((a-10)/8)); s.style.transform='translateX('+(400*(1-ease((a-10)/8)))+'px)';
        },
        menu(el,a){
          q(el,'.rays').style.transform='rotate('+(a*0.5)+'deg)';
          q(el,'.title').style.transform='translateY('+(-300*(1-ease(a/8)))+'px)';
          qa(el,'.card').forEach((c,i)=>{const t=a-6-i*11; c.style.transform='scale('+pop(t,10)+') rotate('+((i%2?3:-3)*(1-ease(t/10)))+'deg)';
            const ic=q(c,'.icon'); ic.style.transform='translateY('+(Math.sin((a+i*8)*.14)*10)+'px)';});
        },
        share(el,a){
          q(el,'.rays').style.transform='rotate('+(-a*0.5)+'deg)';
          q(el,'.title').style.transform='scale('+pop(a-1,8)+')';
          q(el,'.bk').style.transform='translateY('+(700*(1-ease(a/8)))+'px)';
          qa(el,'.pop').forEach((p,i)=>{const t=a-10-i*6; const h=t<0?0:back(t/8); p.style.transform='translateY('+(320-340*h)+'px) rotate('+([-25,-5,15,-12][i]+Math.sin((a+i*5)*.2)*5)+'deg)'; p.style.opacity=t<0?'0':'1';});
          const s=q(el,'.subwrap'); s.style.opacity=String(ease((a-18)/8)); s.style.transform='scale('+(0.6+0.4*ease((a-18)/8))+')';
        },
        end(el,a){
          q(el,'.rays').style.transform='rotate('+(a*0.7)+'deg)';
          q(el,'.glow').style.transform='scale('+(0.9+0.08*Math.sin(a*.15))+')';
          q(el,'.logo').style.transform='translateY('+(Math.sin(a*.1)*10)+'px) scale('+pop(a-3,12)+')';
          q(el,'.title').style.transform='scale('+pop(a-14,9)+')';
          const c=q(el,'.ctawrap'); const ct=a-22; c.style.transform='translateY('+(300*(1-ease(ct/9)))+'px) scale('+(ct<9?1:1+0.05*Math.sin((ct-9)*.25))+')'; c.style.opacity=String(clamp(ct/4));
          const s=q(el,'.subwrap'); s.style.opacity=String(ease((a-30)/8));
        }
      };
      return frame=>{
        scenes.forEach((el,i)=>{
          const s=data.starts[i], next=i+1<data.starts.length?data.starts[i+1]:data.end, a=frame-s;
          const visible=frame>=s&&frame<next+data.wipe;
          el.style.display=visible?'block':'none'; if(!visible)return;
          el.style.clipPath=i===0?'none':'circle('+(ease(a/data.wipe)*120)+'% at 50% 55%)';
          anim[el.dataset.kind](el,a);
        });
      };`,
  });
  return sealVisualTrack({ id: options.id, timelineId: timeline.id, visualIr: "hypit.visual-ir@1",
    presents: [{ id: options.id, order: 0, z: 0, span: window.span,
      elements: [{ id: "spot", kind: "program", order: 0, program,
        style: [{ name: "position", value: "absolute" }, { name: "left", value: `${within.xPx}px` },
          { name: "top", value: `${within.yPx}px` },
          { name: "width", value: `${within.widthPx}px` }, { name: "height", value: `${within.heightPx}px` }] }, ...children] }] });
}
