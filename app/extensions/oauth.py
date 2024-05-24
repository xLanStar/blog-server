from functools import wraps

from flask import abort, session
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from requests import post

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from app.extensions.db import db
from app.models import User, Log


SECRET_PATH = ".credentials/client_secret.json"
CREDS_PATH = ".credentials/creds.json"


def login_user(code: str) -> User:
    response = post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        },
    ).json()
    # Token contains user info(like email, name, picture)
    token_content = id_token.verify_oauth2_token(
        id_token=response["id_token"],
        request=Request(),
        audience=GOOGLE_CLIENT_ID,
    )

    user = User.query.filter_by(email=token_content["email"]).first()
    if user is None:
        user = User(
            email=token_content["email"],
            name=token_content["name"],
            picture=token_content["picture"],
        )
        db.session.add(user)
        db.session.commit()

        log = Log(
            user_id=user.id,
            action="Register",
        )
        db.session.add(log)
        db.session.commit()

    session["user_id"] = user.id

    return user


def logout_user():
    print("logging out")
    session.clear()


def get_current_user() -> User | None:
    if "user_id" not in session:
        return None

    return User.query.get(session["user_id"])


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        print("validating")
        if "user_id" not in session:
            print("aborting")
            return abort(401)
        else:
            return function(*args, **kwargs)

    return wrapper
