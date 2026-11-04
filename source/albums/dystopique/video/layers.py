import json, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
A='/home/claude/20blok/source/albums/dystopique/'
AL=json.load(open(A+'album.json'))
W,H=1920,1080
CY=(0,229,255); PK=(255,43,180)
STM=lambda s: ImageFont.truetype('STM.ttf',s); ORB=lambda s: ImageFont.truetype('ORB7.ttf',s)
def fit(d,txt,font_fn,size,maxw):
    while size>30 and d.textlength(txt,font=font_fn(size))>maxw: size-=4
    return font_fn(size)
def layer(i):
    t=AL['tracks'][i]; art=Image.open(A+t['art']).convert('RGB')
    bg=art.resize((W,W)).crop((0,(W-H)//2,W,(W-H)//2+H)).filter(ImageFilter.GaussianBlur(40))
    bg=ImageEnhance.Brightness(bg).enhance(0.35)
    im=bg.copy(); d=ImageDraw.Draw(im,'RGBA')
    # art panel with neon glow
    S=600; x0,y0=150,(H-S)//2-30
    glow=Image.new('RGBA',(W,H),(0,0,0,0)); g=ImageDraw.Draw(glow)
    g.rectangle([x0-14,y0-14,x0+S+14,y0+S+14],outline=PK+(255,),width=10)
    glow=glow.filter(ImageFilter.GaussianBlur(18)); im.paste(glow,(0,0),glow); d=ImageDraw.Draw(im,'RGBA')
    im.paste(art.resize((S,S),Image.LANCZOS),(x0,y0))
    d.rectangle([x0-3,y0-3,x0+S+2,y0+S+2],outline=PK,width=3)
    X=840
    d.text((X,y0-4),'SCIPHER PUNX  //  DYSTOPIQUE',font=STM(34),fill=CY)
    d.text((X,y0+46),'TRACK %02d / %02d' % (t['n'],len(AL['tracks'])),font=STM(30),fill=(200,210,230))
    f=fit(d,t['title'].upper(),ORB,64,W-X-110)
    d.text((X,y0+100),t['title'].upper(),font=f,fill=(255,255,255))
    d.text((X,y0+190),'PRESENTED BY THE AMERICAN',font=STM(26),fill=PK)
    # visualizer frame + progress track
    d.rectangle([X,y0+260,W-110,y0+500],outline=CY+(90,),width=2)
    d.line([X,y0+560,W-110,y0+560],fill=(255,255,255,70),width=6)
    d.text((X,H-70),'YEAR 2113  ·  SIGNAL ACQUIRED',font=STM(24),fill=(150,160,180))
    return im
if __name__=='__main__':
    i=int(sys.argv[1]); layer(i).save('layer%02d.png'%(i+1))
    # scanlines
    sl=Image.new('RGBA',(W,H),(0,0,0,0)); s=ImageDraw.Draw(sl)
    for y in range(0,H,3): s.line([0,y,W,y],fill=(0,0,0,60))
    sl.save('scan.png')
