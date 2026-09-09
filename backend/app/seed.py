import json, sys
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from .db import SessionLocal
from .models import Show, Season, Episode, Artwork
from .storage import storage
from .catalog import build_catalog

ROOT=Path(__file__).resolve().parents[1]
SEED=ROOT/'seed_shows.json'
ARTWORK_MAP={'poster':'artwork/poster_demo.jpg','banner':'artwork/banner_demo.jpg','thumbnail':'artwork/thumbnail_demo.jpg'}

def main():
    db=SessionLocal()
    rows=json.loads(SEED.read_text())
    for x in rows:
        show=db.query(Show).filter_by(slug=x['slug']).first()
        if not show:
            show=Show(slug=x['slug'],title=x['show_title'],synopsis=x['synopsis'],section=x.get('section'),status='published' if x['status']=='published' else 'draft',categories=x.get('categories',[]))
            db.add(show); db.flush()
        elif x.get('section') and not show.section: show.section=x['section']
        if x['status']=='published': show.status='published'
        season=db.query(Season).filter_by(show_id=show.id,number=x['season_number']).first()
        if not season: season=Season(show_id=show.id,number=x['season_number']); db.add(season); db.flush()
        if db.query(Episode).filter_by(episode_id=x['episode_id']).first(): continue
        e=Episode(episode_id=x['episode_id'],season_id=season.id,number=x['episode_number'],title=x['episode_title'],duration_seconds=x['duration_seconds'],language=x['language'],content_group=x['content_group'],status=x['status'])
        db.add(e)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing=db.query(Episode).filter_by(content_group=x['content_group'],language=x['language']).first()
            if existing:
                existing.source_issue=f"Seed row {x['episode_id']} duplicates content group {x['content_group']} in language {x['language']}; its title is “{x['episode_title']}”, so the duplicate cannot be published as a separate episode."
                db.commit()
            continue
        for kind in x.get('artwork_available',[]):
            src=ARTWORK_MAP.get(kind)
            if src and (Path(storage.root)/src).exists():
                p=Path(storage.root)/src; data=p.read_bytes(); im_size={'poster':(600,900),'banner':(1280,720),'thumbnail':(640,360)}[kind]
                db.add(Artwork(episode_id=e.id,kind=kind,path=src,width=im_size[0],height=im_size[1],size_bytes=len(data)))
        db.commit()
    payload,data,content_hash=build_catalog(db)
    storage.atomic_publish('catalog.json',data)
    db.close()

if __name__=='__main__': main()
