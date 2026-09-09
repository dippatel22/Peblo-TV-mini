import hashlib, json
from collections import defaultdict
from sqlalchemy.orm import Session, joinedload
from .models import Show, Season, Episode, Artwork
from .storage import storage

SECTION_ORDER=['featured','series','minisodes','songs']

def build_catalog(db:Session):
    episodes=(db.query(Episode).join(Episode.season).join(Season.show)
        .options(joinedload(Episode.season).joinedload(Season.show), joinedload(Episode.artworks))
        .filter(Episode.status=='published', Show.status=='published').all())
    groups={}
    for e in episodes:
        show=e.season.show
        if not show.section or e.source_issue: continue
        kinds={a.kind for a in e.artworks}
        required={'thumbnail'} if e.season.number==0 else {'poster','banner','thumbnail'}
        if not e.duration_seconds or not required.issubset(kinds): continue
        # Season 0 is kept out of normal seasons, but trailers are available on the show.
        key=(show.slug,e.content_group)
        item=groups.setdefault(key,{'show_slug':show.slug,'show_title':show.title,'synopsis':show.synopsis,'section':show.section,'categories':sorted(show.categories or []), 'season_number':e.season.number,'episode_number':e.number,'episode_title':e.title,'languages':[], 'duration_seconds':e.duration_seconds, 'artwork':{}})
        if e.language not in item['languages']: item['languages'].append(e.language)
        for a in e.artworks: item['artwork'][a.kind]=f'/media/{a.path}'
        if e.season.number==0:
            item['is_trailer']=True
    shows={}
    for (slug,_), ep in groups.items():
        s=shows.setdefault(slug, {'slug':slug,'title':ep['show_title'],'synopsis':ep['synopsis'],'section':ep['section'],'categories':ep['categories'],'artwork':{},'episodes':[]})
        s['episodes'].append(ep)
    # Artwork is episode-level in this exercise. Pick the first available image for show surfaces.
    for s in shows.values():
        eps=sorted(s['episodes'],key=lambda x:(x['season_number'],x['episode_number'],x['episode_title']))
        s['episodes']=eps
        for kind in ('poster','banner','thumbnail'):
            for ep in eps:
                if kind in ep['artwork']:
                    s['artwork'][kind]=ep['artwork'][kind]; break
        s['seasons']=[]
        season_map=defaultdict(list)
        for ep in eps:
            if ep.get('season_number',0)>0: season_map[ep['season_number']].append(ep)
        for num in sorted(season_map): s['seasons'].append({'number':num,'episodes':season_map[num]})
        s['trailers']=[e for e in eps if e.get('season_number')==0]
        for ep in s['episodes']:
            ep.pop('is_trailer',None)
    sectioned={sec:[] for sec in SECTION_ORDER}
    for s in sorted(shows.values(), key=lambda x:x['title'].lower()): sectioned.setdefault(s['section'],[]).append(s)
    payload={'version':1,'sections':sectioned}
    data=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return payload,data,hashlib.sha256(data).hexdigest()
