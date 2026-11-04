import json,subprocess
P=json.load(open('plan01.json')); D=P['dur']; B0=P['beat0']; BL=P['beatlen']
en='+'.join(f"between(t,{g:.3f},{g+0.1:.3f})" for g in P['glitch'])
fl='+'.join(f"between(t,{g:.3f},{g+0.05:.3f})" for g in P['glitch'])
tot='%d\\:%02d'%(int(D)//60,int(D)%60)
fc=(f"[0:v]eq=contrast=1.06:saturation=1.12:brightness=-0.07,"
 f"colorbalance=rs=0.04:bs=0.07:rh=0.03,"
 f"rgbashift=rh=30:bh=-30:gv=8:enable='{en}',noise=alls=60:allf=t:enable='{en}',"
 f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.22:t=fill:enable='{fl}'[bg];"
 f"[bg][1:v]overlay=0:0[b0];"
 f"[2:a]showwaves=s=966x236:rate=30:mode=cline:colors=0x00E5FF:scale=sqrt:draw=full,format=rgba,split[w1][w2];[w2]gblur=sigma=6[wg];[wg][w1]overlay[wv];"
 f"[b0][wv]overlay=842:472[b1];"
 f"color=c=0xFF2BB4:s=970x12:r=30[pb];color=c=black@0.0:s=970x12:r=30,format=rgba[pt];[pt][pb]overlay=x='-970+970*t/{D}':eval=frame[bar];"
 f"[b1][bar]overlay=840:764:shortest=1[b2];"
 f"[b2]drawtext=fontfile=STM.ttf:fontsize=28:fontcolor=0xC8D2E6:x=840:y=790:text='%{{eif\\:floor(t/60)\\:d}}\\:%{{eif\\:mod(floor(t),60)\\:d\\:2}} / {tot}',format=yuv420p[o]")
cmd=['ffmpeg','-v','error','-y','-i','bg01.mp4','-loop','1','-framerate','30','-i','ov01.png','-i','../20blok/source/albums/dystopique/01-cyphergrid-collapse.mp3',
 '-filter_complex',fc,'-map','[o]','-map','2:a','-t',str(D),'-c:v','libx264','-preset','medium','-crf','19','-r','30','-c:a','aac','-b:a','256k','-movflags','+faststart','v2-01-calm.mp4']
subprocess.run(cmd,check=True); print('done')
