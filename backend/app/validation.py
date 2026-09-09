from sqlalchemy.orm import joinedload
from .models import Show, Episode, Season

VALID_SECTIONS={'featured','series','minisodes','songs'}
VALID_LANGUAGES={'en','hi'}

ARTWORK_REQUIRED={'poster','banner','thumbnail'}

def report(db):
    blocking=[]; warnings=[]
    shows=db.query(Show).options(joinedload(Show.seasons).joinedload(Season.episodes).joinedload(Episode.artworks)).all()
    for show in shows:
        if show.status=='published' and not show.section:
            blocking.append({'severity':'blocking','code':'show_missing_section','message':f'“{show.title}” is published but has no section.','show_slug':show.slug,'fix':'Edit the show and choose Featured, Series, Minisodes, or Songs.'})
        if show.section and show.section not in VALID_SECTIONS:
            blocking.append({'severity':'blocking','code':'invalid_section','message':f'“{show.title}” uses an unknown section.','show_slug':show.slug,'fix':'Choose one of the allowed sections in the show editor.'})
        if show.status=='draft' and not show.section:
            warnings.append({'severity':'warning','code':'draft_missing_section','message':f'“{show.title}” is a draft without a section.','show_slug':show.slug,'fix':'Choose a section before publishing the show.'})
        for season in show.seasons:
            for e in season.episodes:
                if e.language not in VALID_LANGUAGES:
                    blocking.append({'severity':'blocking','code':'invalid_language','message':f'{e.episode_id} uses an unsupported language.','show_slug':show.slug,'episode_id':e.episode_id,'fix':'Choose English (en) or Hindi (hi).'})
                if e.source_issue:
                    blocking.append({'severity':'blocking','code':'seed_duplicate','message':e.source_issue,'show_slug':show.slug,'episode_id':e.episode_id,'fix':'Open this episode and change its content group or language so the pair is unique.'})
                if e.status=='published':
                    if not e.duration_seconds:
                        blocking.append({'severity':'blocking','code':'missing_duration','message':f'{e.episode_id} is published without a duration.','show_slug':show.slug,'episode_id':e.episode_id,'fix':'Enter the episode duration in seconds.'})
                    kinds={a.kind for a in e.artworks}
                    needed={'thumbnail'} if season.number==0 else ARTWORK_REQUIRED
                    missing=sorted(needed-kinds)
                    if missing:
                        label=', '.join(missing)
                        blocking.append({'severity':'blocking','code':'missing_artwork','message':f'{e.episode_id} is missing {label} artwork.','show_slug':show.slug,'episode_id':e.episode_id,'fix':f'Upload the missing {label} artwork using the labelled slot in the episode editor.'})
    return {'blocking':blocking,'warnings':warnings,'can_publish':not blocking,'checked_episodes':sum(len(s.episodes) for sh in shows for s in sh.seasons)}
