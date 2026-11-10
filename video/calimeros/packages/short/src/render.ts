import { sealVisualTrack } from "@hypit/composition";
import type { VisualElement } from "@hypit/composition";
import { htmlVisual } from "@hypit/html-program";
import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalWindowFor } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";

export const beatKinds = ["crack", "split", "word", "build", "logo", "cta"] as const;
export type BeatKind = typeof beatKinds[number];
export type Beat = { id: string; kind: BeatKind; text: string; sub: string; at: TemporalInstant };
export type ShortOptions = { id: string; cta: string };

/* Brand colours sampled from the Calimero's Chicken logo. */
const NAVY = "#12306E", GLOW = "#6CCBF5", RED = "#D3202F", CREAM = "#FFE38A", MINT = "#E7F4C8", SHELL = "#FBF7EE";
const YELLOW = "#FFC72C", INK = "#141414", PAPER = "#F6F1E7";

/* One irregular crack, echoing the jagged edge of the logo's shell. f: 0..1 across, v: tooth height. */
const CRACK: Array<[number, number]> = [[0, .1], [.08, -.55], [.15, .35], [.24, -.95], [.31, .2], [.4, -.6], [.48, .55], [.57, -1], [.64, .3], [.73, -.5], [.81, .5], [.9, -.75], [1, .1]];
const FULL = { x0: -30, x1: 1110, y: 960, amp: 38 };          // crack across the whole stage
const EGG = { x0: 345, x1: 735, y: 860, amp: 30, top: 330 };   // the same crack as the shell's edge
const pts = (g: { x0: number; x1: number; y: number; amp: number }) => CRACK.map(([f, v]) => [g.x0 + f * (g.x1 - g.x0), g.y + v * g.amp] as const);
const poly = (p: ReadonlyArray<readonly [number, number]>) => p.map(([x, y]) => `${x.toFixed(1)}% ${y.toFixed(1)}%`).join(",");
const toPct = (p: ReadonlyArray<readonly [number, number]>) => p.map(([x, y]) => [x / 10.8, y / 19.2] as const);
const fullPct = toPct(pts(FULL));
const TOP_CLIP = `polygon(-5% -5%,105% -5%,${poly([...fullPct].reverse())})`;
const BOTTOM_CLIP = `polygon(${poly(fullPct)},105% 105%,-5% 105%)`;
const eggPts = pts(EGG), [ex0, ey0] = eggPts[0]!, [ex1, ey1] = eggPts[eggPts.length - 1]!;
const EW = EGG.x1 - EGG.x0, EH = EGG.y - EGG.top;
const DOME = `M${ex0},${ey0} C${ex0 - EW * .06},${EGG.y - EH * .55} ${540 - EW * .26},${EGG.top} 540,${EGG.top} C${540 + EW * .26},${EGG.top} ${ex1 + EW * .06},${EGG.y - EH * .55} ${ex1},${ey1}`;
const SHELL_PATH = `${DOME} L${[...eggPts].reverse().map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L")} Z`;
const BACK_PATH = `${DOME} L${ex1 - 4},${EGG.y + 60} L${ex0 + 4},${EGG.y + 60} Z`;

/** Crack → split → words → the same crack becomes the logo. All timing comes from the authored events. */
export function renderShort(timeline: Timeline, within: SpatialFrame, window: TemporalWindow,
  font: FontStackRef, headline: FontStackRef, brand: FontStackRef, beats: readonly Beat[], options: ShortOptions) {
  assertTemporalWindowFor(window, { subjectId: options.id, timeline });
  const start = window.span.startFrame, at = (beat: Beat) => beat.at.frame - start;
  const one = (kind: BeatKind) => { const beat = beats.find(item => item.kind === kind); if (!beat) throw new Error(`Short needs a ${kind} event.`); return beat; };
  const words = beats.filter(beat => beat.kind === "word"), logo = one("logo");
  let order = 0;
  const text = (id: string, value: string, size: number, color: string, face: FontStackRef): VisualElement => ({
    id, kind: "text", parent: "short", order: ++order, text: value, fonts: face.faces,
    style: [{ name: "font-size", value: `${size}px` }, { name: "line-height", value: 1 }, { name: "color", value: color }],
  });
  const children: VisualElement[] = [];
  words.forEach((word, i) => children.push(text(`w-${i}`, word.text, 196, INK, font)));
  const letters = [...logo.text];
  letters.forEach((letter, i) => children.push(text(`l-${i}`, letter, 150, CREAM, headline)));
  children.push(text("chicken", logo.sub, 92, MINT, brand));
  children.push(text("cta", options.cta, 38, INK, font));
  const program = htmlVisual({
    html: `<div class="stage">
      <div class="brand">
        <svg class="art" viewBox="0 0 1080 1920" width="1080" height="1920">
          <path class="egg-glow" d="${SHELL_PATH}"/>
          <path class="egg-back" d="${BACK_PATH}"/>
          <path class="egg-shell" d="${SHELL_PATH}"/>
          <path class="egg-shade" d="M650,430 C720,520 745,700 728,850 L690,842 C705,700 690,540 650,430Z"/>
          <ellipse class="egg-hi" cx="465" cy="470" rx="40" ry="78" transform="rotate(22 465 470)"/>
          <path class="egg-line" d="${DOME}"/>
          <path class="morph" d=""/>
        </svg>
        <div class="plate"><div class="row">${letters.map((_, i) => `<span class="letter" data-i="${i}">{{l-${i}}}</span>`).join("")}</div>
          <div class="chick">{{chicken}}</div></div>
        <div class="ctawrap"><div class="rule"></div><div class="cta">{{cta}}</div></div>
      </div>
      <div class="half y top"></div><div class="half y bottom"></div>
      <div class="words">${words.map((_, i) => `<div class="word" data-i="${i}"><div class="inner">{{w-${i}}}<i class="dot"></i></div></div>`).join("")}</div>
      <div class="half k top"></div><div class="half k bottom"></div>
      <svg class="crackline" viewBox="0 0 1080 1920" width="1080" height="1920"><path class="c1" d=""/><path class="c2" d=""/></svg>
    </div>`,
    css: `:scope{overflow:hidden;background:${PAPER}}
      .stage{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0;transform:scale(${within.widthPx / 1080})}
      .brand{position:absolute;inset:0;background:${PAPER}}
      .art{position:absolute;left:0;top:0}
      .half{position:absolute;inset:0;will-change:transform}
      .half.top{clip-path:${TOP_CLIP}}.half.bottom{clip-path:${BOTTOM_CLIP}}
      .half.k{background:#0E0E0E}.half.y{background:${YELLOW}}
      .crackline{position:absolute;left:0;top:0;overflow:visible}
      .crackline path,.morph{fill:none;stroke-linecap:round;stroke-linejoin:round}
      .c1{stroke:#fff;stroke-width:5}.c2{stroke:${NAVY};stroke-width:7}
      .words{position:absolute;left:0;right:0;top:0;bottom:0}
      .word{position:absolute;left:0;right:0;top:850px;height:230px;overflow:hidden;text-align:center}
      .inner{display:inline-flex;align-items:flex-end;font-weight:900;letter-spacing:-6px;white-space:nowrap}
      .dot{display:inline-block;width:34px;height:34px;border-radius:50%;background:${RED};margin:0 0 30px 12px;flex:none}
      .egg-glow{fill:none;stroke:${GLOW};stroke-width:44;stroke-linejoin:round}
      .egg-back{fill:${NAVY}}
      .egg-shell{fill:${SHELL};stroke:${NAVY};stroke-width:14;stroke-linejoin:round}
      .egg-shade{fill:#E9E1CF}.egg-hi{fill:#fff}
      .egg-line{fill:none;stroke:${NAVY};stroke-width:14;stroke-linecap:round}
      .morph{stroke:${NAVY};stroke-width:14}
      .plate{position:absolute;left:70px;right:70px;top:${EGG.y + 22}px;height:330px;border-radius:64px 64px 150px 150px / 64px 64px 90px 90px;
        background:${NAVY};box-shadow:0 0 0 14px ${GLOW},0 26px 40px #12306E33;transform-origin:50% 0}
      .row{position:absolute;left:0;right:0;top:34px;display:flex;justify-content:center}
      .letter{display:inline-block;-webkit-text-stroke:16px ${RED};paint-order:stroke fill;text-shadow:0 7px 0 #8E1018;margin:0 -1px;transform-origin:50% 80%}
      .chick{position:absolute;left:0;right:0;top:205px;text-align:center;letter-spacing:6px;-webkit-text-stroke:6px ${NAVY};paint-order:stroke fill}
      .ctawrap{position:absolute;left:0;right:0;top:1330px;text-align:center}
      .rule{width:0;height:4px;background:${RED};margin:0 auto 34px}
      .cta{display:inline-block;letter-spacing:14px;text-transform:uppercase;font-weight:900;opacity:0}`,
    data: { crack: at(one("crack")), split: at(one("split")), words: words.map(at), build: at(one("build")), logo: at(logo), cta: at(one("cta")),
      end: window.span.endFrameExclusive - start, full: pts(FULL), egg: eggPts },
    setup: `const q=s=>root.querySelector(s), qa=s=>[...root.querySelectorAll(s)];
      const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
      const io=t=>{t=clamp(t);return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;}, out=t=>1-Math.pow(1-clamp(t),4);
      const back=t=>{t=clamp(t);const c=1.5;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2);};
      const kT=q('.half.k.top'), kB=q('.half.k.bottom'), yT=q('.half.y.top'), yB=q('.half.y.bottom');
      const c1=q('.c1'), c2=q('.c2'), morph=q('.morph'), eggLine=q('.egg-line');
      const fills=[q('.egg-glow'),q('.egg-back'),q('.egg-shell'),q('.egg-shade'),q('.egg-hi')];
      const plate=q('.plate'), letters=qa('.letter'), chick=q('.chick'), rule=q('.rule'), cta=q('.cta');
      const wordEls=qa('.word .inner'), brandEl=q('.brand');
      const dpath=(p,f)=>{ // polyline drawn from the centre outwards up to fraction f
        const n=p.length-1, mid=n/2, reach=f*mid, keep=p.filter((_,i)=>Math.abs(i-mid)<=reach+1e-6);
        const a=Math.floor(mid-reach), b=Math.ceil(mid+reach); const lerp=(i,j,t)=>[p[i][0]+(p[j][0]-p[i][0])*t,p[i][1]+(p[j][1]-p[i][1])*t];
        const pts=[]; if(f<=0)return'';
        const L=mid-reach, R=mid+reach;
        pts.push(lerp(Math.floor(L),Math.min(n,Math.floor(L)+1),L-Math.floor(L)));
        for(let i=Math.ceil(L);i<=Math.floor(R);i++)pts.push(p[i]);
        pts.push(lerp(Math.max(0,Math.ceil(R)-1),Math.ceil(R),1-(Math.ceil(R)-R)));
        return'M'+pts.map(v=>v[0].toFixed(1)+','+v[1].toFixed(1)).join('L');
      };
      const domeLen=eggLine.getTotalLength(); eggLine.style.strokeDasharray=domeLen+' '+domeLen;
      return frame=>{
        // 1. white crack across black, then the black splits along it
        const cr=frame-data.crack, sp=frame-data.split;
        c1.setAttribute('d',cr<0||sp>2?'':dpath(data.full,out(cr/7)));
        const s=io(sp/14);
        kT.style.transform='translateY('+(-1100*s)+'px)'; kB.style.transform='translateY('+(1100*s)+'px)';
        // 2. words land in the opening, one at a time
        wordEls.forEach((w,i)=>{const a=frame-data.words[i], next=i+1<data.words.length?data.words[i+1]:data.build;
          const inn=out(a/9), leave=io((frame-next)/8);
          w.style.transform='translateY('+(a<0?240:240*(1-inn)-240*leave)+'px)';
          w.parentElement.style.display=a<0||frame>next+8?'none':'block';});
        // 3. a navy crack across yellow, which splits too and keeps the line
        const b=frame-data.build;
        const sb=io((b-8)/14);
        yT.style.transform='translateY('+(-1100*sb)+'px)'; yB.style.transform='translateY('+(1100*sb)+'px)';
        // the crack line morphs from full width into the shell's jagged edge
        const m=io((b-14)/16);
        const line=data.full.map((p,i)=>[p[0]+(data.egg[i][0]-p[0])*m,p[1]+(data.egg[i][1]-p[1])*m]);
        c2.setAttribute('d',b<0||b>=8?'':dpath(data.full,out(b/7)));
        morph.setAttribute('d',b<8?'':'M'+line.map(v=>v[0].toFixed(1)+','+v[1].toFixed(1)).join('L'));
        // 4. the dome draws up from the edge, then the shell fills
        const d=io((b-28)/14);
        eggLine.style.strokeDashoffset=String(domeLen*(1-d)); eggLine.style.opacity=b<28?'0':'1';
        const f=out((b-40)/8); fills.forEach(el=>el.style.opacity=String(f));
        // 5. wordmark
        const l=frame-data.logo;
        plate.style.transform='scaleY('+(l<0?0:back(l/10))+')'; plate.style.opacity=l<0?'0':'1';
        letters.forEach((el,i)=>{const n=letters.length, c=(n-1)/2, t=l-4-i*1.5;
          const y=-1.6*(c*c-(i-c)*(i-c)), r=(i-c)*1.3;
          el.style.transform='translateY('+(y+40*(1-out(t/8)))+'px) rotate('+r+'deg) scale('+(t<0?0:back(t/8))+')';});
        chick.style.opacity=String(clamp((l-18)/8)); chick.style.transform='translateY('+(18*(1-out((l-18)/10)))+'px)';
        // 6. call to action
        const k=frame-data.cta;
        rule.style.width=(k<0?0:120*out(k/12))+'px';
        cta.style.opacity=String(clamp((k-6)/10)); cta.style.letterSpacing=(k<6?22:8+14*(1-out((k-6)/16)))+'px';
        // slow push-in on the finished logo
        brandEl.style.transform='scale('+(1+0.04*clamp((frame-data.build)/(data.end-data.build)))+')';
      };`,
  });
  return sealVisualTrack({ id: options.id, timelineId: timeline.id, visualIr: "hypit.visual-ir@1",
    presents: [{ id: options.id, order: 0, z: 0, span: window.span,
      elements: [{ id: "short", kind: "program", order: 0, program,
        style: [{ name: "position", value: "absolute" }, { name: "left", value: `${within.xPx}px` },
          { name: "top", value: `${within.yPx}px` },
          { name: "width", value: `${within.widthPx}px` }, { name: "height", value: `${within.heightPx}px` }] }, ...children] }] });
}
