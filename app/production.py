"""Durable course scene packets and bounded production quality gates."""
import hashlib
import re
from . import store, media

VERSION = 'course-4'

def packet(request, line, scene, cast, location, number=1):
    speaker=next((c for c in cast['characters'] if c['name']==line['speaker']),None)
    # Both local and hosted narration are mixed after rendering; the video model
    # must not create a competing voice or lip movement for either path.
    studio=request.get('audio_mode') in ('studio','local','elevenlabs')
    native=speaker is not None and not studio
    performance=(speaker['performance'] if speaker else 'Low cinematic narrator, native Indian accent, clear natural diction')
    active=', '.join(scene['character_tags']) if scene['character_tags'] else 'none'
    audio=(f"[LIP-SYNC LOCK]: Studio audio will be layered in editing. Every visible character mouth remains closed. Do not generate voices, dialogue or singing.\n"
           if studio else f"[LIP-SYNC LOCK]: Only {line['speaker']} speaks. EXACT DIALOGUE ({request['language']}): {line['text']}\n"
           f"VOICE DIRECTION: {performance}. Emotion: {line['emotion']}. Finish the complete line within eight seconds. "
           'Only this speaker moves their mouth; all other mouths stay closed. No narrator or additional voices.'
           if speaker else f'[LIP-SYNC LOCK]: No character speaks. Every character mouth remains closed and static. OFF-SCREEN NARRATOR: Read this exact {request["language"]} narration: {line["text"]}. No visible mouth moves.')
    negatives='NO photorealism; NO 3D rendering; NO CGI shading; NO realistic skin or hair textures; NO extra characters; NO identity changes; NO dual-character lip-sync; NO English-accent inflection; NO text overlays; NO subtitles; NO watermarks.'
    # Compile the fixed template ourselves; generated fields contain visual prose only.
    camera=location['angles'][scene.get('background_angle',1)-1]
    from .config import STYLE
    identities='\n'.join(c['tag']+': '+c['look'] for c in cast['characters'] if c['tag'] in scene['character_tags'])
    still=f"{STYLE}\nACTIVE ENVIRONMENT: {scene['background_tag']}\nCAMERA: {camera}\nACTIVE CHARACTERS: {active}\nMANDATORY VISIBLE STORY EVENT: Depict this spoken beat literally in the frame, using concrete people, objects and action; do not replace it with generic mood: {line['text']}\n{scene['still_prompt']}\nLOCKED IDENTITIES:\n{identities}\nUse the supplied reference images exactly. No unlisted people or faces."
    formatted=(f"### SYSTEM & ENVIRONMENT\nCLIP LENGTH: 8 seconds (edited to 7.5 seconds)\nSTYLE ANCHOR: {STYLE}\nACTIVE ENVIRONMENT: {scene['background_tag']}\nACTIVE CHARACTERS: {active}\n\n### VISUAL ACTION & CAMERA\nCAMERA: {camera}\nSCENE ACTION: {scene['animation_prompt']}\nPHYSICS/EFFECTS: {scene.get('physics_effects','Only movement explicitly described by the scene action; preserve geometry.')}\n\n### LIP-SYNC CONTROL & AUDIO\n{audio}\nSOUND DESIGN: {scene.get('audio_prompt','Quiet location ambience.')} No music.\n\n### NEGATIVE RESTRICTIONS\n{negatives}")
    def stamp(seconds):
        return f'{int(seconds)//60:02d}:{seconds%60:04.1f}'
    document=(f"SCENE {number} — {scene['title']}\nTIMESTAMP: {stamp((number-1)*7.5)} – {stamp(number*7.5)}\nASSETS: {scene['background_tag']} + {active}\nSPEAKER: {speaker['tag'] if speaker else 'NARRATOR (layer in edit)'}\n\nSTILL IMAGE PROMPT\n{still}\n\nANIMATION + AUDIO PROMPT\n{formatted}")
    return {'version':VERSION,'language':request['language'],'speaker':line['speaker'],'spoken_text':line['text'],
            'native_dialogue':native,'voice_direction':performance,'character_tags':scene['character_tags'],
            'background_tag':scene['background_tag'],'background_angle':scene.get('background_angle',1),
            'camera':location['angles'][scene.get('background_angle',1)-1],
            'still_prompt':still,'animation_prompt':formatted,'document':document,
            'audio_prompt':audio+'\nAmbience and effects: '+scene.get('audio_prompt','Quiet location ambience.')+' No music.',
            'negatives':negatives}

def reviewed_asset(provider,path,refs,prompt,aspect,review_path,requirements):
    """Generate one resumable Pruna image candidate without external review."""
    if not path.exists():provider.image(prompt,path,refs,aspect)

def verified_video(provider,folder,n,still,refs,packet,aspect):
    """Generate one resumable full-quality Pruna video candidate without external review."""
    video=folder/f'raw-{n:02d}.mp4'
    if not video.exists():provider.video(packet['animation_prompt']+'\n'+packet['audio_prompt']+'\n'+packet['negatives'],still,video,aspect)
    return video,None
