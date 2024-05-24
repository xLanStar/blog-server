import logging

from flask import Blueprint
from webargs import fields
from webargs.flaskparser import use_kwargs

from app.extensions.db import db
from app.extensions.oauth import get_current_user, login_required
from app.models import Post, Comment, Log
from app.utils.hash import get_hash
from app.utils.cipher import encrypt, decrypt


comment_blueprint = Blueprint("comment", __name__, url_prefix="/comment")


@comment_blueprint.route("", methods=["POST"])
@use_kwargs(
    {
        "post_id": fields.Int(required=True),
        "text": fields.Str(required=True),
    }
)
@login_required
def create_comment(post_id: int, text: str):
    post: Post | None = Post.query.get(post_id)
    if post is None:
        logging.error("Failed to add a comment.")
        return "找不到貼文", 404

    current_user = get_current_user()

    text_iv, encrypted_text = encrypt(text)
    text_hash = get_hash(encrypted_text)
    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        text=encrypted_text,
        text_hash=text_hash,
        text_iv=text_iv,
    )
    db.session.add(comment)
    db.session.commit()

    # 新增建立留言記錄
    log = Log(
        user_id=current_user.id,
        action="Comment",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} added a new comment.")

    return "新增成功"


@comment_blueprint.route("/<int:id>", methods=["DELETE"])
@login_required
def delete_comment(id: int):
    comment: Comment | None = Comment.query.get(id)
    if comment is None:
        logging.error("Failed to delete a comment.")
        return "找不到留言", 404

    current_user = get_current_user()

    if current_user.id != comment.user_id:
        logging.error("Failed to delete a comment.")
        return "你沒有權限刪除", 403

    db.session.delete(comment)
    db.session.commit()

    # 新增刪除留言記錄
    log = Log(
        user_id=current_user.id,
        action="Delete-Comment",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} deleted a comment.")

    return "刪除成功"


@comment_blueprint.route("/<int:id>", methods=["PATCH"])
@use_kwargs(
    {
        "text": fields.Str(required=False),
    }
)
@login_required
def edit_comment(id: int, **kwargs):
    comment: Comment | None = Comment.query.get(id)

    if comment is None:
        return "找不到留言", 404

    current_user = get_current_user()

    if current_user.id != comment.user_id:
        logging.error("Failed to add, delete, or modify a comment.")
        return "你沒有權限編輯", 403

    if "text" in kwargs:
        text_iv, encrypted_text = encrypt(kwargs["text"])
        comment.text = encrypted_text
        comment.text_hash = get_hash(encrypted_text)
        comment.text_iv = text_iv

    db.session.commit()

    # 新增編輯留言記錄
    log = Log(
        user_id=current_user.id,
        action="Edit-Comment",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} edited a comment.")

    return "編輯成功"
