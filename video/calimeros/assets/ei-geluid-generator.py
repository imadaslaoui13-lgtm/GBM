# Minimal sound design for the egg reveal reel (9 s). Times match calimeros-ei.svml.
import numpy as np, wave, sys
SR=48000; DUR=9.0; N=int(SR*DUR); out=np.zeros((N,2)); rng=np.random.default_rng(11)
def add(sig,t,g=1.0,pan=0.0):
    i=int(t*SR); j=min(N,i+len(sig)); s=sig[:j-i]*g
    out[i:j,0]+=s*(1-max(0,pan)); out[i:j,1]+=s*(1+min(0,pan))
def env(n,a,d): t=np.arange(n)/SR; return np.minimum(1,t/a)*np.exp(-t/d)
def onepole(x,k):
    y=np.empty_like(x); a=0.0
    for i,v in enumerate(x): a+=k*(v-a); y[i]=a
    return y
def knock(): n=int(.12*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*(180+120*np.exp(-t*60))*t)*env(n,.001,.025)*.5
def crack(l=.22,density=40):
    n=int(l*SR); x=np.zeros(n)
    for _ in range(density):
        p=int(rng.random()**1.4*n*.85); w=int(rng.integers(8,120)); seg=rng.standard_normal(w)*np.hanning(w)
        x[p:p+w]+=seg[:len(x[p:p+w])]*(1-p/n)
    return np.diff(np.concatenate([[0],x]))*.8
def whoosh(l=.6):
    n=int(l*SR); x=rng.standard_normal(n); t=np.linspace(0,1,n)
    return onepole(x,.05)*np.sin(np.pi*t)**2*2.2
def boom(): n=int(1.4*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*(55+40*np.exp(-t*8))*t)*env(n,.005,.45)*.7
def bell(f,l=2.5):
    n=int(l*SR); t=np.arange(n)/SR
    return (np.sin(2*np.pi*f*t+.8*np.sin(2*np.pi*f*3.01*t)*np.exp(-t*3))+.25*np.sin(2*np.pi*f*2*t))*env(n,.003,.9)*.18
def pad(freqs,l,a=1.5):
    n=int(l*SR); t=np.arange(n)/SR; x=sum(np.sin(2*np.pi*f*t)+.5*np.sin(2*np.pi*f*1.003*t) for f in freqs)
    e=np.minimum(1,t/a)*np.minimum(1,(l-t)/1.2); return x*e*.035
add(pad([110,164.8,220],4.2,2.5),0.0)                 # quiet tension
add(pad([130.8,196,261.6,329.6],5.2,.4),3.9,g=1.3)      # warm resolve on the reveal
for t in (0.4,1.8,3.0): add(knock(),t+.05,g=.8)
add(crack(.18,25),1.0,g=.9); add(crack(.25,45),2.2,g=1.0); add(crack(.35,70),3.3,g=1.1)
add(whoosh(.55),3.55,g=.7); add(crack(.5,140),4.0,g=1.2); add(boom(),4.0,g=.9)
for f,dt in ((523.3,0),(659.3,.12),(784,.24),(1046.5,.42)): add(bell(f),4.15+dt,g=.9,pan=(dt-.2))
add(bell(784,2.0),5.4,g=.5)
fade=int(1.0*SR); out[-fade:]*=np.linspace(1,0,fade)[:,None]
out/=np.max(np.abs(out)); out=np.tanh(out*4.5)/np.tanh(4.5)*.9
w=wave.open(sys.argv[1],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out*32767).astype('<i2').tobytes()); w.close()
