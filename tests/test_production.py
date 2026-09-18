import copy
import json
import pytest
from app import production, media, pipeline, store, auth, local_tts, elevenlabs_tts
from app.models import Request, validate_links
from app.planning import demo_plan

def test_title_only_defaults():
    request=Request(title='The locked door')
    assert request.mode=='live' and request.audio_mode=='elevenlabs'

def test_angle_selection_and_audio_modes():
    p=demo_plan({'title':'test'})
    scene=p['scenes']['scenes'][2];scene['background_angle']=2
    req=Request(title='test').model_dump()
    packet=production.packet(req,p['story']['lines'][2],scene,p['cast'],p['locations']['backgrounds'][0])
    assert packet['camera']=='eye-level roadside' and not packet['native_dialogue']
    assert 'Studio audio will be layered' in packet['audio_prompt']
    narrator=production.packet(req,p['story']['lines'][0],scene,p['cast'],p['locations']['backgrounds'][0])
    assert not narrator['native_dialogue'] and 'mouth remains closed' in narrator['audio_prompt']
    scene['background_angle']=4
    with pytest.raises(ValueError,match='angle'):validate_links(p['story'],p['cast'],p['locations'],p['scenes'])

def test_image_generation_is_resumable_without_external_review(tmp_path):
    class Provider:
        calls=0
        def image(self,prompt,path,refs,aspect):self.calls+=1;path.write_bytes(b'image')
    provider=Provider()
    for _ in range(2):
        production.reviewed_asset(provider,tmp_path/'image.png',[],'prompt','16:9',tmp_path/'review.json','blue')
    assert provider.calls==1

def test_unknown_video_submission_never_retries(tmp_path):
    class Provider:
        calls=0
        def video(self,*args):self.calls+=1;raise RuntimeError('uncertain submission')
    provider=Provider()
    with pytest.raises(RuntimeError,match='uncertain'):
        production.verified_video(provider,tmp_path,1,tmp_path/'still.png',[],dict(animation_prompt='',audio_prompt='',negatives=''),'16:9')
    assert provider.calls==1

def test_completed_video_is_reused_without_external_review(tmp_path):
    class Provider:
        calls=0
        def video(self,prompt,image,path,aspect):self.calls+=1;path.write_bytes(b'video')
    provider=Provider()
    packet=dict(animation_prompt='',audio_prompt='',negatives='',still_prompt='',native_dialogue=False)
    for _ in range(2):
        path,review=production.verified_video(provider,tmp_path,1,tmp_path/'still.png',[],packet,'16:9')
        assert path.name=='raw-01.mp4'
    assert provider.calls==1

def test_retry_operation_is_also_protected_from_regeneration(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    store.init()
    ident=store.create(Request(title='Test',mode='demo').model_dump())
    folder=store.folder(ident)
    store.save(folder/'raw-01-retry.operation.json',{'name':'operations/pending'})
    with pytest.raises(ValueError,match='unresolved'):pipeline.archive_scene(ident,1)

def test_native_speech_trim_renders_real_media(tmp_path):
    if not media.available():pytest.skip('FFmpeg unavailable')
    video=tmp_path/'native.mp4'
    media.ff('-f','lavfi','-i','color=c=blue:s=320x180:r=24:d=8','-f','lavfi','-i','sine=frequency=440:duration=8','-c:v','libx264','-c:a','aac','-shortest',video)
    output=tmp_path/'edited.mp4'
    media.render_scene(video,None,output,'16:9',True,(1,6))
    assert abs(media.duration(output)-7.5)<.05
    streams=media.probe(output)['streams']
    assert {'video','audio'}<={s['codec_type'] for s in streams}

def test_live_orchestration_with_fake_provider(tmp_path,monkeypatch):
    """Exercise all six acts, native/dialogue split, assets and packaging without API charges."""
    monkeypatch.setattr(store,'DATA',tmp_path)
    # No media-provider selection variables are required; Pruna is fixed in code.
    monkeypatch.delenv('IMAGE_PROVIDER',raising=False)
    monkeypatch.delenv('VIDEO_PROVIDER',raising=False)
    monkeypatch.setenv('REPLICATE_API_TOKEN','fake-test-token')
    monkeypatch.setenv('TEXT_PROVIDER','groq')
    monkeypatch.setenv('ALLOW_PAID_GENERATION','true')
    monkeypatch.setattr(media,'available',lambda:True)
    monkeypatch.setattr(media,'duration',lambda path:8)
    monkeypatch.setattr(media,'ff',lambda *args,**kwargs:args[-1].write_bytes(b'media'))
    monkeypatch.setattr(media,'render_scene',lambda video,audio,target,*args:target.write_bytes(b'edited'))
    monkeypatch.setattr(media,'thumbnail',lambda source,target,title:target.write_bytes(b'thumbnail'))
    monkeypatch.setattr(media,'finish',lambda folder,*args,**kwargs:((folder/'final.mp4').write_bytes(b'final') and {'duration_seconds':45}))
    monkeypatch.setattr(local_tts,'synthesize',lambda text,target,check:target.write_bytes(b'local-hindi-audio'))
    monkeypatch.setattr(elevenlabs_tts,'synthesize',lambda text,target,check:target.write_bytes(b'elevenlabs-hindi-audio'))
    store.init()
    p=demo_plan({'title':'The door'})
    expected=[l['text'] for l in p['story']['lines']]
    class Provider:
        def __init__(self,*args):pass
        def image(self,prompt,path,refs=(),aspect='16:9'):path.write_bytes(b'png')
        def video(self,prompt,image,path,aspect):path.write_bytes(b'video')
    from app import replicate_provider
    monkeypatch.setattr(replicate_provider,'Replicate',Provider)
    monkeypatch.setattr(pipeline,'plan',lambda *args:copy.deepcopy(p))
    monkeypatch.setattr(pipeline,'publishing',lambda provider,folder,request,plan:p['publishing'])
    ident=store.create(Request(title='The door').model_dump())
    pipeline.work(ident)
    job=store.get(ident)
    assert job['status']=='complete',job.get('error')
    folder=store.folder(ident)
    assert (folder/'production-kit.zip').exists()
    assert len(list(folder.glob('packet-*.json')))==6
    assert len(list(folder.glob('speech-??.mp3')))==6
    assert len(list(folder.glob('review-audio-??.json')))==0
    assert store.read(folder/'manifest.json')['models']=={
        'image':'google/nano-banana','image_edit':'google/nano-banana','video':'prunaai/p-video-2',
    }
    packet=store.read(folder/'packet-03.json')
    assert not packet['native_dialogue'] and packet['spoken_text']==expected[2]
    assert 'ACTIVE ENVIRONMENT' in packet['animation_prompt']
    assert 'LIP-SYNC CONTROL' in packet['animation_prompt']
