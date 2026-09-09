from app.validation import report
from app.models import Show, Season, Episode, Artwork

def test_published_episode_without_artwork_blocks(db_session):
    show=Show(slug='demo',title='Demo',synopsis='x',section='series',status='published',categories=['stories'])
    db_session.add(show); db_session.flush()
    season=Season(show_id=show.id,number=1); db_session.add(season); db_session.flush()
    ep=Episode(episode_id='ep-x',season_id=season.id,number=1,title='One',duration_seconds=30,language='en',content_group='demo-s01e01',status='published')
    db_session.add(ep); db_session.commit()
    r=report(db_session)
    assert any(i['code']=='missing_artwork' for i in r['blocking'])

def test_draft_missing_section_is_warning(db_session):
    db_session.add(Show(slug='draft',title='Draft',synopsis='x',section=None,status='draft',categories=[])); db_session.commit()
    r=report(db_session)
    assert not any(i['code']=='show_missing_section' for i in r['blocking'])
    assert any(i['code']=='draft_missing_section' for i in r['warnings'])
