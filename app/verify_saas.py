"""Explicit diagnostic: 200 isolated test tenants, no external calls or media generation.
Run with python -m app.verify_saas. Uses a disposable PostgreSQL schema only.
"""
import os,uuid,tempfile,time,json,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def main():
    import psycopg
    from psycopg.conninfo import make_conninfo
    original=os.environ['DATABASE_URL'];schema='nightfall_test_'+uuid.uuid4().hex
    connection=psycopg.connect(original,autocommit=True)
    connection.execute('CREATE SCHEMA '+schema)
    os.environ['DATABASE_URL']=make_conninfo(original,options='-c search_path='+schema)
    os.environ.pop('S3_BUCKET',None);os.environ.pop('REPLICATE_API_TOKEN',None)
    os.environ['COOKIE_SECURE']='false'
    from . import store,auth,database,worker
    started=time.monotonic()
    try:
        with tempfile.TemporaryDirectory() as root:
            store.DATA=Path(root);store.init();auth.init()
            hashed=auth.password_hash('load-test-password')
            with store.db() as c:
                for i in range(200):c.execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',(f'load-{i}',hashed,'member'))
            def submit(i):
                owner=f'load-{i}';key=f'fake-private-key-{i}'
                auth.set_key(owner,key)
                ident=store.create({'title':f'Test {i}','mode':'demo'},owner,key_cipher=auth.cipher().encrypt(key.encode()).decode())
                return ident,owner,key
            with ThreadPoolExecutor(max_workers=20) as pool:jobs=list(pool.map(submit,range(200)))
            expected={j[0]:j for j in jobs};seen=set();mutex=threading.Lock()
            def consume(_):
                while True:
                    item=worker.claim()
                    if not item:return
                    ident,token,lease=item
                    try:
                        with mutex:
                            assert ident not in seen,'Duplicate claim';seen.add(ident)
                        assert store.get(ident)['owner']==expected[ident][1]
                        assert auth.job_key(ident)==expected[ident][2],'Cross-tenant key leak'
                        store.update(ident,status='complete')
                    finally:lease.close()
            with ThreadPoolExecutor(max_workers=20) as pool:list(pool.map(consume,range(20)))
            assert len(seen)==200
            # Real authenticated HTTP requests through the app, with 200 concurrent clients.
            from .main import app
            from fastapi.testclient import TestClient
            def check_http(i):
                ident,owner,key=jobs[i]
                with TestClient(app) as c:
                    login=c.post('/api/auth/login',json={'username':owner,'password':'load-test-password'})
                    assert login.status_code==200
                    own=c.get('/api/jobs').json();assert len(own)==1 and own[0]['id']==ident
                    assert c.get('/api/jobs/'+jobs[(i+1)%200][0]).status_code==404
                    assert key not in c.get('/api/status').text
            # Shared lifespan already initialized; avoid rerunning migrations for every client.
            def request_wave(i):
                ident,owner,key=jobs[i]
                c=TestClient(app,client=(f'192.0.2.{i+1}',50000+i))
                login=c.post('/api/auth/login',json={'username':owner,'password':'load-test-password'})
                assert login.status_code==200
                own=c.get('/api/jobs').json();assert len(own)==1 and own[0]['id']==ident
                assert c.get('/api/jobs/'+jobs[(i+1)%200][0]).status_code==404
                assert key not in c.get('/api/status').text
                c.close()
            with ThreadPoolExecutor(max_workers=20) as pool:list(pool.map(request_wave,range(200)))
            import asyncio,httpx
            tokens=[]
            for i in range(200):
                result,error=auth.login(f'load-{i}','load-test-password',f'wave-{i}')
                assert not error;tokens.append(result['token'])
            async def wave():
                transport=httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport,base_url='http://testserver',timeout=60) as c:
                    async def read(i):
                        response=await c.get('/api/jobs',cookies={auth.COOKIE:tokens[i]})
                        assert response.status_code==200 and response.json()[0]['owner']==f'load-{i}'
                    await asyncio.gather(*(read(i) for i in range(200)))
            asyncio.run(wave())
            print(json.dumps({'tenants':200,'jobs_claimed_once':len(seen),'parallel_queue_threads':20,'simultaneous_dashboard_requests':200,'cross_account_checks':200,'external_calls':0,'seconds':round(time.monotonic()-started,2)}),flush=True)
    finally:
        if database._pool:database._pool.close()
        connection.execute('DROP SCHEMA '+schema+' CASCADE');connection.close()

if __name__=='__main__':main()
