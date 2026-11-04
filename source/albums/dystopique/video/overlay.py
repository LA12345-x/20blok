import json,sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
A='../20blok/source/albums/dystopique/'
AL=json.load(open(A+'album.json'))
W,H=1920,1080; CY=(0,229,255); PK=(255,43,180)
STM=lambda s: ImageFont.truetype('STM.ttf',s); ORB=lambda s: ImageFont.truetype('ORB7.ttf',s)
def fit(d,txt,ff,size,maxw):
    while size>30 and d.textlength(txt,font=ff(size))>maxw: size-=4
    return ff(size)
i=int(sys.argv[1]); t=AL['tracks'][i]; art=Image.open(A+t['art']).convert('RGB')
im=Image.new('RGBA',(W,H),(0,0,0,0))
# vignette
v=Image.new('L',(W,H),0); vd=ImageDraw.Draw(v)
for k in range(60): 
    a=int(150*(1-k/60)**2); vd.rectangle([k*6,k*4,W-k*6,H-k*4],outline=a,width=7)
v=v.filter(ImageFilter.GaussianBlur(40)); im.paste((0,0,0,255),(0,0),v)
S=600; x0,y0=150,(H-S)//2-30; X=840
# glass panel behind text + waveform
pn=Image.new('RGBA',(W,H),(0,0,0,0)); pd=ImageDraw.Draw(pn)
pd.rounded_rectangle([X-40,y0-40,W-70,y0+S+30],radius=18,fill=(8,4,18,150))
im=Image.alpha_composite(im,pn)
# art glow + art
g=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(g)
gd.rectangle([x0-14,y0-14,x0+S+14,y0+S+14],outline=PK+(255,),width=10)
g=g.filter(ImageFilter.GaussianBlur(18)); im=Image.alpha_composite(im,g)
im.paste(art.resize((S,S),Image.LANCZOS),(x0,y0))
d=ImageDraw.Draw(im)
d.rectangle([x0-3,y0-3,x0+S+2,y0+S+2],outline=PK,width=3)
d.text((X,y0-4),'SCIPHER PUNX  //  DYSTOPIQUE',font=STM(34),fill=CY)
d.text((X,y0+46),'TRACK %02d / %02d'%(t['n'],len(AL['tracks'])),font=STM(30),fill=(200,210,230))
f=fit(d,t['title'].upper(),ORB,64,W-X-110)
d.text((X,y0+100),t['title'].upper(),font=f,fill=(255,255,255))
d.text((X,y0+190),'PRESENTED BY THE AMERICAN.ID',font=STM(26),fill=PK)
d.rectangle([X,y0+260,W-110,y0+500],outline=CY+(90,),width=2)
d.line([X,y0+560,W-110,y0+560],fill=(255,255,255,70),width=6)
d.text((X,H-70),'YEAR 2113  //  SIGNAL ACQUIRED',font=STM(24),fill=(170,180,200))
sl=Image.new('RGBA',(W,H),(0,0,0,0)); sd=ImageDraw.Draw(sl)
for y in range(0,H,3): sd.line([0,y,W,y],fill=(0,0,0,50))
im=Image.alpha_composite(im,sl)
im.save('ov%02d.png'%(i+1))
