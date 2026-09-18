import sys,types
import pytest
from PIL import Image
from app import hf_images

def test_hf_routes_dimensions_and_no_secret_metadata(tmp_path,monkeypatch):
    monkeypatch.setenv('HF_TOKEN','hf_test_secret')
    calls=[]
    class Client:
        def __init__(self,**kwargs):assert kwargs['provider']=='fal-ai'
        def text_to_image(self,prompt,**kwargs):calls.append(kwargs);return Image.new('RGB',(kwargs['width'],kwargs['height']))
    monkeypatch.setitem(sys.modules,'huggingface_hub',types.SimpleNamespace(InferenceClient=Client))
    path=tmp_path/'reference.png'
    hf_images.generate('woman in blue',path,lambda:None)
    assert Image.open(path).size==(1024,576)
    assert calls[0]['model']==hf_images.MODEL and calls[0]['num_inference_steps']==4
    assert 'hf_test_secret' not in path.with_suffix('.generation.json').read_text()

def test_hf_never_drops_reference_images(tmp_path):
    with pytest.raises(ValueError,match='cannot compose'):hf_images.generate('prompt',tmp_path/'x.png',lambda:None,refs=[('tag',tmp_path/'ref.png')])

def test_missing_key_stops_without_paid_fallback(tmp_path,monkeypatch):
    monkeypatch.setenv('HF_TOKEN','')
    with pytest.raises(RuntimeError,match='HF_TOKEN'):hf_images.generate('prompt',tmp_path/'x.png',lambda:None)
