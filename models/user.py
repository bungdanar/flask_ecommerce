from typing import Union
from requests import Response, post
from flask import request, url_for

from db import db

MAILGUN_DOMAIN = 'sandboxcd6e5ad678034703b6c55091327ffc77.mailgun.org'
MAILGUN_API_KEY = 'key'
FROM_TITLE = 'Flask Ecommerce'
FROM_EMAIL = 'email'


class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), nullable=False, unique=True)
    activated = db.Column(db.Boolean, default=False)

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()

    def send_confirmation_email(self) -> Response:
        link = request.url_root[:-1] + url_for('userconfirm', user_id=self.id)

        return post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=('api', MAILGUN_API_KEY),
            data={
                'from': f'{FROM_TITLE} <{FROM_EMAIL}>',
                'to': self.email,
                'subject': 'Registration confirmation',
                'text': f'Please click the link to confirm your registration: {link}'
            }
        )

    @classmethod
    def find_by_username(cls, username: str) -> Union["UserModel", None]:
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, _id: int) -> Union["UserModel", None]:
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_email(cls, email: str) -> Union["UserModel", None]:
        return cls.query.filter_by(email=email).first()
