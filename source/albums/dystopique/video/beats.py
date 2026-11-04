import numpy as np,librosa,json
f='../20blok/source/albums/dystopique/01-cyphergrid-collapse.mp3'
y,sr=librosa.load(f,sr=22050); dur=len(y)/sr
oenv=librosa.onset.onset_strength(y=y,sr=sr)
tempo,beats=librosa.beat.beat_track(onset_envelope=oenv,sr=sr,tightness=400)
bt=librosa.frames_to_time(beats,sr=sr)
# low-band kick strength per beat to find downbeat phase
S=np.abs(librosa.stft(y)); low=S[:12].sum(0); lt=librosa.frames_to_time(np.arange(len(low)),sr=sr)
k=np.interp(bt,lt,low)
ph=int(np.argmax([k[p::4].mean() for p in range(4)]))
bars=bt[ph::4]
rms=librosa.feature.rms(y=y)[0]; rt=librosa.frames_to_time(np.arange(len(rms)),sr=sr)
def e(a,b): m=(rt>=a)&(rt<b); return float(rms[m].mean()) if m.any() else 0
be=[e(bars[i],bars[i+1]) for i in range(len(bars)-1)]
print('dur',round(dur,2),'beatlen',round(float(np.median(np.diff(bt))),4),'phase',ph,'first beat',round(bt[0],3),'nbars',len(bars))
for i,b in enumerate(bars[:-1]): print(i,round(b,2),round(be[i],3))
json.dump({'dur':dur,'beats':bt.tolist(),'bars':bars.tolist(),'barE':be},open('beats01.json','w'))
