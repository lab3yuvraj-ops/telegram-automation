"""Private object storage shared by web replicas and workers. No tenant-supplied paths."""
import os,hashlib,json,mimetypes
from pathlib import Path
from functools import lru_cache

def enabled():return bool(os.getenv('S3_BUCKET'))
@lru_cache
def client():
    import boto3
    from botocore.config import Config
    return boto3.client('s3',endpoint_url=os.environ['S3_ENDPOINT'],aws_access_key_id=os.environ['S3_ACCESS_KEY'],aws_secret_access_key=os.environ['S3_SECRET_KEY'],region_name=os.getenv('S3_REGION','auto'),config=Config(signature_version='s3v4',s3={'addressing_style':'virtual'},retries={'max_attempts':3}))

def records(ident):
    from . import store
    with store.db() as c:return [dict(r) for r in c.execute('SELECT * FROM artifacts WHERE job_id=?',(ident,))]

def publish_path(path):
    from . import store
    if not enabled():return
    try: relative=Path(path).resolve().relative_to(store.DATA.resolve())
    except ValueError:return
    if len(relative.parts)<2:return
    ident=relative.parts[0]
    if len(ident)!=32:return
    job=store.get(ident)
    if not job:return
    name='/'.join(relative.parts[1:])
    if not path.is_file() or path.suffix in ('.tmp',):return
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with store.db() as c: old=c.execute('SELECT digest FROM artifacts WHERE job_id=? AND name=?',(ident,name)).fetchone()
    if old and old[0]==digest:return
    tenant=hashlib.sha256(job['owner'].encode()).hexdigest()
    key=f'tenants/{tenant}/{ident}/{digest}/{name}'
    client().upload_file(str(path),os.environ['S3_BUCKET'],key,ExtraArgs={'ContentType':mimetypes.guess_type(name)[0] or 'application/octet-stream'})
    with store.db() as c:c.execute('INSERT INTO artifacts VALUES (?,?,?,?,?) ON CONFLICT(job_id,name) DO UPDATE SET object_key=excluded.object_key,digest=excluded.digest,size=excluded.size',(ident,name,key,digest,path.stat().st_size))

def sync(ident):
    from . import store
    if not enabled():return
    for path in store.folder(ident).rglob('*'):
        if path.is_file() and not path.name.endswith(('.tmp','.partial.mp4')):publish_path(path)

def hydrate(ident):
    from . import store
    if not enabled():return
    root=store.folder(ident).resolve();root.mkdir(parents=True,exist_ok=True)
    for record in records(ident):
        path=(root/record['name']).resolve()
        if not path.is_relative_to(root):raise ValueError('Invalid saved artifact path')
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==record['digest']:continue
        path.parent.mkdir(parents=True,exist_ok=True)
        client().download_file(os.environ['S3_BUCKET'],record['object_key'],str(path))

def read_json(ident,name):
    from . import store
    if not enabled():
        path=store.folder(ident)/name
        return store.read(path) if path.exists() else None
    with store.db() as c:record=c.execute('SELECT object_key FROM artifacts WHERE job_id=? AND name=?',(ident,name)).fetchone()
    return json.loads(client().get_object(Bucket=os.environ['S3_BUCKET'],Key=record[0])['Body'].read()) if record else None

def forget(ident,names):
    # Archived versions remain stored; only the current artifact index is removed.
    from . import store
    if not enabled():return
    with store.db() as c:
        for name in names:c.execute('DELETE FROM artifacts WHERE job_id=? AND name=?',(ident,name))

def response(ident,name,range_header=None):
    from . import store
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException
    with store.db() as c:record=c.execute('SELECT object_key FROM artifacts WHERE job_id=? AND name=?',(ident,name)).fetchone()
    if not record:raise HTTPException(404,'File not found')
    args={'Bucket':os.environ['S3_BUCKET'],'Key':record[0]}
    if range_header:args['Range']=range_header
    from botocore.exceptions import ClientError
    try:obj=client().get_object(**args)
    except ClientError as e:
        if e.response['Error']['Code']=='InvalidRange':raise HTTPException(416,'Invalid range')
        raise
    headers={'Accept-Ranges':'bytes','Content-Length':str(obj['ContentLength'])}
    if 'ContentRange' in obj:headers['Content-Range']=obj['ContentRange']
    if name.endswith(('.json','.srt','.zip','.md')):headers['Content-Disposition']=f'attachment; filename="{name}"'
    def chunks():
        try:yield from obj['Body'].iter_chunks(chunk_size=256*1024)
        finally:obj['Body'].close()
    return StreamingResponse(chunks(),status_code=206 if 'ContentRange' in obj else 200,media_type=obj.get('ContentType','application/octet-stream'),headers=headers)
