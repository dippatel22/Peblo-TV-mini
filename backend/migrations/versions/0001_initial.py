"""initial schema"""
from alembic import op
import sqlalchemy as sa
revision='0001_initial'; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('shows',
        sa.Column('id', sa.Integer, primary_key=True), sa.Column('slug', sa.String(160), nullable=False, unique=True),
        sa.Column('title', sa.String(240), nullable=False), sa.Column('synopsis', sa.Text, nullable=False, server_default=''),
        sa.Column('section', sa.String(32), nullable=True), sa.Column('categories', sa.JSON, nullable=False, server_default='[]'), sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('seasons',
        sa.Column('id', sa.Integer, primary_key=True), sa.Column('show_id', sa.Integer, sa.ForeignKey('shows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('number', sa.Integer, nullable=False), sa.Column('title', sa.String(160), nullable=True),
        sa.UniqueConstraint('show_id','number', name='uq_season_show_number'))
    op.create_table('episodes',
        sa.Column('id', sa.Integer, primary_key=True), sa.Column('episode_id', sa.String(80), nullable=False, unique=True),
        sa.Column('season_id', sa.Integer, sa.ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('number', sa.Integer, nullable=False), sa.Column('title', sa.String(240), nullable=False), sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('language', sa.String(8), nullable=False), sa.Column('content_group', sa.String(160), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'), sa.Column('source_issue', sa.Text, nullable=True),
        sa.UniqueConstraint('content_group','language', name='uq_episode_group_language'))
    op.create_index('ix_episodes_status', 'episodes', ['status'])
    op.create_index('ix_episodes_language', 'episodes', ['language'])
    op.create_index('ix_episodes_content_group', 'episodes', ['content_group'])
    op.create_table('artworks',
        sa.Column('id', sa.Integer, primary_key=True), sa.Column('episode_id', sa.Integer, sa.ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False), sa.Column('path', sa.String(500), nullable=False), sa.Column('width', sa.Integer, nullable=False),
        sa.Column('height', sa.Integer, nullable=False), sa.Column('size_bytes', sa.Integer, nullable=False),
        sa.UniqueConstraint('episode_id','kind', name='uq_artwork_episode_kind'))
    op.create_table('publish_runs',
        sa.Column('id', sa.Integer, primary_key=True), sa.Column('actor', sa.String(120), nullable=False), sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True), sa.Column('status', sa.String(20), nullable=False),
        sa.Column('show_count', sa.Integer, nullable=False, server_default='0'), sa.Column('episode_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('catalogue_path', sa.String(500), nullable=True), sa.Column('content_hash', sa.String(64), nullable=True), sa.Column('message', sa.Text, nullable=True))

def downgrade():
    op.drop_table('publish_runs'); op.drop_table('artworks'); op.drop_index('ix_episodes_content_group'); op.drop_index('ix_episodes_language'); op.drop_index('ix_episodes_status'); op.drop_table('episodes'); op.drop_table('seasons'); op.drop_table('shows')
