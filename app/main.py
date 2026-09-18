"""Health-only HTTP service; Telegram is the product interface."""
import os,threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from . import store,auth,telegram_bot

@asynccontextmanager
async def lifespan(app):
    store.init();auth.init();telegram_bot.init()
    stop=threading.Event()
    thread=threading.Thread(target=telegram_bot.supervise,args=(stop,),daemon=True,name='telegram')
    thread.start()
    yield
    stop.set();thread.join(timeout=15)

app=FastAPI(title='Nightfall Telegram Backend',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.get('/healthz')
def health():return {'ok':True,'interface':'telegram','telegram_configured':bool(os.getenv('TELEGRAM_BOT_TOKEN')),'telegram_state':telegram_bot.STATE}
