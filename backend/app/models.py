from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Show(Base):
    __tablename__='shows'
    id: Mapped[int]=mapped_column(primary_key=True)
    slug: Mapped[str]=mapped_column(String(160), unique=True, index=True)
    title: Mapped[str]=mapped_column(String(240))
    synopsis: Mapped[str]=mapped_column(Text, default='')
    section: Mapped[str|None]=mapped_column(String(32), nullable=True)
    categories: Mapped[list]=mapped_column(JSON, default=list)
    status: Mapped[str]=mapped_column(String(20), default='draft')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    seasons: Mapped[list['Season']]=relationship(back_populates='show', cascade='all, delete-orphan')

class Season(Base):
    __tablename__='seasons'
    id: Mapped[int]=mapped_column(primary_key=True)
    show_id: Mapped[int]=mapped_column(ForeignKey('shows.id', ondelete='CASCADE'))
    number: Mapped[int]=mapped_column(Integer)
    title: Mapped[str|None]=mapped_column(String(160), nullable=True)
    show: Mapped[Show]=relationship(back_populates='seasons')
    episodes: Mapped[list['Episode']]=relationship(back_populates='season', cascade='all, delete-orphan')
    __table_args__=(UniqueConstraint('show_id','number',name='uq_season_show_number'),)

class Episode(Base):
    __tablename__='episodes'
    id: Mapped[int]=mapped_column(primary_key=True)
    episode_id: Mapped[str]=mapped_column(String(80), unique=True)
    season_id: Mapped[int]=mapped_column(ForeignKey('seasons.id', ondelete='CASCADE'))
    number: Mapped[int]=mapped_column(Integer)
    title: Mapped[str]=mapped_column(String(240))
    duration_seconds: Mapped[int|None]=mapped_column(Integer, nullable=True)
    language: Mapped[str]=mapped_column(String(8))
    content_group: Mapped[str]=mapped_column(String(160), index=True)
    status: Mapped[str]=mapped_column(String(20), default='draft', index=True)
    source_issue: Mapped[str|None]=mapped_column(Text, nullable=True)
    season: Mapped[Season]=relationship(back_populates='episodes')
    artworks: Mapped[list['Artwork']]=relationship(back_populates='episode', cascade='all, delete-orphan')
    __table_args__=(UniqueConstraint('content_group','language',name='uq_episode_group_language'),)

class Artwork(Base):
    __tablename__='artworks'
    id: Mapped[int]=mapped_column(primary_key=True)
    episode_id: Mapped[int]=mapped_column(ForeignKey('episodes.id', ondelete='CASCADE'))
    kind: Mapped[str]=mapped_column(String(20))
    path: Mapped[str]=mapped_column(String(500))
    width: Mapped[int]=mapped_column(Integer)
    height: Mapped[int]=mapped_column(Integer)
    size_bytes: Mapped[int]=mapped_column(Integer)
    episode: Mapped[Episode]=relationship(back_populates='artworks')
    __table_args__=(UniqueConstraint('episode_id','kind',name='uq_artwork_episode_kind'),)

class PublishRun(Base):
    __tablename__='publish_runs'
    id: Mapped[int]=mapped_column(primary_key=True)
    actor: Mapped[str]=mapped_column(String(120))
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str]=mapped_column(String(20))
    show_count: Mapped[int]=mapped_column(Integer, default=0)
    episode_count: Mapped[int]=mapped_column(Integer, default=0)
    catalogue_path: Mapped[str|None]=mapped_column(String(500), nullable=True)
    content_hash: Mapped[str|None]=mapped_column(String(64), nullable=True)
    message: Mapped[str|None]=mapped_column(Text, nullable=True)
