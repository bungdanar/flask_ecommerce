import traceback

from flask import request
from flask_restful import Resource
from werkzeug.security import safe_str_cmp
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from models.user import UserModel
from models.confirmation import ConfirmationModel
from schemas.user import UserSchema
from blacklist import BLACKLIST
from libs.mailgun import MailgunException


USER_ALREADY_EXISTS = "A user with that username already exists"
EMAIL_ALREADY_EXISTS = "A user with that email already exists"
USER_NOT_FOUND = "User not found"
USER_DELETED = "User deleted"
INVALID_CREDENTIALS = "Invalid credentials"
USER_LOGGED_OUT = "User <id={user_id}> successfully logged out"
NOT_CONFIRMED_ERROR = 'You have not confirmed registration, please check your email <{}>'
USER_CONFIRMED = 'User confirmed'
FAILED_TO_CREATE = 'Internal server error. Failed to create user'
SUCCESS_REGISTER_MESSAGE = 'Account created successfully. An email with an activation link has been sent to your ' \
                           'email address. '

user_schema = UserSchema()


class UserRegister(Resource):
    @classmethod
    def post(cls):
        user: UserModel = user_schema.load(request.get_json())

        if UserModel.find_by_username(user.username):
            return {"message": USER_ALREADY_EXISTS}, 400

        if UserModel.find_by_email(user.email):
            return {"message": EMAIL_ALREADY_EXISTS}, 400

        try:
            user.save_to_db()

            confirmation = ConfirmationModel(user.id)
            confirmation.save_to_db()

            user.send_confirmation_email()
            return {"message": SUCCESS_REGISTER_MESSAGE}, 201
        except MailgunException as e:
            user.delete_from_db()
            return {'message': str(e)}, 500
        except:
            traceback.print_exc()
            user.delete_from_db()
            return {'message': FAILED_TO_CREATE}, 500


class User(Resource):
    @classmethod
    def get(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404

        return user_schema.dump(user)

    @classmethod
    def delete(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404

        user.delete_from_db()
        return {"message": USER_DELETED}


class UserLogin(Resource):
    @classmethod
    def post(cls):
        user_data: UserModel = user_schema.load(request.get_json(), partial=('email',))

        user = UserModel.find_by_username(user_data.username)

        if user and safe_str_cmp(user.password, user_data.password):
            confirmation = user.most_recent_confirmation
            if confirmation and confirmation.confirmed:
                access_token = create_access_token(identity=user.id, fresh=True)
                refresh_token = create_refresh_token(user.id)

                return {"access_token": access_token, "refresh_token": refresh_token}

            return {'message': NOT_CONFIRMED_ERROR.format(user.email)}, 400

        return {"message": INVALID_CREDENTIALS}, 401


class UserLogout(Resource):
    @classmethod
    @jwt_required()
    def post(cls):
        jti = get_jwt()["jti"]
        user_id = get_jwt_identity()

        BLACKLIST.add(jti)
        return {"message": USER_LOGGED_OUT.format(user_id=user_id)}


class TokenRefresh(Resource):
    @classmethod
    @jwt_required(refresh=True)
    def post(cls):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}
