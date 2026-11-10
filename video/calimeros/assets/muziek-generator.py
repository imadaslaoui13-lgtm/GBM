import numpy as np, wave, sys
SR=48000; DUR=16.0; N=int(SR*DUR); out=np.zeros((N,2))
BPM=120; B=60/BPM
rng=np.random.default_rng(3)
def add(sig,t,pan=0.0,g=1.0):
    i=int(t*SR); j=min(N,i+len(sig))
    if i>=N: return
    s=sig[:j-i]*g
    out[i:j,0]+=s*(1-max(0,pan)); out[i:j,1]+=s*(1+min(0,pan))
def env(n,a=0.002,d=0.2):
    t=np.arange(n)/SR; return np.minimum(1,t/a)*np.exp(-t/d)
def kick():
    n=int(.35*SR); t=np.arange(n)/SR; f=50+120*np.exp(-t*30)
    return np.sin(2*np.pi*np.cumsum(f)/SR)*env(n,.001,.12)*1.0
def clap():
    n=int(.2*SR); x=rng.standard_normal(n); x=np.convolve(x,[1,-.9],'same')
    e=env(n,.001,.05); e[:int(.01*SR)]*=1.3; return x*e*.35
def hat(open_=False):
    n=int((.15 if open_ else .05)*SR); x=rng.standard_normal(n); x=np.diff(np.concatenate([[0],x]))
    return x*env(n,.0005,.04 if open_ else .012)*.18
def note(m): return 440*2**((m-69)/12)
def bass(m,l):
    n=int(l*SR); t=np.arange(n)/SR; f=note(m)
    x=np.sign(np.sin(2*np.pi*f*t))*.35+np.sin(2*np.pi*f*t)*.65
    return np.tanh(x*1.5)*env(n,.003,l*0.6)*.32
def stab(ms,l=.18):
    n=int(l*SR); t=np.arange(n)/SR; x=sum(2*((f*t)%1)-1 for f in [note(m)*d for m in ms for d in (1,1.004)])
    x=np.convolve(x,np.ones(12)/12,'same'); return x*env(n,.002,.08)*.07
def bell(m,l=.6):
    n=int(l*SR); t=np.arange(n)/SR; f=note(m)
    x=np.sin(2*np.pi*f*t+1.5*np.sin(2*np.pi*f*2*t)*np.exp(-t*6))+.3*np.sin(2*np.pi*f*3*t)*np.exp(-t*8)
    return x*env(n,.002,l*.5)*.22
def crunch(l=.45):
    n=int(l*SR); x=np.zeros(n)
    for _ in range(140):
        p=int(rng.random()**1.6*n*.9); w=int(rng.integers(20,400)); seg=rng.standard_normal(w)*np.hanning(w)
        x[p:p+w]+=seg[:len(x[p:p+w])]*(1-p/n)
    x=np.diff(np.concatenate([[0],x])); return np.tanh(x*1.2)*.55
def whoosh(l=.35):
    n=int(l*SR); x=rng.standard_normal(n); t=np.linspace(0,1,n)
    y=np.zeros(n); a=0
    for i in range(n):
        k=.02+.25*t[i]**2; a+=k*(x[i]-a); y[i]=a
    return y*np.sin(np.pi*t)**2*.5
prog=[(48,[60,64,67]),(45,[60,64,69]),(41,[60,65,69]),(43,[59,62,67])]
bars=int(DUR/(4*B))
for bar in range(bars):
    t0=bar*4*B; root,ch=prog[bar%4]
    for b in range(4):
        tb=t0+b*B
        add(kick(),tb)
        if b in (1,3): add(clap(),tb,g=1.0)
        add(hat(),tb+B/2,pan=.3); add(hat(),tb,pan=-.3,g=.6)
        if b==3 and bar%2: add(hat(True),tb+B/2,pan=.3)
        add(bass(root if b%2==0 else root+12,B/2*.95),tb); add(bass(root+7 if b==3 else root,B/2*.9),tb+B/2)
        add(stab(ch),tb+B/2,pan=.2)
# jingle on end card (12.0s): original 5-note motif
for k,(m,dt,l) in enumerate([(72,0,.3),(76,.25,.3),(79,.5,.3),(76,.75,.3),(84,1.0,1.4)]):
    add(bell(m,l*1.6),12.0+dt,g=1.1); add(bell(m-12,l*1.6),12.0+dt,g=.5)
for k,(m,dt) in enumerate([(84,2.0),(79,2.25),(84,2.5)]):
    add(bell(m,.5),12.0+dt,g=.8)
add(crunch(),0.2,g=1.3); add(crunch(.3),2.07,g=.9)
for t in (2.0,4.0,6.0,10.0,12.0): add(whoosh(),t-.3,g=.9)
fade=int(.8*SR); out[-fade:]*=np.linspace(1,0,fade)[:,None]
out/=np.max(np.abs(out)); out=np.tanh(out*3.2)/np.tanh(3.2)*0.93
pcm=(out*32767).astype('<i2')
w=wave.open(sys.argv[1],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('ok')
