import json
B=json.load(open('beats01.json')); b=B['bars']; D=B['dur']
# (start, kind, src, extra)  kind: L=loop, I=image(pan dir)
cuts=[(0,'L6',0),(b[0],'I4','r'),(b[4],'I6','l'),(b[8],'I5','u'),(b[12],'L1',0),
 (b[14],'L2',0),(b[16],'I7','r'),(b[18],'L3',0),(b[20],'I1','l'),
 (b[22],'L4',0),
 (b[26],'L5',0),(b[28],'I3','u'),(b[30],'L3',2.5),
 (b[32],'I2','r'),
 (b[34],'L5',2.5),(b[36],'I7','l'),(b[38],'L1',2.5),
 (b[40],'L6',3)]
glitch=[b[0],b[14],b[22],b[26],b[32],b[34],b[40]]
segs=[]
for i,(t,s,x) in enumerate(cuts):
    e=cuts[i+1][0] if i+1<len(cuts) else D
    f0=round(t*30); f1=round(e*30); segs.append(dict(src=s,x=x,frames=f1-f0,t=t))
json.dump(dict(segs=segs,glitch=glitch,beat0=B['beats'][0],beatlen=0.4876,dur=D),open('plan01.json','w'),indent=0)
print(len(segs),sum(s['frames'] for s in segs)/30)
