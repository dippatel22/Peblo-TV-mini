from pydantic import BaseModel, Field, field_validator
from typing import Literal

Section=Literal['featured','series','minisodes','songs']
Language=Literal['en','hi']
Status=Literal['draft','published']

class LoginIn(BaseModel): username: str; password: str
class TokenOut(BaseModel): access_token: str; role: str

class ShowIn(BaseModel):
    title: str = Field(min_length=1,max_length=240)
    slug: str = Field(min_length=1,max_length=160)
    synopsis: str = ''
    section: Section|None = None
    categories: list[str] = []
    status: Status = 'draft'
    @field_validator('slug')
    @classmethod
    def slug_ok(cls,v):
        if not all(c.isalnum() or c=='-' for c in v): raise ValueError('Use lowercase letters, numbers and hyphens only.')
        return v
class ShowOut(ShowIn):
    id:int
    class Config: from_attributes=True

class SeasonIn(BaseModel): number:int=Field(ge=0); title:str|None=None
class EpisodeIn(BaseModel):
    episode_id: str=Field(min_length=1,max_length=80)
    season_number:int=Field(ge=0)
    number:int=Field(ge=1)
    title:str=Field(min_length=1,max_length=240)
    duration_seconds:int|None=Field(default=None,ge=1)
    language:Language
    content_group:str=Field(min_length=1,max_length=160)
    status:Status='draft'

class EpisodeOut(EpisodeIn):
    id:int; show_id:int; artwork:dict[str,dict]
    class Config: from_attributes=True

class ValidationIssue(BaseModel):
    severity:str
    code:str
    message:str
    show_slug:str|None=None
    episode_id:str|None=None
    fix:str
class ValidationReport(BaseModel):
    blocking:list[ValidationIssue]
    warnings:list[ValidationIssue]
    can_publish:bool
    checked_episodes:int

class PublishOut(BaseModel):
    id:int; status:str; show_count:int; episode_count:int; content_hash:str|None; message:str|None
    class Config: from_attributes=True
