from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.extensions.db import db


class User(db.Model):
    id = Column(
        Integer,
        primary_key=True,
    )
    email = Column(
        String(255),
        unique=True,
        nullable=False,
    )
    name = Column(
        String(50),
        unique=True,
        nullable=False,
    )
    picture = Column(
        String(255),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        index=True,
    )

    posts = relationship(
        "Post",
        backref="user",
        passive_deletes=True,
    )
    comments = relationship(
        "Comment",
        backref="user",
        passive_deletes=True,
    )
    post_likes = relationship(
        "PostLike",
        backref="user",
        passive_deletes=True,
    )
    logs = relationship(
        "Log",
        backref="user",
        passive_deletes=True,
    )

    def __json__(self):
        return {
            "id": self.id,
            "name": self.name,
        }
