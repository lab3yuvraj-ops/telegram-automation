import copy
from types import SimpleNamespace
import pytest
from app import production, store
from app.models import Request, Story, validate_links
from app.planning import demo_plan
from app.replicate_provider import Replicate

def test_six_beats_and_landscape_only():
    p=demo_plan({'title':'The last ride'})
    Story.model_validate(p['story'])
    with pytest.raises(ValueError):
        Story.model_validate({**p['story'],'lines':p['story']['lines']*2})
    with pytest.raises(ValueError):Request(title='Test',aspect='9:16')

def test_course_document_uses_selected_plate_and_exact_words():
    p=demo_plan({'title':'Test'})
    scene=p['scenes']['scenes'][2]
    location=p['locations']['backgrounds'][1]
    packet=production.packet(Request(title='Test').model_dump(),p['story']['lines'][2],scene,p['cast'],location,3)
    assert '00:15.0 – 00:22.5' in packet['document']
    assert location['angles'][2] in packet['still_prompt']
    assert p['cast']['characters'][1]['look'] in packet['still_prompt']
    assert 'Studio audio will be layered' in packet['animation_prompt']
    for label in ('ASSETS:', 'SPEAKER:', 'STILL IMAGE PROMPT', 'SYSTEM & ENVIRONMENT', 'PHYSICS/EFFECTS', 'NEGATIVE RESTRICTIONS'):
        assert label in packet['document']

def test_valid_continuing_shot_and_placeholder_rejection():
    p=demo_plan({'title':'Test'})
    p['scenes']['scenes'][1]=copy.deepcopy(p['scenes']['scenes'][0])
    validate_links(p['story'],p['cast'],p['locations'],p['scenes'])
    p['scenes']['scenes'][1]['still_prompt']='placeholder'
    with pytest.raises(ValueError,match='placeholder'):
        validate_links(p['story'],p['cast'],p['locations'],p['scenes'])

def test_uncertain_pruna_prediction_is_never_resubmitted(tmp_path):
    calls=[]
    def submit(**kwargs):
        calls.append(kwargs)
        raise TimeoutError('ambiguous submission')
    provider=object.__new__(Replicate)
    provider.checkpoint=lambda:None
    provider.client=SimpleNamespace(models=SimpleNamespace(get=lambda model:SimpleNamespace(latest_version=SimpleNamespace(id='v1'))),predictions=SimpleNamespace(create=submit))
    path=tmp_path/'image.png'
    with pytest.raises(TimeoutError):provider._predict('model',{},path,{'prompt':'test'})
    assert store.read(path.with_suffix('.operation.json'))['status']=='submitting'
    with pytest.raises(RuntimeError,match='uncertain'):provider._predict('model',{},path,{'prompt':'test'})
    assert len(calls)==1

def test_semantic_plan_failure_stops_before_media(tmp_path,monkeypatch):
    from app import planning,story_engine
    p=demo_plan({'title':'Test'})
    monkeypatch.setattr(story_engine,'build',lambda *args:p['story'])
    for name in ('cast','locations','scenes'):store.save(tmp_path/(name+'.json'),p[name])
    class Reviewer:
        def structured(self,prompt,schema):
            return {'consistent':False,'issues':['Missing final location'],'correction':'Extract the home exterior.'}
    with pytest.raises(RuntimeError,match='before media generation'):
        planning.plan(Reviewer(),tmp_path,Request(title='Test').model_dump(),lambda *args:None)
    assert not store.read(tmp_path/'review-plan.json')['consistent']
