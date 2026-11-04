#!/bin/bash
# render one silent video segment for track N (1-14)
N=$(printf %02d $1); cd "$(dirname "$0")"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 wav/t$N.wav)
TOT=$(python3 -c "d=$DUR;print('%d\\\\:%02d'%(int(d)//60,int(d)%60))")
ffmpeg -v error -y -loop 1 -framerate 30 -i layer$N.png -i wav/t$N.wav -loop 1 -framerate 30 -i scan.png \
 -f lavfi -i "color=c=0xFF2BB4:s=970x12:r=30" -f lavfi -i "color=c=black@0.0:s=970x12:r=30,format=rgba" \
 -filter_complex "[1:a]showwaves=s=966x236:rate=30:mode=cline:colors=0x00E5FF:scale=sqrt:draw=full,format=rgba[w];[w]split[w1][w2];[w2]gblur=sigma=6[wg];[wg][w1]overlay[v];[0][v]overlay=842:472:shortest=1[b];[4][3]overlay=x='-970+970*t/$DUR':eval=frame[bar];[b][bar]overlay=840:764[b2];[b2]drawtext=fontfile=STM.ttf:fontsize=28:fontcolor=0xC8D2E6:x=840:y=790:text='%{eif\:floor(t/60)\:d}\:%{eif\:mod(floor(t),60)\:d\:2} / $TOT'[c];[c][2]overlay=0:0:shortest=1,format=yuv420p[o]" \
 -map "[o]" -t $DUR -an -c:v libx264 -preset veryfast -crf 20 -r 30 seg$N.mp4 && echo done $N
