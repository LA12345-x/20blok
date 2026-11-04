import json,subprocess,sys
P=json.load(open('plan01.json'))
LD={'L1':5.208,'L2':5.208,'L3':5.208,'L4':5.208,'L5':5.208,'L6':9.04}
def run(i,s):
    n=s['frames']; d=n/30; out='seg/s%02d.mp4'%i
    if s['src'][0]=='L':
        ld=LD[s['src']]*2; sp=min(max(d/ld,1.0),1.6)
        crop='crop=iw:ih*0.9:0:ih*0.1,' if s['src']=='L3' else ''
        vf=f"{crop}split[a][b];[b]reverse[r];[a][r]concat,setpts={sp}*PTS,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=30"
        cmd=['ffmpeg','-v','error','-y','-ss',str(s['x']),'-i','src/%s.mp4'%s['src'],'-filter_complex',vf+',loop=loop=-1:size=32767','-frames:v',str(n),'-an','-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',out]
    else:
        W,H=2208,1242; mx,my=W-1920,H-1080
        dr=s['x']; p=f"(n/{max(n-1,1)})"
        x={'r':f"{mx}*{p}",'l':f"{mx}*(1-{p})",'u':f"{mx}/2"}[dr]
        y={'r':f"{my}/2",'l':f"{my}/2",'u':f"{my}*(1-{p})"}[dr]
        vf=f"scale={W}:{H}:flags=lanczos,crop=1920:1080:'{x}':'{y}'"
        cmd=['ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i','src/%s.png'%s['src'],'-vf',vf,'-frames:v',str(n),'-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',out]
    subprocess.run(cmd,check=True)
import os; os.makedirs('seg',exist_ok=True)
with open('seg/list.txt','w') as f:
    for i,s in enumerate(P['segs']): run(i,s); f.write("file 's%02d.mp4'\n"%i)
print('ok')
