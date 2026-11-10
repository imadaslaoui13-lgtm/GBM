# Sound design for the "De barst" short (10 s). Times match calimeros-short.svml.
import numpy as np, wave, sys
SR=48000; DUR=10.0; N=int(SR*DUR); out=np.zeros((N,2)); rng=np.random.default_rng(5)
def add(sig,t,g=1.0,pan=0.0):
    i=int(t*SR); j=min(N,i+len(sig)); s=sig[:j-i]*g
    out[i:j,0]+=s*(1-max(0,pan)); out[i:j,1]+=s*(1+min(0,pan))
def env(n,a,d): t=np.arange(n)/SR; return np.minimum(1,t/a)*np.exp(-t/d)
def onepole(x,k):
    y=np.empty_like(x); a=0.0
    for i,v in enumerate(x): a+=k*(v-a); y[i]=a
    return y
def crack(l,density):
    n=int(l*SR); x=np.zeros(n)
    for _ in range(density):
        p=int(rng.random()**1.5*n*.85); w=int(rng.integers(6,100)); seg=rng.standard_normal(w)*np.hanning(w)
        x[p:p+w]+=seg[:len(x[p:p+w])]*(1-p/n)
    return np.diff(np.concatenate([[0],x]))*.9
def whoosh(l): n=int(l*SR); t=np.linspace(0,1,n); return onepole(rng.standard_normal(n),.06)*np.sin(np.pi*t)**2*2.4
def thump(f=52,d=.35): n=int(1.2*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*(f+45*np.exp(-t*18))*t)*env(n,.002,d)
def click(): n=int(.05*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*2400*t)*env(n,.0005,.006)*.6+np.sin(2*np.pi*90*t)*env(n,.001,.03)
def tick(f): n=int(.08*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*f*t)*env(n,.001,.02)*.25
def tone(fs,l,a=.02,d=1.2):
    n=int(l*SR); t=np.arange(n)/SR; x=sum(np.sin(2*np.pi*f*t)+.4*np.sin(2*np.pi*f*2.0*t)*np.exp(-t*4) for f in fs)
    return x*np.minimum(1,t/a)*np.exp(-t/d)*.12
def riser(l):
    n=int(l*SR); t=np.arange(n)/SR; f=220+660*(t/l)**2
    return np.sin(2*np.pi*np.cumsum(f)/SR)*(t/l)**2*.07
# minimal pulse under the words (100 BPM, soft)
for k in range(7): add(thump(48,.25),0.9+k*0.6,g=.35)
add(crack(.25,60),0.3,g=1.2)
add(whoosh(.45),0.6,g=.8); add(thump(),0.9,g=1.0)
for t in (0.9,2.2,3.5): add(click(),t+.05,g=.9)
add(crack(.3,70),4.8,g=1.1); add(whoosh(.5),4.85,g=.7); add(thump(60,.5),5.07,g=.8)
add(riser(1.0),5.2)
add(tone([523.3,659.3,784],2.5),6.1,g=.9)
for i in range(10): add(tick(1200+i*60),6.43+i*0.05,g=1.0,pan=(i-4.5)/9)
add(tone([261.6,392,523.3,659.3],4.0,.05,1.8),7.5,g=1.0); add(thump(44,.8),7.5,g=.7)
fade=int(1.2*SR); out[-fade:]*=np.linspace(1,0,fade)[:,None]
out/=np.max(np.abs(out)); out=np.tanh(out*4.0)/np.tanh(4.0)*.9
w=wave.open(sys.argv[1],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out*32767).astype('<i2').tobytes()); w.close()
