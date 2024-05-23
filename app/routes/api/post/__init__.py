import datetime
import logging

from flask import Blueprint
from webargs import fields
from webargs.flaskparser import use_kwargs

from app.extensions.db import db
from app.extensions.oauth import get_current_user, login_required
from app.models import Post, Log, User, Comment, PostLike
from app.utils.hash import get_hash
from app.utils.cipher import encrypt, decrypt

post_blueprint = Blueprint("post", __name__, url_prefix="/post")


@post_blueprint.route("", methods=["GET"])
@login_required
def get_posts():
    posts: list[Post] = Post.query.order_by(Post.created_at.desc()).all()

    if any(get_hash(post.text) != post.text_hash for post in posts):
        return f"發現文章資料被竄改,請通知管理員", 500

    if any(
        get_hash(comment.text) != comment.text_hash
        for post in posts
        for comment in post.comments
    ):
        return f"發現留言資料被竄改,請通知管理員", 500

    try:
        decrypted_posts = [
            {
                "id": post.id,
                "text": decrypt(post.text_iv, post.text),
                "comments": [
                    {
                        "id": comment.id,
                        "text": decrypt(comment.text_iv, comment.text),
                        "author_id": comment.user.id,
                        "author_name": comment.user.name,
                        "created_at": comment.created_at,
                        "author_picture": comment.user.picture,
                    }
                    for comment in post.comments
                ],
                "created_at": post.created_at,
                "author_id": post.user.id,
                "author_name": post.user.name,
                "author_picture": post.user.picture,
                "liked": any(
                    like.user_id == get_current_user().id for like in post.post_likes
                ),
                "likes_count": len(post.post_likes),
            }
            for post in posts
        ]
    except ValueError as e:
        return f"解密過程中出現錯誤: {str(e)}", 500

    return decrypted_posts


@post_blueprint.route("", methods=["POST"])
@use_kwargs(
    {
        "text": fields.Str(required=True),
    }
)
@login_required
def create_post(text: str):
    # if "password" in text:  # 檢查是否輸入了類似密碼的文字
    #     # 要求再三確認
    #     return render_template("confirm.html", text=text, action="post")

    current_user = get_current_user()

    text_iv, encrypted_text = encrypt(text)
    text_hash = get_hash(encrypted_text)
    post = Post(
        user_id=current_user.id,
        text=encrypted_text,
        text_hash=text_hash,
        text_iv=text_iv,
    )
    db.session.add(post)
    db.session.commit()

    # 新增建立貼文記錄
    log = Log(
        user_id=current_user.id,
        action="Create-Post",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} added a new post.")

    return "新增成功"


@post_blueprint.route("/<int:id>", methods=["DELETE"])
@login_required
def delete_post(id: int):
    post = Post.query.get(id)

    if post is None:
        return "找不到貼文", 404

    current_user = get_current_user()

    if current_user.id != post.user_id:
        logging.error("Failed to add, delete, or modify a post.")
        return "你沒有權限刪除", 403

    comments = Comment.query.filter_by(post_id=id)

    for _ in comments:
        log = Log(
            user_id=current_user.id,
            action="Delete-Comment",
        )
        db.session.add(log)

    comments.delete()
    db.session.delete(post)
    db.session.commit()

    # 新增刪除貼文記錄
    log = Log(
        user_id=current_user.id,
        action="Delete-Post",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} deleted a post.")

    return "刪除成功"


@post_blueprint.route("/<int:id>", methods=["PATCH"])
@use_kwargs(
    {
        "text": fields.Str(required=False),
    }
)
@login_required
def edit_post(id: int, **kwargs):
    post: Post | None = Post.query.get(id)

    if post is None:
        return "找不到貼文", 404

    current_user = get_current_user()

    if current_user.id != post.user_id:
        logging.error("Failed to add, delete, or modify a post.")
        return "你沒有權限編輯", 403

    if "text" in kwargs:
        text_iv, encrypted_text = encrypt(kwargs["text"])
        post.text = encrypted_text
        post.text_hash = get_hash(encrypted_text)
        post.text_iv = text_iv

    db.session.commit()

    # 新增編輯貼文記錄
    log = Log(
        user_id=current_user.id,
        action="Edit-Post",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} edited a post.")

    return "編輯成功"


@post_blueprint.route("/like/<int:id>", methods=["POST"])
@login_required
def like_post(id: int):
    post: Post | None = Post.query.get(id)

    if post is None:
        return "找不到貼文", 404

    current_user = get_current_user()

    post_like: PostLike | None = PostLike.query.filter_by(
        user_id=current_user.id,
        post_id=id,
    ).first()

    if post_like is not None:
        return "你已經喜歡過這篇文章了", 403

    post_like = PostLike(
        user_id=current_user.id,
        post_id=id,
    )
    db.session.add(post_like)

    # 新增喜歡貼文記錄
    log = Log(
        user_id=current_user.id,
        action="Like-Post",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} liked a post.")

    return "喜歡貼文成功"


@post_blueprint.route("/dislike/<int:id>", methods=["POST"])
@login_required
def dislike_post(id: int):
    post: Post | None = Post.query.get(id)

    if post is None:
        return "找不到貼文", 404

    current_user = get_current_user()

    post_like: PostLike | None = PostLike.query.filter_by(
        user_id=current_user.id,
        post_id=id,
    ).first()

    if post_like is None:
        return "無法進行此操作", 403

    db.session.delete(post_like)
    db.session.commit()

    # 新增取消喜歡貼文記錄
    log = Log(
        user_id=current_user.id,
        action="Dislike-Post",
    )
    db.session.add(log)
    db.session.commit()

    logging.debug(f"User {current_user} disliked a post.")

    return "取消喜歡貼文成功"
