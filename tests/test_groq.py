import json
import httpx
import pytest
from pydantic import BaseModel
from app import groq_text

class Result(BaseModel):
    title:str

def test_groq_schema_and_validated_response(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','secret-test')
    monkeypatch.setenv('GROQ_MODEL','openai/gpt-oss-120b')
    def post(url,**kw):
        assert url=='https://api.groq.com/openai/v1/chat/completions'
        assert kw['json']['response_format']['json_schema']['schema']==Result.model_json_schema()
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"title":"A new story"}'}}]})
    monkeypatch.setattr(httpx,'post',post)
    assert groq_text.structured('test',Result,lambda:None)=={'title':'A new story'}

def test_groq_quota_waits_and_retries_without_leaking(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','secret-test');calls=[]
    def post(*args,**kw):
        calls.append(1)
        if len(calls)==1:return httpx.Response(429,headers={'retry-after':'1'},text='secret-test')
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"title":"A new story"}'}}]})
    monkeypatch.setattr(httpx,'post',post)
    clock=[0]
    monkeypatch.setattr(groq_text.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(groq_text.time,'sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    assert groq_text.structured('test',Result,lambda:None)=={'title':'A new story'}
    assert len(calls)==2

def test_compound_uses_json_object_mode(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test');monkeypatch.setenv('GROQ_MODEL','groq/compound-mini')
    def post(*args,**kw):
        assert kw['json']['response_format']=={'type':'json_object'}
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"title":"A new story"}'}}]})
    monkeypatch.setattr(httpx,'post',post)
    assert groq_text.structured('test',Result,lambda:None)=={'title':'A new story'}

def test_groq_retries_invalid_json_bounded(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test');calls=[]
    def post(*args,**kw):calls.append(1);return httpx.Response(200,json={'choices':[{'message':{'content':'{}'}}]})
    monkeypatch.setattr(httpx,'post',post)
    with pytest.raises(RuntimeError,match='three attempts'):groq_text.structured('test',Result,lambda:None)
    assert len(calls)==3
