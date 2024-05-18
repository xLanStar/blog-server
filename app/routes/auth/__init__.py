import logging

from flask import (
    Blueprint,
    jsonify,
)
from flask_mail import Message

# from requests import session
from webargs import fields
from webargs.flaskparser import use_kwargs

from app.config import Config
from app.extensions.db import db
from app.extensions.mail import mail
from app.extensions.oauth import (
    login_user,
    logout_user,
    get_current_user,
    login_required,
)
from app.models import Log

auth_blueprint = Blueprint("auth", __name__, url_prefix="/auth")


@auth_blueprint.route("/login", methods=["POST"])
@use_kwargs(
    {
        "code": fields.Str(required=True),
    }
)
def login(code: str):
    try:
        user = login_user(code)
    except Exception as e:
        logging.error(f"OAuth login failed: {e}")
        return "Login failed", 400

    # 新增登入記錄
    log = Log(
        user_id=user.id,
        action="Login",
    )
    db.session.add(log)
    db.session.commit()

    logging.info(f"User {user.name} logged in.")

    # 發送登入通知郵件
    if Config.MAIL_ENABLE:
        msg = Message("Login Notification", recipients=[user.email])
        msg.body = "You have logged in successfully."
        mail.send(msg)

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "picture": user.picture,
        }
    )


@auth_blueprint.route("/logout", methods=["POST"])
@login_required
def logout():
    current_user = get_current_user()

    # 新增登出記錄
    log = Log(
        user_id=current_user.id,
        action="Logout",
    )
    db.session.add(log)
    db.session.commit()

    logging.info(f"User {current_user.name} logged out.")

    logout_user()

    return "登出成功"


@auth_blueprint.route("/verify", methods=["GET"])
@login_required
def verify():
    current_user = get_current_user()

    if current_user is None:
        logout_user()
        return "Unauthorized", 401

    return jsonify(
        {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "picture": current_user.picture,
        }
    )
