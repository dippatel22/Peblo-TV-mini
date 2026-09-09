from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, cast, Text
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError
import io

from .config import settings
from .db import get_db
from .models import Show, Season, Episode, Artwork, PublishRun
from .schemas import LoginIn, TokenOut, ShowIn, ShowOut, EpisodeIn, EpisodeOut, ValidationReport, PublishOut
from .auth import authenticate, create_token, require_editor, require_admin
from .validation import report
from .catalog import build_catalog
from .storage import storage

app=FastAPI(title='Peblo TV Mini API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

ART={
 'poster': {'aspect':2/3,'target':(600,900)},
 'banner': {'aspect':16/9,'target':(1280,720)},
 'thumbnail': {'aspect':16/9,'target':(640,360)},
}

@app.get('/health')
def health(db:Session=Depends(get_db)):
    try: db.execute(func.now())
    except Exception: raise HTTPException(503,'Database is not ready.')
    return {'status':'ok'}

@app.post('/auth/login',response_model=TokenOut)
def login(body:LoginIn):
    user=authenticate(body.username,body.password)
    if not user: raise HTTPException(401,'Username or password is incorrect.')
    return {'access_token':create_token(user['username'],user['role']),'role':user['role']}

@app.get('/media/{path:path}')
def media(path:str):
    p=Path(settings.storage_root)/'artwork'/path
    try: p.resolve().relative_to((Path(settings.storage_root)/'artwork').resolve())
    except ValueError: raise HTTPException(404,'Artwork not found.')
    if not p.exists(): raise HTTPException(404,'Artwork not found.')
    return FileResponse(p)

@app.get('/admin/shows')
def list_shows(search:str='',section:str='',status:str='',language:str='',page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=50),db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    q=db.query(Show)
    if search:
        like=f'%{search}%'
        q=q.filter(or_(Show.title.ilike(like),Show.slug.ilike(like)))
    if section: q=q.filter(Show.section==section)
    if status: q=q.filter(Show.status==status)
    if language:
        q=q.join(Show.seasons).join(Season.episodes).filter(Episode.language==language).distinct()
    total=q.count(); rows=q.order_by(Show.title).offset((page-1)*page_size).limit(page_size).all()
    return {'items':[ShowOut.model_validate(x).model_dump() for x in rows],'page':page,'page_size':page_size,'total':total,'pages':(total+page_size-1)//page_size}

@app.post('/admin/shows',response_model=ShowOut,status_code=201)
def create_show(body:ShowIn,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    if db.query(Show).filter(Show.slug==body.slug).first(): raise HTTPException(409,'That slug is already in use.')
    s=Show(**body.model_dump()); db.add(s); db.commit(); db.refresh(s); return s

@app.get('/admin/shows/{show_id}',response_model=ShowOut)
def get_show(show_id:int,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    s=db.get(Show,show_id)
    if not s: raise HTTPException(404,'Show not found.')
    return s

@app.put('/admin/shows/{show_id}',response_model=ShowOut)
def update_show(show_id:int,body:ShowIn,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    s=db.get(Show,show_id)
    if not s: raise HTTPException(404,'Show not found.')
    other=db.query(Show).filter(Show.slug==body.slug,Show.id!=show_id).first()
    if other: raise HTTPException(409,'That slug is already in use.')
    for k,v in body.model_dump().items(): setattr(s,k,v)
    db.commit(); db.refresh(s); return s

@app.delete('/admin/shows/{show_id}',status_code=204)
def delete_show(show_id:int,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    s=db.get(Show,show_id)
    if not s: raise HTTPException(404,'Show not found.')
    db.delete(s); db.commit()

@app.get('/admin/episodes')
def list_episodes(search:str='',status:str='',language:str='',section:str='',page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=50),db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    q=db.query(Episode).join(Episode.season).join(Season.show)
    if search:
        like=f'%{search}%'; q=q.filter(or_(Episode.title.ilike(like),Show.title.ilike(like),cast(Show.categories, Text).ilike(like)))
    if status: q=q.filter(Episode.status==status)
    if language: q=q.filter(Episode.language==language)
    if section: q=q.filter(Show.section==section)
    total=q.count(); rows=q.order_by(Show.title,Episode.number,Episode.language).offset((page-1)*page_size).limit(page_size).all()
    def pack(e): return {'id':e.id,'episode_id':e.episode_id,'show_id':e.season.show_id,'show_title':e.season.show.title,'season_number':e.season.number,'number':e.number,'title':e.title,'duration_seconds':e.duration_seconds,'language':e.language,'content_group':e.content_group,'status':e.status,'source_issue':e.source_issue,'artwork':{a.kind:{'width':a.width,'height':a.height,'size_bytes':a.size_bytes,'url':f'/media/{a.path}'} for a in e.artworks}}
    return {'items':[pack(e) for e in rows],'page':page,'page_size':page_size,'total':total,'pages':(total+page_size-1)//page_size}

@app.get('/admin/episodes/{episode_id}')
def get_episode(episode_id:int,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    e=db.get(Episode,episode_id)
    if not e: raise HTTPException(404,'Episode not found.')
    return {'id':e.id,'episode_id':e.episode_id,'show_id':e.season.show_id,'season_number':e.season.number,'number':e.number,'title':e.title,'duration_seconds':e.duration_seconds,'language':e.language,'content_group':e.content_group,'status':e.status,'source_issue':e.source_issue,'artwork':{a.kind:{'width':a.width,'height':a.height,'size_bytes':a.size_bytes,'url':f'/media/{a.path}'} for a in e.artworks}}

@app.post('/admin/shows/{show_id}/episodes',status_code=201)
def create_episode(show_id:int,body:EpisodeIn,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    show=db.get(Show,show_id)
    if not show: raise HTTPException(404,'Show not found.')
    season=db.query(Season).filter_by(show_id=show_id,number=body.season_number).first()
    if not season: season=Season(show_id=show_id,number=body.season_number); db.add(season); db.flush()
    if db.query(Episode).filter_by(episode_id=body.episode_id).first(): raise HTTPException(409,'That episode ID already exists.')
    if db.query(Episode).filter_by(content_group=body.content_group,language=body.language).first(): raise HTTPException(409,'That content group and language combination already exists.')
    e=Episode(season_id=season.id,**{k:v for k,v in body.model_dump().items() if k!='season_number'}); db.add(e); db.commit(); db.refresh(e); return get_episode(e.id,db,_)

@app.put('/admin/episodes/{episode_id}')
def update_episode(episode_id:int,body:EpisodeIn,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    e=db.get(Episode,episode_id)
    if not e: raise HTTPException(404,'Episode not found.')
    if db.query(Episode).filter(Episode.content_group==body.content_group,Episode.language==body.language,Episode.id!=episode_id).first(): raise HTTPException(409,'That content group and language combination already exists.')
    season=e.season
    if season.number!=body.season_number:
        new=db.query(Season).filter_by(show_id=season.show_id,number=body.season_number).first()
        if not new: new=Season(show_id=season.show_id,number=body.season_number); db.add(new); db.flush()
        e.season_id=new.id
    for k,v in body.model_dump().items():
        if k!='season_number': setattr(e,k,v)
    e.source_issue=None
    db.commit(); db.refresh(e); return get_episode(e.id,db,_)

@app.delete('/admin/episodes/{episode_id}',status_code=204)
def delete_episode(episode_id:int,db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    e=db.get(Episode,episode_id)
    if not e: raise HTTPException(404,'Episode not found.')
    db.delete(e); db.commit()

@app.post('/admin/episodes/{episode_id}/artwork/{kind}')
async def upload_artwork(episode_id:int,kind:str,file:UploadFile=File(...),db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    if kind not in ART: raise HTTPException(400,'Choose poster, banner, or thumbnail.')
    e=db.get(Episode,episode_id)
    if not e: raise HTTPException(404,'Episode not found.')
    data=await file.read()
    spec=ART[kind]
    if len(data)>200*1024: raise HTTPException(400,f'{kind.title()} must be 200 KB or smaller. Try exporting a more compressed image.')
    try:
        im=Image.open(io.BytesIO(data)); im.verify(); im=Image.open(io.BytesIO(data))
    except (UnidentifiedImageError,ValueError): raise HTTPException(400,'That file is not a readable image. Please upload a JPG or PNG.')
    w,h=im.size; ratio=w/h; target=spec['target']
    if abs(ratio-spec['aspect'])/spec['aspect']>0.01: raise HTTPException(400,f'{kind.title()} must use a {"2:3" if kind=="poster" else "16:9"} shape. This image is {w}×{h}.')
    if not (target[0]*0.9<=w<=target[0]*1.1 and target[1]*0.9<=h<=target[1]*1.1): raise HTTPException(400,f'{kind.title()} should be close to {target[0]}×{target[1]} px. This image is {w}×{h}.')
    ext='jpg' if (file.content_type or '').lower() in ('image/jpeg','image/jpg') else 'png'
    key=f'artwork/{e.episode_id}/{kind}.{ext}'
    storage.save_bytes(key,data)
    old=db.query(Artwork).filter_by(episode_id=e.id,kind=kind).first()
    if old: old.path=key; old.width=w; old.height=h; old.size_bytes=len(data)
    else: db.add(Artwork(episode_id=e.id,kind=kind,path=key,width=w,height=h,size_bytes=len(data)))
    db.commit()
    return {'kind':kind,'width':w,'height':h,'size_bytes':len(data),'url':f'/media/{key}'}

@app.get('/admin/validation-report',response_model=ValidationReport)
def validation_report(db:Session=Depends(get_db),_:dict=Depends(require_editor)): return report(db)

@app.get('/admin/publish-runs')
def publish_runs(db:Session=Depends(get_db),_:dict=Depends(require_editor)):
    rows=db.query(PublishRun).order_by(PublishRun.id.desc()).limit(20).all()
    return [PublishOut.model_validate(x).model_dump() for x in rows]

@app.post('/admin/catalog/publish',response_model=PublishOut)
def publish(db:Session=Depends(get_db),user:dict=Depends(require_admin)):
    validation=report(db)
    run=PublishRun(actor=user.get('sub','admin'),status='running'); db.add(run); db.commit(); db.refresh(run)
    if validation['blocking']:
        run.status='blocked'; run.finished_at=datetime.now(timezone.utc); run.message=f"Publish blocked by {len(validation['blocking'])} issue(s)."; db.commit(); return run
    payload,data,content_hash=build_catalog(db)
    key=f'catalog.{run.id}.json'
    storage.save_bytes(key,data)
    try:
        current_hash=__import__('hashlib').sha256(storage.read_bytes('catalog.json')).hexdigest()
    except FileNotFoundError:
        current_hash=None
    if current_hash != content_hash:
        storage.atomic_publish('catalog.json',data)
        message='Catalogue published successfully.'
    else:
        message='No catalogue changes; existing published snapshot kept.'
    run.status='published'; run.finished_at=datetime.now(timezone.utc); run.show_count=sum(len(v) for v in payload['sections'].values()); run.episode_count=sum(len(s['episodes']) for v in payload['sections'].values() for s in v); run.catalogue_path=key; run.content_hash=content_hash; run.message=message
    db.commit(); db.refresh(run); return run

@app.get('/catalog')
def catalog():
    p=Path(settings.storage_root)/'catalog.json'
    if not p.exists(): return {'version':1,'sections':{'featured':[],'series':[],'minisodes':[],'songs':[]}}
    return Response(p.read_bytes(),media_type='application/json',headers={'Cache-Control':'public, max-age=60'})

@app.get('/catalog/search')
def catalog_search(q:str='',category:str='',language:str='',section:str=''):
    p=Path(settings.storage_root)/'catalog.json'
    if not p.exists(): return {'items':[],'total':0}
    import json
    data=json.loads(p.read_text())
    items=[]
    for sec,shows in data.get('sections',{}).items():
        for show in shows:
            if section and sec!=section: continue
            hay=' '.join([show['title'],show['synopsis'],' '.join(show.get('categories',[]))])
            episode_matches=[]
            for ep in show.get('episodes',[]):
                if language and language not in ep.get('languages',[]): continue
                if q and q.lower() not in (hay+' '+ep['episode_title']).lower(): continue
                episode_matches.append(ep)
            if not q and not language: episode_matches=show.get('episodes',[])
            elif q and not episode_matches: continue
            if category and category not in show.get('categories',[]): continue
            clone={**show,'episodes':episode_matches}
            items.append(clone)
    return {'items':items,'total':len(items)}
