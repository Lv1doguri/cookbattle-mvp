import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class SkillTier(str, enum.Enum):
    """Self-selected cooking skill level, chosen once at signup.

    Topics/submissions/votes/results are scoped per tier so beginners
    only ever compete against beginners, not the whole user base.
    """

    BEGINNER = "beginner"  # 하
    INTERMEDIATE = "intermediate"  # 중
    ADVANCED = "advanced"  # 상


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # null for Google-only accounts
    google_sub = Column(String, unique=True, index=True, nullable=True)
    nickname = Column(String, nullable=False)
    skill_tier = Column(SQLEnum(SkillTier), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    submissions = relationship("Submission", back_populates="user")
    votes = relationship("Vote", back_populates="voter")


class Topic(Base):
    """A cooking theme. `active_date` is the single day it's open for entries."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    active_date = Column(Date, nullable=False, index=True)
    is_closed = Column(Boolean, default=False)  # manually or cron-flipped once voting ends
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    submissions = relationship("Submission", back_populates="topic")


class Submission(Base):
    """One user's dish photo entry for one topic. One per user per topic (enforced)."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("topic_id", "user_id", name="uq_one_entry_per_user_per_topic"),)

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    topic = relationship("Topic", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    votes = relationship("Vote", back_populates="submission")


class Vote(Base):
    """A vote cast by one user for one submission. One vote per voter per topic (enforced in code)."""

    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("submission_id", "voter_id", name="uq_no_duplicate_vote"),)

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    submission = relationship("Submission", back_populates="votes")
    voter = relationship("User", back_populates="votes")
