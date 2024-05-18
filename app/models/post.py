from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.extensions.db import db


class Post(db.Model):
    id = Column(
        Integer,
        primary_key=True,
    )
    text = Column(
        LargeBinary,
        nullable=False,
    )
    text_iv = Column(
        LargeBinary,
        nullable=False,
    )
    text_hash = Column(
        LargeBinary,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comments = relationship(
        "Comment",
        backref="post",
        passive_deletes=True,
    )
    post_likes = relationship(
        "PostLike",
        backref="post",
        passive_deletes=True,
    )