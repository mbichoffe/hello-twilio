import os
from dotenv import load_dotenv, find_dotenv
from flask import Flask, request, redirect, url_for, render_template, jsonify
from http import HTTPStatus
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import requests
from requests import Request, Session
import phonenumbers
from flask_moment import Moment
from datetime import datetime
import pusher

app = Flask(__name__)
moment = Moment(app)

load_dotenv(find_dotenv())

#ENVIRONMENT VARIABLES
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID_P')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN_P')
TWILIO_SHORT_CODE = os.getenv('TWILIO_SHORT_CODE')

SPLASHTHAT_CLIENT_SECRET = os.getenv('SPLASHTHAT_CLIENT_SECRET')
SPLASHTHAT_CLIENT_ID = os.getenv('SPLASHTHAT_CLIENT_ID')
NUMBERS = [os.getenv("TWILIO_NUMBERS")]
CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')
PUSHER_ID = os.getenv('PUSHER_ID')
PUSHER_KEY = os.getenv('PUSHER_KEY')
PUSHER_SECRET = os.getenv('PUSHER_SECRET')

pusher_client = pusher.Pusher(
  app_id='638813',
  key='00127d7d175b18006f04',
  secret='b158e3dca09275556237',
  cluster='us2',
  ssl=True
)

EVENT_ID = '3188092'
# TODO : Add event data to env file
EVENT_URL_ID = "246ae8934cbf423dff3a8c604dce6d9304d3830a4f6fedc7612073757d287550"
EVENT_URL = "https://tweeksciencefair.splashthat.com"
API_URL = "https://prod-api.splashthat.com"

ALL_GUEST_DICT = {}

class Guest:
    def __init__(self, guest_dict, phone):
        self.id = str(guest_dict["id"])
        self.first_name = guest_dict["contact"]["first_name"]
        self.last_name = guest_dict["contact"]["last_name"]
        self.phone = phone

@app.route("/")
def home():
    token = get_access_token()
    # Get event data
    eventInfoResponse = get_event_information(token, EVENT_ID)

    if eventInfoResponse:
        title = eventInfoResponse['title']
        description = eventInfoResponse['meta_description']
        print(eventInfoResponse['start_time'])
        start_time = datetime.strptime(eventInfoResponse['start_time'], '%Y-%m-%dT%H:%M:%S')
        end_time = datetime.strptime(eventInfoResponse['end_time'], '%Y-%m-%dT%H:%M:%S')

    return render_template('index.html',
        event_title=title,
        description=description,
        start_time= start_time,
        end_time= end_time)

@app.route("/feed")
def feed():
    return render_template('feed.html')

@app.route("/v1/send-initial-message", methods=["POST"])
def send_initial_message():
    for guest in ALL_GUEST_DICT.values():
        message = CLIENT.messages.create(
            to=guest.phone,
            from_=TWILIO_SHORT_CODE,
            body="Hello! Thank you for RSVPing to the Tweek Science Fair. When you arrive at the event, check in by replying 'HERE' to this message. Come by the Hello Tweek booth to receive a small prize for your participation!")

    return("Hello World")

@app.route("/v1/send-reminder", methods=["POST"])
def send_reminder():
    failed = 0
    for guest in ALL_GUEST_DICT.values():
        try:
            message = send_message(guest.phone, "Reminder! Tweek Science Fair is happening today at 2PM. Text from this number to check in.")
        except TwilioRestException as e:
            print(e)
            failed +=1
            continue
    return jsonify({"message": "Reminder sent to guests with " + str(failed) + " failures"}), HTTPStatus.OK

@app.route("/v1/get-attendees", methods=["GET"])
def get_attendees():
    token = get_access_token()
    response = get_guests_list(token, EVENT_ID)
    # TODO: We know it is not necessary to pass env variable, but we will re-engineer this in the future
    try:
        response["guests"]
    except KeyError:
        return jsonify({"message": "Could not retrieve data"}), HTTPStatus.BAD_REQUEST

    for guest in response["guests"]:
        for obj in guest["answers"]:
            if obj["question_id"] == 866483:
                try:
                    phone_obj = phonenumbers.parse(obj["answer"], "US")
                except phonenumbers.phonenumberutil.NumberParseException:
                    print("Guest with id {} entered {} which is not a phone number.".format(str(guest["id"]), obj["answer"]))
                    continue

                if phonenumbers.is_possible_number(phone_obj) and phonenumbers.is_valid_number(phone_obj):
                    phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
                    ALL_GUEST_DICT[phone] = Guest(guest, phone)
                else:
                    print("Guest with id {} entered {} which is not a valid or possible phone number.".format(str(guest["id"]), obj["answer"]))
                    continue
    print("All guests: {}".format(ALL_GUEST_DICT))

    return jsonify({"message": "All attendees gotten."}), HTTPStatus.OK


@app.route("/sms", methods=["POST"])
def incoming_message():

    phone_number = request.values.get('From')

    requests.post(url_for('check_in_guest', _external=True), json={"phone_number": phone_number})

    return("Hello we sent a text")

@app.route("/v1/checkin", methods=["POST"])
def check_in_guest():

    token = get_access_token()
    phone_number = request.get_json()['phone_number']

    if phone_number:
        guest = ALL_GUEST_DICT.get(phone_number)
        if not guest:
            resp = send_message(phone_number, "We could not find your phone number in our guest list. "
                                       "Please look for a Twilio volunteer for assistance.")
            if resp.status == "queued":  # Message was sent succesfully
                return jsonify({"message": "Phone number {} not found in guest list".format(phone_number)}), HTTPStatus.OK
            else:
                # Guest is NOT checked in and failed to receive message
                # TODO: Will the initial status back from Twilio ever not be queued?
                # Would need status callbacks to properly verify that a message has not been delivered
                msg = "Phone number {} not found in guest list and we could not send confirmation SMS".format(
                    phone_number)
                print(msg)
                return jsonify({"message": msg}), HTTPStatus.BAD_REQUEST
        else:
            is_checked_in = splashthat_check_in(guest, token)
            if is_checked_in:
                # Call url that sends guest success message with guest.phone as param
                resp = send_message(guest.phone, "You are now checked in. Please enjoy the event!")

                if resp.status == "queued": # Message was sent succesfully
                    return ('Message sent')
                else:
                    # Guest is checked in but failed to receive message
                    # TODO: This cannot be tested at this time. Needs status callbacks for proper testing

                    msg = "Guest {} {} was checked in successfully but we couldn't send confirmation SMS".format(
                        guest.first_name, guest.last_name)
                    print(msg)
                    return jsonify({"message": msg}), HTTPStatus.BAD_REQUEST
            else:
                send_message(guest.phone, "We could not check you in at this time")  # Or any other message
                msg = "Failed to check in phone number {}".format(guest.phone)
                print(msg)
                return jsonify({"message": "Failed to check in"}), HTTPStatus.INTERNAL_SERVER_ERROR


def splashthat_check_in(guest: object, access_token: str) -> bool:
    """
    Calls SplashThat API to check in a guest
    If successful, returns success message -- otherwise it returns an error message
    :param: guest_id
    :return: True if request succeeds, False otherwise
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.put(API_URL +
                             "/groupcontact/" +
                             guest.id +
                             "/checkin",
                             headers=headers
                             )
    if response.ok:
        pusher_client.trigger('my-channel', 'check-in-event', { "name": guest.first_name + ' ' + guest.last_name})
        return True

    elif response.status_code == 409:
        print("user {} {} is already checked in.".format(guest.first_name, guest.last_name))
        return True

    else:
        print("error checking in {} {}".format(guest.first_name, guest.last_name))
        return False

def get_event_information(access_token:str, event_id:str):
    """
    :param token: string
    :param event_id: string
    :return: giant json
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.get(API_URL +
                            "/events/" +
                            event_id +
                            "/settings",
                            headers=headers)
    json = response.json()
    # If the response was successful and returned JSON has the value True
    # for the 'created' key
    if response.ok:
        return json["data"]
    else:
        return json["error_description"]

def get_guests_list(access_token:str, event_id:str):
    """
    :param token: string
    :param event_id: string
    :return: giant json
    """

    headers = {'Authorization': 'Bearer ' + access_token}

    response = requests.get(API_URL +
                            "/events/" +
                            event_id +
                            "/guestlist?limit=1000",
                            headers=headers)
    json = response.json()
    # If the response was successful and returned JSON then this has the value True
    # for the 'created' key
    if response.ok:
        return json["data"]
    else:
        return json["error_description"]

def get_access_token():
    """Use access code to request user's access token"""

    response = requests.get("https://api.splashthat.com/oauth/v2/token?client_id="+
                            SPLASHTHAT_CLIENT_ID+
                            "&client_secret="+
                            SPLASHTHAT_CLIENT_SECRET+
                            "&grant_type=password&scope=user&username="+
                            EMAIL_ADDRESS+
                            "&password="+
                            PASSWORD)

    json = response.json()

    if response.ok:
        access_token = json['access_token']
    # If there was an error, use None as the access token and
    # flash a message
    else:
        access_token = None
        print(f'OAuth failed: {json["error_description"]}')

    return access_token

def send_message(number:str, body:str=None)-> "twilio.rest.api.v2010.account.message.MessageInstance":
    message = CLIENT.messages.create(
        to=number,
        from_=TWILIO_SHORT_CODE,
        body=body)
    return message

if __name__ == "__main__":
    app.run(debug=True)
