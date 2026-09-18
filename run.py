"""Run `python run.py` or `python run.py --title "The Last Auto" --mode demo`."""
import argparse, time, os
from dotenv import load_dotenv
load_dotenv()

def main():
    p=argparse.ArgumentParser(description='Nightfall: title to 60-second horror video')
    p.add_argument('--title');p.add_argument('--mode',choices=['demo','live'],default='demo')
    p.add_argument('--language',choices=['Hindi','Hinglish','English'],default='Hindi')
    p.add_argument('--audio-mode',choices=['elevenlabs','local','studio','native'],default='elevenlabs')
    args=p.parse_args()
    if args.title:
        from app import store, pipeline, auth
        from app.models import Request
        store.init();auth.init();ident=store.create(Request(title=args.title,mode=args.mode,language=args.language,audio_mode=args.audio_mode).model_dump())
        pipeline.enqueue(ident)
        last=''
        while True:
            job=store.get(ident)
            if job['stage']!=last: print(job['stage'],flush=True);last=job['stage']
            if job['status'] in ('complete','failed','cancelled'):
                print(store.folder(ident) if job['status']=='complete' else job['error'])
                raise SystemExit(0 if job['status']=='complete' else 1)
            time.sleep(1)
    else:
        if os.getenv('APP_ROLE')=='worker':
            from app.worker import main as worker_main
            worker_main();return
        import uvicorn
        uvicorn.run('app.main:app',host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','8000')),proxy_headers=True,forwarded_allow_ips='*' if os.getenv('RAILWAY_ENVIRONMENT_ID') else '127.0.0.1')
if __name__=='__main__': main()
