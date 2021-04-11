import traceback
from time import time

from flask import make_response, render_template
from flask_restful import Resource

from libs.mailgun import MailgunException
from models.confirmation import ConfirmationModel
from models.user import UserModel
from resources.user import USER_NOT_FOUND
from schemas.confirmation import ConfirmationSchema


confirmation_schema = ConfirmationSchema()

NOT_FOUND = 'Confirmation reference not found'
EXPIRED = 'The link has expired'
ALREADY_CONFIRMED = 'Registration has already been confirmed'
RESEND_FAIL = 'Internal Server Error. Failed to resend confirmation email'
RESEND_SUCCESSFUL = 'Email confirmation successfully resent'


class Confirmation(Resource):
    @classmethod
    def get(cls, confirmation_id: str):
        confirmation = ConfirmationModel.find_by_id(confirmation_id)
        if not confirmation:
            return {'message': NOT_FOUND}, 400

        if confirmation.expired:
            return {'message': EXPIRED}, 400

        if confirmation.confirmed:
            return {'message': ALREADY_CONFIRMED}, 400

        confirmation.confirmed = True
        confirmation.save_to_db()

        headers = {'Content-Type': 'text/html'}
        return make_response(
            render_template('confirmation_page.html', email=confirmation.user.email),
            200,
            headers
        )


class ConfirmationByUser(Resource):
    @classmethod
    def get(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {'message': USER_NOT_FOUND}, 404

        return (
            {
                'current_time': int(time()),
                'confirmation': [
                    confirmation_schema.dump(each)
                    for each in user.confirmation.order_by(ConfirmationModel.expire_at)
                ]
            }
        )

    @classmethod
    def post(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {'message': USER_NOT_FOUND}, 404

        try:
            confirmation = user.most_recent_confirmation
            if confirmation:
                if confirmation.confirmed:
                    return {'message': ALREADY_CONFIRMED}, 400
                confirmation.force_to_expire()

            new_confirmation = ConfirmationModel(user_id)
            new_confirmation.save_to_db()
            user.send_confirmation_email()

            return {'message': RESEND_SUCCESSFUL}, 201
        except MailgunException as e:
            return {'message': str(e)}, 500
        except:
            traceback.print_exc()
            return {'message': RESEND_FAIL}, 500
