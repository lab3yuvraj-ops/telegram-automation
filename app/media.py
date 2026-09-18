import json, os, shutil, subprocess, wave, math, struct
from pathlib import Path
from .config import ROOT

def run(args, cwd=None):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
    if p.returncode: raise RuntimeError('Media processing failed: '+p.stderr[-2200:])
    return p.stdout

def ff(*args,cwd=None):
    # Limit decoder, filter and encoder threads on small hosting instances.
    values=list(map(str,args))
    return run([os.getenv('FFMPEG','ffmpeg'),'-hide_banner','-loglevel','error','-y','-threads','2','-filter_threads','2','-filter_complex_threads','2',*values[:-1],'-threads','2',values[-1]],cwd)
def probe(path):
    return json.loads(run([os.getenv('FFPROBE','ffprobe'),'-v','error','-show_format','-show_streams','-of','json',str(path)]))
def duration(path): return float(probe(path)['format']['duration'])
def available(): return bool(shutil.which(os.getenv('FFMPEG','ffmpeg')) and shutil.which(os.getenv('FFPROBE','ffprobe')))

def thumbnail(source,target,title):
    from PIL import Image,ImageDraw,ImageFont,ImageOps
    im=ImageOps.fit(Image.open(source).convert('RGB'),(1280,720)).convert('RGBA')
    overlay=Image.new('RGBA',im.size)
    draw=ImageDraw.Draw(overlay)
    for y in range(350,720):draw.line((0,y,1280,y),fill=(3,8,12,int(230*(y-350)/370)))
    im=Image.alpha_composite(im,overlay).convert('RGB');draw=ImageDraw.Draw(im)
    paths=['C:/Windows/Fonts/nirmala.ttf','C:/Windows/Fonts/Nirmala.ttc','/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
    fontpath=next((p for p in paths if Path(p).exists()),None)
    if not fontpath:raise RuntimeError('Install a Unicode font for thumbnail titles')
    for size in range(66,21,-2):
        font=ImageFont.truetype(fontpath,size)
        lines=['']
        for word in title.split():
            candidate=(lines[-1]+' '+word).strip()
            if draw.textbbox((0,0),candidate,font=font)[2]>1120 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        text='\n'.join(lines)
        box=draw.multiline_textbbox((0,0),text,font=font,spacing=8)
        if box[2]-box[0]<=1120 and box[3]-box[1]<=190:break
    draw.multiline_text((70,665-(box[3]-box[1])-box[1]),text,font=font,spacing=8,fill='#f1f0d7',stroke_width=2,stroke_fill='#0a1017')
    im.save(target)

def tone(path, seconds, kind='bed'):
    rate=24000
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        out=bytearray()
        for i in range(int(seconds*rate)):
            t=i/rate
            if kind=='bed': value=(math.sin(t*2*math.pi*55)+.3*math.sin(t*2*math.pi*58.2))*.07*(.7+.3*math.sin(t*.8))
            elif kind=='sting': value=.15*math.sin(2*math.pi*(420*t+40*t*t))*math.exp(-t*4)
            elif kind=='heartbeat': value=.13*math.sin(t*2*math.pi*65)*math.exp(-(t%1.2)*15)
            elif kind=='wind': value=.03*math.sin(t*2*math.pi*89)*math.sin(t*2*math.pi*93)
            else: value=0
            fade=min(1,t/.15,max(0,(seconds-t)/.3))
            out.extend(struct.pack('<h',int(32767*value*fade)))
        w.writeframes(out)

def fit_speech(source,target,seconds=7.5):
    length=duration(source)
    speed=max(1,length/(seconds-.18))
    if speed>1.5: raise RuntimeError(f'Speech is {length:.1f}s, too long for a {seconds}s scene. Shorten this line or regenerate speech; refusing to cut spoken words.')
    ff('-i',source,'-af',f'atempo={speed:.6f},apad,atrim=0:{seconds},loudnorm=I=-16:TP=-1.5:LRA=9','-ar','48000','-ac','2',target)

def make_demo_video(image, target):
    ff('-loop','1','-i',image,'-t','8','-r','24','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',target)

def render_scene(video,audio,target,aspect,native=False,timing=None):
    w,h=(1280,720) if aspect=='16:9' else (720,1280)
    # All native 8-second clips are retimed whole to 7.5s, never cut mid-dialogue.
    length=duration(video)
    if timing:
        start,end=timing
        span=end-start
        speed=max(1,span/7.32)
        if speed>1.25:raise RuntimeError('Verified speech cannot fit without excessive acceleration')
        visual=(f'trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed},' if native else '')
        visual+=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=24,tpad=stop_mode=clone:stop_duration=8,trim=duration=7.5,fade=t=in:st=0:d=0.10,fade=t=out:st=7.4:d=0.10'
        sound=f'atrim=start={start}:end={end},asetpts=PTS-STARTPTS,atempo={speed},apad,atrim=duration=7.5,loudnorm=I=-16:TP=-1.5:LRA=9'
        inputs=['-i',video] if native else ['-i',video,'-i',audio]
        ff(*inputs,'-map','0:v:0','-map','0:a:0' if native else '1:a:0','-vf',visual,'-af',sound,'-t','7.5','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',target)
        return
    vf=f'setpts={7.5/length:.9f}*PTS,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=24,fade=t=in:st=0:d=0.10,fade=t=out:st=7.4:d=0.10'
    if native:
        if not any(s['codec_type']=='audio' for s in probe(video)['streams']): raise RuntimeError('Native dialogue scene has no audio track')
        ff('-i',video,'-vf',vf,'-af',f'atempo={length/7.5:.6f},apad,atrim=0:7.5,loudnorm=I=-16:TP=-1.5:LRA=9','-t','7.5','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',target)
    else:
        ff('-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0','-vf',vf,'-t','7.5','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',target)

def finish(folder,scene_files,sounds=None,scene_seconds=7.5):
    total_seconds=scene_seconds*len(scene_files)
    # Explicit ASS canvas avoids ambiguous SRT style overrides across libass versions.
    import re
    captions=(folder/'captions.srt').read_text(encoding='utf-8')
    header='[Script Info]\nScriptType: v4.00+\nPlayResX: 1280\nPlayResY: 720\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Nirmala UI,28,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,0,0,0,0,100,100,0,0,3,1,0,8,100,100,42,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    header=header.replace('Nirmala UI',os.getenv('CAPTION_FONT','Nirmala UI'))
    events=[]
    for block in captions.strip().split('\n\n'):
        lines=block.splitlines()
        if len(lines)<3: continue
        start,end=lines[1].split(' --> ')
        def ass_time(value): return value[1:8]+'.'+value[9:11]
        text=' '.join(lines[2:]).replace('\\','').replace('{','').replace('}','')
        events.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}')
    (folder/'captions.ass').write_text(header+'\n'.join(events),encoding='utf-8')
    (folder/'concat.txt').write_text('\n'.join(f"file '{p.name}'" for p in scene_files),encoding='utf-8')
    ff('-f','concat','-safe','0','-i','concat.txt','-c','copy','joined.mp4',cwd=folder)
    music_override=os.getenv('BGM_FILE')
    if music_override:
        source=Path(music_override).expanduser().resolve()
        if not source.is_file(): raise RuntimeError('Configured BGM_FILE does not exist')
        ff('-stream_loop','-1','-i',source,'-t',str(total_seconds),'-af',f'volume=0.12,afade=t=in:d=1,afade=t=out:st={max(0,total_seconds-2)}:d=2','-ar','24000','-ac','1',folder/'music.wav')
    else: tone(folder/'music.wav',total_seconds)
    # Add scene-specific, original synthesized effects to the ambience track.
    if sounds:
        with wave.open(str(folder/'music.wav'),'rb') as w: music=bytearray(w.readframes(w.getnframes()))
        for index,kind in enumerate(sounds):
            effect=folder/f'sfx-{index+1:02d}.wav';tone(effect,7.5,kind)
            with wave.open(str(effect),'rb') as w: data=w.readframes(w.getnframes())
            offset=int(index*scene_seconds*24000)*2
            for j in range(0,min(len(data),len(music)-offset),2):
                a=struct.unpack_from('<h',music,offset+j)[0]; b=struct.unpack_from('<h',data,j)[0]
                struct.pack_into('<h',music,offset+j,max(-32768,min(32767,a+b)))
        with wave.open(str(folder/'music.wav'),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(music)
    # Sidechain compression ducks the original, locally synthesized bed under speech.
    ff('-i','joined.mp4','-i','music.wav','-filter_complex','[0:a]asplit=2[voice][key];[1:a][key]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[bed];[voice][bed]amix=inputs=2:normalize=0,alimiter=limit=0.89[a]',
       '-map','0:v','-map','[a]','-t',str(total_seconds),'-vf','ass=captions.ass','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart','final.partial.mp4',cwd=folder)
    (folder/'final.partial.mp4').replace(folder/'final.mp4')
    info=probe(folder/'final.mp4')
    actual=float(info['format']['duration'])
    stream=next(s for s in info['streams'] if s['codec_type']=='video')
    if (stream['width'],stream['height']) not in ((1280,720),(720,1280)):
        raise RuntimeError('Invalid output canvas')
    if abs(actual-total_seconds)>.15: raise RuntimeError(f'Final duration check failed: {actual}; expected {total_seconds}')
    if not {'audio','video'} <= {s['codec_type'] for s in info['streams']}: raise RuntimeError('Missing output stream')
    return {'duration_seconds':actual,'video_codec':stream['codec_name'],'has_audio':True,'width':stream['width'],'height':stream['height']}
