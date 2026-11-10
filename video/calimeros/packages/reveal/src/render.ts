import { sealVisualTrack } from "@hypit/composition";
import type { VisualElement } from "@hypit/composition";
import { htmlVisual } from "@hypit/html-program";
import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import { assertTemporalWindowFor } from "@hypit/temporal";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
import { logoDataUri } from "./logo-data.js";

export const beatKinds = ["wobble", "crack", "open", "tagline"] as const;
export type BeatKind = typeof beatKinds[number];
export type Beat = { id: string; kind: BeatKind; text: string; sub: string; at: TemporalInstant };
export type RevealOptions = { id: string; cta: string };

/* Egg box in stage units (1080 x 1920). The crack line is a zigzag across it. */
const EGG = { left: 290, top: 590, width: 500, height: 660 };
const ZIG: Array<[number, number]> = [[-2, 47], [9, 43], [17, 50], [27, 42], [36, 49], [46, 41], [55, 49], [64, 42], [73, 50], [82, 43], [91, 49], [102, 44]];
const zigPct = (pts: Array<[number, number]>) => pts.map(([x, y]) => `${x}% ${y}%`).join(",");
const TOP_CLIP = `polygon(-2% -2%,102% -2%,${zigPct([...ZIG].reverse())})`;
const BOTTOM_CLIP = `polygon(${zigPct(ZIG)},102% 102%,-2% 102%)`;
const crackPoints = (from: number, step: number) => {
  const out: string[] = [];
  for (let i = from; i >= 0 && i < ZIG.length; i += step) { const [x, y] = ZIG[i]!; out.push(`${(x / 100 * EGG.width).toFixed(1)},${(y / 100 * EGG.height).toFixed(1)}`); }
  return `M${out.join("L")}`;
};
const CENTER = 6; // crack starts here and runs to both sides
const shards = Array.from({ length: 9 }, (_, i) => `<i class="shard" data-i="${i}"></i>`).join("");

/** One scene: the egg's wobbles and cracks build tension, the opening hands over to the logo. */
export function renderReveal(timeline: Timeline, within: SpatialFrame, window: TemporalWindow,
  font: FontStackRef, headline: FontStackRef, beats: readonly Beat[], options: RevealOptions) {
  assertTemporalWindowFor(window, { subjectId: options.id, timeline });
  const start = window.span.startFrame, local = (beat: Beat) => beat.at.frame - start;
  const of = (kind: BeatKind) => beats.filter(beat => beat.kind === kind);
  const open = of("open")[0], tagline = of("tagline")[0];
  if (!open || !tagline) throw new Error("Reveal needs one open and one tagline event.");
  let order = 0;
  const text = (id: string, value: string, size: number, color: string, face: FontStackRef): VisualElement => ({
    id, kind: "text", parent: "reveal", order: ++order, text: value, fonts: face.faces,
    style: [{ name: "font-size", value: `${size}px` }, { name: "line-height", value: 1.1 }, { name: "color", value: color }],
  });
  const children: VisualElement[] = [text("tagline", tagline.text, 46, "#2E2219", headline)];
  if (options.cta) children.push(text("cta", options.cta, 34, "#B8321A", font));
  const program = htmlVisual({
    html: `<div class="stage"><div class="bg"></div><div class="world">
      <div class="glow"></div><div class="shadow"></div>
      <div class="logo"><img src="${logoDataUri}" alt=""/></div>
      <div class="egg"><div class="half top"><div class="shell"></div></div><div class="half bottom"><div class="shell"></div><div class="inside"></div></div>
        <div class="crackbox"><svg viewBox="0 0 ${EGG.width} ${EGG.height}" width="${EGG.width}" height="${EGG.height}">
          <path class="crack l" d="${crackPoints(CENTER, -1)}"/><path class="crack r" d="${crackPoints(CENTER, 1)}"/>
          <path class="crack hair h1" d="M${ZIG[4]![0] / 100 * EGG.width} ${ZIG[4]![1] / 100 * EGG.height} l-18 -34 l10 -22"/>
          <path class="crack hair h2" d="M${ZIG[8]![0] / 100 * EGG.width} ${ZIG[8]![1] / 100 * EGG.height} l20 30 l-6 26"/>
        </svg></div></div>
      <div class="shards">${shards}</div>
      <div class="copy"><div class="tagline">{{tagline}}</div>${options.cta ? `<div class="rule"></div><div class="cta">{{cta}}</div>` : ""}</div>
    </div></div>`,
    css: `:scope{overflow:hidden;background:#F6F1E7}
      .stage{position:absolute;left:0;top:0;width:1080px;height:1920px;transform-origin:0 0;transform:scale(${within.widthPx / 1080})}
      .bg{position:absolute;inset:0;background:radial-gradient(ellipse 70% 55% at 50% 47%,#FFFDF8 0,#F6F1E7 60%,#E9E1D2 100%)}
      .world{position:absolute;inset:0;transform-origin:50% 48%}
      .glow{position:absolute;left:90px;top:470px;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,#FFF7DA 0,#FFE9A6aa 30%,#FFE9A600 68%);opacity:0}
      .shadow{position:absolute;left:${EGG.left + 50}px;top:${EGG.top + EGG.height - 30}px;width:${EGG.width - 100}px;height:60px;border-radius:50%;background:radial-gradient(ellipse,#3b2a1a55 0,#3b2a1a00 70%)}
      .egg{position:absolute;left:${EGG.left}px;top:${EGG.top}px;width:${EGG.width}px;height:${EGG.height}px;transform-origin:50% 100%}
      .half{position:absolute;inset:0}.top{clip-path:${TOP_CLIP};transform-origin:20% 45%}.bottom{clip-path:${BOTTOM_CLIP}}
      .shell,.inside,.crackbox{position:absolute;inset:0;border-radius:50% 50% 50% 50% / 62% 62% 38% 38%;overflow:hidden}
      .shell{background:radial-gradient(ellipse 60% 55% at 36% 30%,#FFFFFF 0,#FCF8F0 35%,#EEE5D5 72%,#D8CAB2 100%);box-shadow:inset -18px -26px 50px #c9b89c55}
      .inside{background:radial-gradient(ellipse 70% 30% at 50% 47%,#FFF3CF 0,#F7E7C0 40%,#00000000 72%);opacity:0}
      .crack{fill:none;stroke:#6B5640;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
      .hair{stroke-width:2.5;opacity:0}
      .shards{position:absolute;left:0;top:0}
      .shard{position:absolute;left:0;top:0;width:34px;height:28px;background:#F4EDE0;clip-path:polygon(0 30%,60% 0,100% 70%,30% 100%);box-shadow:inset -4px -4px 0 #d8cab2}
      .logo{position:absolute;left:150px;top:590px;width:780px;height:582px;opacity:0;transform-origin:50% 60%}
      .logo img{width:100%;height:100%;filter:drop-shadow(0 22px 28px #3b2a1a33)}
      .copy{position:absolute;left:60px;right:60px;top:1290px;text-align:center}
      .tagline{text-transform:uppercase;font-weight:800;opacity:0}
      .rule{width:0;height:3px;background:#B8321A;margin:34px auto 28px}
      .cta{opacity:0;letter-spacing:3px;text-transform:uppercase;font-weight:700}`,
    data: { wobbles: of("wobble").map(local), cracks: of("crack").map(local), open: local(open), tagline: local(tagline),
      end: window.span.endFrameExclusive - start, egg: EGG },
    setup: `const q=s=>root.querySelector(s), qa=s=>[...root.querySelectorAll(s)];
      const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)), ease=t=>1-Math.pow(1-clamp(t),3), easeIn=t=>Math.pow(clamp(t),2);
      const back=t=>{t=clamp(t);const c=1.6;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2);};
      const world=q('.world'), egg=q('.egg'), top=q('.top'), bottom=q('.bottom'), inside=q('.inside'), cbox=q('.crackbox');
      const L=q('.crack.l'), R=q('.crack.r'), hairs=qa('.hair'), glow=q('.glow'), shadow=q('.shadow'), logo=q('.logo');
      const tag=q('.tagline'), rule=q('.rule'), cta=q('.cta'), shardEls=qa('.shard');
      [L,R,...hairs].forEach(p=>{const n=p.getTotalLength();p.dataset.len=n;p.style.strokeDasharray=n+' '+n;});
      const draw=(p,f)=>{const n=+p.dataset.len;p.style.strokeDashoffset=String(n*(1-clamp(f)));};
      const stages=[0.28,0.62,1];
      const sh=Array.from({length:9},(_,i)=>({x:data.egg.left+data.egg.width*(0.1+0.8*i/8),y:data.egg.top+data.egg.height*0.46,
        vx:(i-4)*2.6+((i*7)%5-2),vy:-14-((i*11)%7)*1.6,r:(i*47)%360,vr:((i*29)%13-6)*2.5}));
      return frame=>{
        const o=frame-data.open;
        // slow camera push-in over the whole reel
        world.style.transform='scale('+(1+0.05*clamp(frame/data.end))+')';
        // wobble: damped swing on each wobble event, plus a jolt on each crack
        let rot=0;
        data.wobbles.forEach((w,i)=>{const a=frame-w;if(a>=0)rot+=(5+i*2)*Math.sin(a*0.75)*Math.exp(-a/8);});
        data.cracks.forEach(c=>{const a=frame-c;if(a>=0)rot+=2.2*Math.sin(a*1.6)*Math.exp(-a/4);});
        if(o<0&&o>-10){rot+=Math.sin(frame*2.3)*1.6*(1+o/10+1);}
        const lift=o>=0?0:0;
        egg.style.transform='rotate('+(o>=0?0:rot)+'deg) translateY('+lift+'px)';
        // crack grows in stages
        let f=0;data.cracks.forEach((c,i)=>{const a=frame-c;if(a>=0)f=Math.max(f,(i?stages[i-1]:0)+(stages[i]-(i?stages[i-1]:0))*ease(a/5));});
        draw(L,f);draw(R,f);hairs.forEach((h,i)=>{const c=data.cracks[1+i];const a=c===undefined?-1:frame-c;h.style.opacity=a>=0?'1':'0';draw(h,ease(a/6));});
        cbox.style.opacity=String(o<0?1:clamp(1-o/3));
        // opening
        if(o<0){top.style.transform='none';top.style.opacity='1';bottom.style.transform='none';bottom.style.opacity='1';inside.style.opacity='0';}
        else{
          const t=ease(o/16);
          top.style.transform='translate('+(160*t)+'px,'+(-420*t+260*easeIn(o/30))+'px) rotate('+(38*t)+'deg)';
          top.style.opacity=String(clamp(1-(o-8)/10));
          inside.style.opacity=String(clamp(o/3)*clamp(1-(o-6)/8));
          bottom.style.transform='translateY('+(320*easeIn(o/12))+'px) scale('+(1-0.1*ease(o/12))+')';
          bottom.style.opacity=String(clamp(1-(o-3)/6));
        }
        shadow.style.opacity=String(o<0?1:clamp(1-o/12));
        shadow.style.transform='scaleX('+(1-Math.abs(rot)*0.012)+')';
        shardEls.forEach((s,i)=>{const d=sh[i];if(o<0||o>36){s.style.opacity='0';return;}
          s.style.opacity=String(clamp(1-o/36));
          s.style.transform='translate('+(d.x+d.vx*o)+'px,'+(d.y+d.vy*o+0.75*o*o)+'px) rotate('+(d.r+d.vr*o)+'deg)';});
        glow.style.opacity=String(o<0?0:ease(o/10)*(0.85+0.15*Math.sin(frame*0.08)));
        glow.style.transform='scale('+(o<0?0.6:0.6+0.4*ease(o/14))+')';
        // logo rises out of the egg
        const g=o-2;
        logo.style.opacity=String(g<0?0:clamp(g/6));
        logo.style.transform=g<0?'scale(.3)':'translateY('+(90*(1-ease(g/18))+Math.sin((frame-data.open)*0.07)*6)+'px) scale('+(0.3+0.7*back(g/18))+')';
        // tagline and call to action
        const a=frame-data.tagline;
        tag.style.opacity=String(clamp(a/10));tag.style.letterSpacing=(a<0?22:10+12*(1-ease(a/18)))+'px';
        tag.style.transform='translateY('+(16*(1-ease(a/12)))+'px)';
        if(rule){rule.style.width=(a<10?0:160*ease((a-10)/12))+'px';}
        if(cta){cta.style.opacity=String(clamp((a-16)/10));}
      };`,
  });
  return sealVisualTrack({ id: options.id, timelineId: timeline.id, visualIr: "hypit.visual-ir@1",
    presents: [{ id: options.id, order: 0, z: 0, span: window.span,
      elements: [{ id: "reveal", kind: "program", order: 0, program,
        style: [{ name: "position", value: "absolute" }, { name: "left", value: `${within.xPx}px` },
          { name: "top", value: `${within.yPx}px` },
          { name: "width", value: `${within.widthPx}px` }, { name: "height", value: `${within.heightPx}px` }] }, ...children] }] });
}
