# still photo -> barely-moving clip with grain + a light texture (cctv | vhs | grain)
import sys,subprocess,numpy as np,time
from PIL import Image,ImageDraw,ImageFont
src,out,n,fx=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
im=Image.open(src).convert('RGB'); W,H=1920,1080; iw,ih=im.size; base=max(W/iw,H/ih)
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',out],stdin=subprocess.PIPE)
rng=np.random.default_rng(1); F=ImageFont.truetype('STM.ttf',30)
for f in range(n):
    u=f/max(n-1,1); s=base*(1.04+0.03*u); vw,vh=W/s,H/s
    fr=im.transform((W,H),Image.AFFINE,(1/s,0,iw/2-vw/2,0,1/s,ih/2-vh/2),resample=Image.BICUBIC)
    a=np.asarray(fr).astype(np.float32)
    if fx=='cctv':
        g=a.mean(2,keepdims=True); a=a*0.55+g*0.45; a*=np.array([0.95,1.03,0.98])
        y=int((f*6)%(H+200))-100; a[max(y,0):max(min(y+80,H),0)]*=1.12
    if fx=='vhs':
        a[:,:,0]=np.roll(a[:,:,0],5,1); a[:,:,2]=np.roll(a[:,:,2],-5,1)
        if f%47<2: r=rng.integers(0,H-30); a[r:r+30]=np.roll(a[r:r+30],18,1)
    a+=rng.normal(0,11,(H,W,1)).astype(np.float32)
    fr=Image.fromarray(np.clip(a,0,255).astype(np.uint8))
    if fx=='cctv':
        d=ImageDraw.Draw(fr)
        if (f//15)%2==0: d.ellipse([60,60,82,82],fill=(230,40,40))
        d.text((96,56),'REC',font=F,fill=(235,235,235))
        sec=f//30; d.text((60,H-90),'CAM 04   2113-11-04  03:%02d:%02d'%(17+sec//60,sec%60),font=F,fill=(235,235,235))
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait()
