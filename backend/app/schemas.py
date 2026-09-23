import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from .models import SkillTier


# ---- auth ----
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    skill_tier: SkillTier


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    # Only required the first time (i.e. this Google account has no
    # existing user yet) — ignored on subsequent logins.
    skill_tier: Optional[SkillTier] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    nickname: str
    skill_tier: SkillTier


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- topics ----
class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    active_date: dt.date
    is_closed: bool
    submission_count: int = 0
    has_submitted: bool = False


# ---- submissions ----
class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic_id: int
    user_id: int
    nickname: str
    image_url: str
    created_at: dt.datetime
    vote_count: int = 0
    is_mine: bool = False
    has_voted: bool = False


# ---- results ----
class ResultEntry(BaseModel):
    submission_id: int
    nickname: str
    image_url: str
    vote_count: int
    rank: int
    is_winner: bool


class TopicResults(BaseModel):
    topic_id: int
    topic_name: str
    is_closed: bool
    entries: list[ResultEntry]
